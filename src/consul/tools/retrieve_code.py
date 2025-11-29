import ast
from pathlib import Path

from .utils import parse_ast_from_content, read_file_lines


def get_source_code(target_type: str, file_path: str, name: str | None = None) -> dict[str, str | int]:
    """
    Retrieve complete source code for a specific function, class, method, or entire file.

    Args:
        target_type: 'function', 'class', 'method', or 'file'.
        file_path: Path to the file to retrieve code from.
        name: Optional exact name of function/class to retrieve. If None and target_type is 'file', returns whole file.

    Returns:
        dict[str, str]: On success, returns {"code": code_with_line_numbers, "file_last_line_num": number of last line
            in file}. On failure, returns {"error": message}.

    """
    # check if file exists
    file_obj = Path(file_path).resolve()
    result: dict[str, str]
    if not file_obj.exists():
        result = {"error": f"File not found: {file_path}"}
        return result

    # load file
    try:
        lines = read_file_lines(str(file_obj))
    except Exception as e:  # noqa: BLE001
        result = {"error": f"Could not read file: {e}"}
        return result

    # return whole file if desired
    if target_type == "file":
        result = {"code": "".join(f"{i + 1}: {line}" for i, line in enumerate(lines))}
        return result

    # parse file using ast
    try:
        content = "".join(lines)
        tree = parse_ast_from_content(content)
    except (SyntaxError, UnicodeDecodeError) as e:
        result = {"error": f"Could not parse file: {e}"}
        return result

    # go through file and find desired content
    for node in ast.walk(tree):
        if target_type in ["function", "method"] and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == name:
                start_line = min((d.lineno for d in getattr(node, "decorator_list", [])), default=node.lineno)
                end_line = getattr(node, "end_lineno", start_line)
                code_lines = lines[start_line - 1 : end_line]
                numbered_code = "".join(f"{start_line + idx}: {line}" for idx, line in enumerate(code_lines))
                result = {"code": numbered_code, "file_last_line_num": len(lines)}
                break
        elif target_type == "class" and isinstance(node, ast.ClassDef) and node.name == name:
            start_line = min((d.lineno for d in getattr(node, "decorator_list", [])), default=node.lineno)
            end_line = getattr(node, "end_lineno", start_line)
            code_lines = lines[start_line - 1 : end_line]
            numbered_code = "".join(f"{start_line + idx}: {line}" for idx, line in enumerate(code_lines))
            result = {"code": numbered_code, "file_last_line_num": len(lines)}
            break
    else:
        result = {"error": f"No {target_type} named '{name}' found in {file_path}"}

    return result
