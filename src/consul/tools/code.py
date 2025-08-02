import ast
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from loguru import logger

from consul.cli.utils.text import TerminalHandler

from .utils import compile_search_pattern, find_python_files, parse_ast_from_content, read_file_lines


@tool
def get_source_code(  # noqa: C901
    target_type: str,
    name: str,
    file_path: str | None = None,
    project_root: str = ".",
    include_context: bool = False,  # noqa: FBT001, FBT002
) -> dict[str, Any]:
    """
    Retrieve complete source code for specific functions, classes, or methods.

    Input:
        target_type: 'function', 'class', 'method', or 'file'
        name: Exact name of function/class to retrieve
        file_path: Specific file to look in (optional)
        include_context: Include surrounding code context

    Use when: You need the actual implementation code.
    Returns: Complete source code with line numbers.
    """
    if target_type == "file":
        if not file_path:
            return {"error": "file_path required for target_type='file'"}
        file_obj = Path(file_path).resolve()
        if not file_obj.exists():
            return {"error": f"File not found: {file_path}"}
        try:
            content = "".join(read_file_lines(str(file_obj)))
            return {
                "name": file_obj.name,
                "type": "file",
                "file": str(file_obj),
                "code": content,
                "lines": (1, len(content.splitlines())),
            }
        except Exception as e:
            return {"error": f"Could not read file: {e}"}

    files_to_search = [Path(file_path)] if file_path else find_python_files(project_root, "**/*.py")

    for file_path_obj in files_to_search:
        try:
            lines = read_file_lines(str(file_path_obj))
            content = "".join(lines)
            tree = parse_ast_from_content(content)

            for node in ast.walk(tree):
                found = False
                node_type = None

                if target_type in ["function", "method"] and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == name:
                        found = True
                        node_type = "async function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                elif target_type == "class" and isinstance(node, ast.ClassDef) and node.name == name:
                    found = True
                    node_type = "class"

                if found:
                    start_line = node.lineno
                    end_line = getattr(node, "end_lineno", start_line)
                    code_lines = lines[start_line - 1 : end_line] if end_line else [lines[start_line - 1]]
                    source_code = "".join(code_lines)
                    result = {
                        "name": name,
                        "type": node_type,
                        "file": str(file_path_obj),
                        "lines": (start_line, end_line),
                        "code": source_code,
                        "docstring": ast.get_docstring(node),
                    }
                    if include_context:
                        context_start = max(0, start_line - 4)
                        context_end = min(len(lines), end_line + 3)
                        context_code = "".join(lines[context_start:context_end])
                        result["context"] = context_code
                        result["context_lines"] = (context_start + 1, context_end)
                    return result
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue

    return {"error": f"No {target_type} named '{name}' found"}


@tool
def find_code_content(
    query: str,
    project_root: str = ".",
    file_pattern: str = "**/*.py",
    context_lines: int = 3,
    max_results: int = 20,
) -> dict[str, Any]:
    """
    Search for specific content/patterns within code files.

    Args:
        query: Text pattern to search for (supports regex if wrapped in /pattern/).
        project_root: Root directory for searching.
        file_pattern: Glob pattern for files to search.
        context_lines: Number of lines to include around matches.
        max_results: Maximum number of matches to return.

    Returns:
        dict: Search results with context and line numbers.

    """
    try:
        files = find_python_files(project_root, file_pattern)
        pattern, is_regex = compile_search_pattern(query)
        results = []
        for file_path in files:
            try:
                lines = read_file_lines(str(file_path))
                for i, line in enumerate(lines):
                    if pattern.search(line):
                        start = max(0, i - context_lines)
                        end = min(len(lines), i + context_lines + 1)
                        results.append(
                            {
                                "file": str(file_path),
                                "line_number": i + 1,
                                "matched_line": line.strip(),
                                "context": "".join(lines[start:end]),
                                "context_lines": (start + 1, end),
                            }
                        )
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break
            except (OSError, UnicodeDecodeError):
                continue
        return {
            "results": results,
            "summary": {
                "total_found": len(results),
                "query": query,
                "is_regex": is_regex,
                "truncated": len(results) == max_results,
            },
        }
    except Exception as e:  # noqa: BLE001
        return {
            "error": f"Search failed: {e!s}",
            "results": [],
            "summary": {
                "total_found": 0,
                "query": query,
            },
        }


@tool
def propose_code_changes(file_path: str, proposed_code: str) -> dict[str, Any]:
    """
    Propose a code change or create a new file. Code change is proposed via 'code --diff'. Create the 'proposed_code'
    accordingly.

    Args:
        file_path (str): Relative path to existing or new file.
        proposed_code (str): Proposed new code as a string.

    Returns:
        dict[str, Any]: dictionary describing state of the code change

    """
    # resolve path to existing / new file
    original_file = Path(file_path).resolve()

    # split code into lines
    proposed_lines = proposed_code.splitlines(keepends=True)

    # create temporary file with new code in projects ".temp" folder
    tmp_dir = Path.cwd() / ".temp"
    tmp_dir.mkdir(exist_ok=True)

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py", dir=tmp_dir) as tmp:
        tmp.writelines(proposed_lines)
        proposed_file = Path(tmp.name)

    # if the `file_path` file doesn't exist, create an empty temp file for diff
    is_new_file = not original_file.exists()
    if is_new_file:
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py", dir=tmp_dir) as empty_tmp:
            empty_tmp_path = Path(empty_tmp.name)
    else:
        empty_tmp_path = original_file

    try:
        # Find the code command
        code_cmd = shutil.which("code")

        if not code_cmd:
            msg = "VSCode command 'code' not found"
            logger.warning(msg)
            return {"status": "failed", "message": msg}

        # TODO: can I mitigate the S603 rule somehow reasonably?
        result = subprocess.run(
            [code_cmd, "--diff", str(empty_tmp_path), str(proposed_file)], check=False, capture_output=True, text=True
        )

        if result.returncode != 0:
            msg = f"VSCode command failed: {result.stderr}"
            logger.warning(msg)
            return {"status": "failed", "message": msg}

        # HACK, FIXME: The usage of TerminalHandler is hacky here as I would like to keep interface and agents
        # implementation as separate as possible. This is hopefuly shortterm solution before I implement the asyncio
        # event / consumer approach. So hopefully I'll manage lol.
        choice = TerminalHandler.prompt_user_input("→ Accept the proposed change? [y/N]: ")
        accepted = choice == "y"

        # ask user why the changes were rejected
        if not accepted:
            reason = TerminalHandler.prompt_user_input("→ Comment why changes were rejected: ")
            msg = f"Changes rejected wit note from the user: '{reason}'."
            return {"status": "failed", "message": msg}

        # save the changes
        original_file.parent.mkdir(parents=True, exist_ok=True)
        original_file.write_text("".join(proposed_lines), encoding="utf-8")

    except Exception as e:  # noqa: BLE001
        msg = f"Exception raised during the propose_code_change tool run: {e!s}"
        logger.warning(msg)
        return {"status": "failed", "message": msg}

    else:
        msg = f"Changes accepted by user and applied to {original_file}"
        return {"status": "success", "message": msg}

    finally:
        proposed_file.unlink(missing_ok=True)
        if is_new_file and empty_tmp_path.exists():
            empty_tmp_path.unlink(missing_ok=True)
