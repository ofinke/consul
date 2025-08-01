import ast
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

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

# NOTE: This works enough. Time to polish it. I want to return dict instead of bool. Move prints to logger or remove them
# create hack implementation of user input using the CLI TerminalHandler
@tool
def propose_code_change(file_path: str, proposed_code: str) -> bool:
    """
    Propose a code change by showing a VSCode diff and asking for user approval.

    Args:
        file_path (str): Relative path to the file to be changed.
        proposed_code (str): Proposed new code as a string.

    Returns:
        bool: True if the change was accepted and applied, False otherwise.

    """
    # resolve path to existing file
    abs_path = Path(file_path).resolve()

    # split 
    proposed_lines = proposed_code.splitlines(keepends=True)

    tmp_dir = Path.cwd() / ".temp"
    tmp_dir.mkdir(exist_ok=True)

    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".py", dir=tmp_dir) as tmp:
        tmp.writelines(proposed_lines)
        tmp_path = Path(tmp.name)

    try:
        # Find the code command
        code_cmd = shutil.which("code")
        if not code_cmd:
            # Try common locations
            possible_paths = [
                "/usr/local/bin/code",
                "C:\\Users\\{}\\AppData\\Local\\Programs\\Microsoft VS Code\\bin\\code.cmd".format(
                    os.getenv("USERNAME", "")
                ),
            ]
            for path in possible_paths:
                if Path(path).exists():
                    code_cmd = path
                    break

        if not code_cmd:
            raise FileNotFoundError("VSCode command not found")

        print(f"Using VSCode at: {code_cmd}")

        result = subprocess.run(
            [code_cmd, "--diff", str(abs_path), str(tmp_path)], check=False, capture_output=True, text=True
        )

        if result.returncode != 0:
            print(f"VSCode command failed: {result.stderr}")
            raise subprocess.CalledProcessError(result.returncode, code_cmd)

        print("Diff opened in VSCode. Please review the changes.")

        choice = input("Accept the proposed change? [y/N]: ").strip().lower()
        accepted = choice == "y"

        if accepted:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text("".join(proposed_lines), encoding="utf-8")
            print(f"✓ Changes applied to {abs_path}")
        else:
            print("✗ Changes rejected.")

    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"Could not open VSCode diff: {e}")
        print("Showing text diff instead:")

        choice = input("Accept the proposed change? [y/N]: ").strip().lower()
        accepted = choice == "y"

        if accepted:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            abs_path.write_text("".join(proposed_lines), encoding="utf-8")
            print(f"✓ Changes applied to {abs_path}")

    finally:
        tmp_path.unlink(missing_ok=True)

    return accepted
