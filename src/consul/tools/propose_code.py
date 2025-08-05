import io
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from langchain_core.tools import tool
from loguru import logger
from unidiff import PatchSet

from consul.cli.utils.text import TerminalHandler


def _ensure_temp_dir() -> Path:
    """Ensure .temp directory exists and return path."""
    tmp_dir = Path.cwd() / ".temp"
    tmp_dir.mkdir(exist_ok=True)
    return tmp_dir


def _show_diff_in_vscode(original_file: Path, modified_file: Path) -> tuple[bool, str]:
    """Show diff in VSCode and return success status and error message if any."""
    code_cmd = shutil.which("code")
    if not code_cmd:
        return False, "VSCode command 'code' not found"

    result = subprocess.run(
        [code_cmd, "--diff", str(original_file), str(modified_file)], check=False, capture_output=True, text=True
    )

    if result.returncode != 0:
        return False, f"VSCode command failed: {result.stderr}"

    return True, ""


def _get_user_approval() -> tuple[bool, str]:
    """Get user approval for changes."""
    choice = TerminalHandler.prompt_user_input("→ Accept suggested changes? [y/N]: ")
    if choice == "y":
        return True, ""
    reason = TerminalHandler.prompt_user_input("→ Comment why changes were rejected: ")
    return False, reason


def _eval_patch_hunk(patch: str) -> str:
    """
    Checks and repairs all hunks in a unified diff patch if the hunk header doesn't match the actual number of lines
    in the hunk body. Returns the (possibly fixed) patch as a string.
    """
    if not any(line.startswith("--- ") for line in patch.splitlines()):
        patch = "--- a/file.txt\n+++ b/file.txt\n" + patch

    hunk_header_re = re.compile(
        r"^@@ "
        r"-([1-9]\d*)(?:,([1-9]\d*))?\s"  # group(1): old_start, group(2): old_count (optional)
        r"\+([1-9]\d*)(?:,([1-9]\d*))?"  # group(3): new_start, group(4): new_count (optional)
        r" @@(.*)$"  # group(5): optional section
    )

    lines = patch.splitlines()
    out_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = hunk_header_re.match(line)
        if m:
            # Save hunk header and body for now
            hunk_header = line
            hunk_body = []
            i += 1
            # Stop at the next hunk header or end of patch
            while i < len(lines) and not hunk_header_re.match(lines[i]):
                hunk_body.append(lines[i])
                i += 1
            # Count old and new lines in hunk body
            old_lines = 0
            new_lines = 0
            for body_line in hunk_body:
                if body_line.startswith((" ", "-")):
                    old_lines += 1
                if body_line.startswith((" ", "+")):
                    new_lines += 1
            # Prepare fixed counts
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) else 1
            section = m.group(5) or ""
            # Only fix if mismatched
            if old_count != old_lines or new_count != new_lines:
                fixed_header = f"@@ -{old_start},{old_lines} +{new_start},{new_lines} @@{section}"
                out_lines.append(fixed_header)
            else:
                out_lines.append(hunk_header)
            out_lines.extend(hunk_body)

        else:
            out_lines.append(line)
            i += 1  # Only increment when we're not processing a hunk

    # ensure trailing newline
    patch_str = "\n".join(out_lines)
    if not patch_str.endswith("\n"):
        patch_str += "\n"
    return patch_str


def _apply_patch(original_content: str, patch: str) -> str:
    # Safety: PatchSet expects file headers (---, +++) to find the file!
    if not any(line.startswith("--- ") for line in patch.splitlines()):
        msg = "Patch must include file headers (---, +++ lines)."
        raise ValueError(msg)

    # Split the content keeping line endings so hunk.linenos match
    original_lines = original_content.splitlines(keepends=True)
    patchset = PatchSet(io.StringIO(patch))
    patched_file = patchset[0]

    # Apply all hunks to `original_lines` in order
    patched_lines = []
    idx = 0  # position in original_lines

    for hunk in patched_file:
        # Write unchanged lines before hunk
        while idx < hunk.source_start - 1:
            patched_lines.append(original_lines[idx])
            idx += 1
        # Now, apply hunk
        for hunk_line in hunk:
            if hunk_line.is_context:
                # Unchanged line: copy from original
                patched_lines.append(original_lines[idx])
                idx += 1
            elif hunk_line.is_removed:
                # Line removed: skip in original
                idx += 1
            elif hunk_line.is_added:
                # Line added: add from patch
                patched_lines.append(hunk_line.value)
            # Note: No else: unknown line types
    # After the last hunk, add remaining lines
    patched_lines.extend(original_lines[idx:])

    return "".join(patched_lines)


@tool
def propose_code_edit(file_path: str, patch: str) -> dict[str, str]:
    """
    Apply a patch to an existing file using unified diff format with a valid hunk header.

    Args:
        file_path (str): Path to existing file to modify
        patch (str): Unified diff patch content. The patch needs to contain valid file hunk header with following format
            "@@ -1,6 +1,7 @@"

    Returns:
        dict[str, str]: Status of the patch operation

    """
    original_file = Path(file_path).resolve()

    # Validate file exists
    if not original_file.exists():
        return {
            "status": "failed",
            "message": f"Cannot patch non-existent file: {file_path}.",
        }

    modified_file = None
    try:
        # Read original content and apply patch
        original_content = original_file.read_text(encoding="utf-8")
        modified_content = _apply_patch(original_content, _eval_patch_hunk(patch))

        # Create temporary file with modified content
        tmp_dir = _ensure_temp_dir()
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py", dir=tmp_dir) as tmp:
            tmp.write(modified_content)
            modified_file = Path(tmp.name)

        # Show diff in VSCode
        success, error_msg = _show_diff_in_vscode(original_file, modified_file)
        if not success:
            return {"status": "failed", "message": error_msg}

        # Get user approval
        approved, rejection_reason = _get_user_approval()
        if not approved:
            return {"status": "rejected", "message": f"Patch rejected: {rejection_reason}"}

        # Apply changes
        original_file.write_text(modified_content, encoding="utf-8")

    except ValueError as e:
        msg = str(e)
        logger.warning(msg)
        return {"status": "failed", "message": msg}
    except Exception as e:  # noqa: BLE001
        msg = f"Unexpected error applying patch: {e!s}"
        logger.warning(msg)
        return {"status": "failed", "message": msg}

    else:
        return {"status": "success", "message": f"Patch successfully applied to {original_file}"}

    finally:
        if modified_file and modified_file.exists():
            modified_file.unlink(missing_ok=True)


@tool
def propose_new_code(file_path: str, content: str) -> dict[str, str]:
    """
    Propose new code into a new file.

    Args:
        file_path (str): Path for the new file to create
        content (str): Complete file content

    Returns:
        dict[str, str]: Status of the file creation

    """
    target_file = Path(file_path).resolve()

    # Check if file already exists
    if target_file.exists():
        return {
            "status": "failed",
            "message": f"File already exists: '{file_path}'. Cannot overwrite existing file!",
        }

    empty_file = None
    proposed_file = None
    try:
        # Create temporary files for diff display
        tmp_dir = _ensure_temp_dir()

        # Empty file to represent "before" state
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py", dir=tmp_dir) as empty_tmp:
            empty_file = Path(empty_tmp.name)

        # File with proposed content
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py", dir=tmp_dir) as content_tmp:
            content_tmp.write(content)
            proposed_file = Path(content_tmp.name)

        # Show diff in VSCode (empty file vs new content)
        success, error_msg = _show_diff_in_vscode(empty_file, proposed_file)
        if not success:
            return {"status": "failed", "message": error_msg}

        # Get user approval
        approved, rejection_reason = _get_user_approval()
        if not approved:
            return {"status": "rejected", "message": f"File creation rejected with comment: {rejection_reason}"}

        # Create directory if needed and write file
        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(content, encoding="utf-8")

    except Exception as e:  # noqa: BLE001
        msg = f"Failed to create file: {e!s}"
        logger.warning(msg)
        return {"status": "failed", "message": msg}

    else:
        return {"status": "success", "message": f"New file created: {target_file}"}

    finally:
        # Cleanup temporary files
        if empty_file and empty_file.exists():
            empty_file.unlink(missing_ok=True)
        if proposed_file and proposed_file.exists():
            proposed_file.unlink(missing_ok=True)
