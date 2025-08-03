import ast
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
