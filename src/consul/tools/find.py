import ast
from pathlib import Path
from typing import Any

from langchain_core.tools import tool

from .utils import compile_search_pattern, find_python_files, parse_ast_from_content, read_file_lines


@tool
def find_patterns(  # noqa: C901
    pattern_type: str,
    search_term: str | None = None,
    file_path: str | None = None,
    include_usage: bool = True,  # noqa: FBT001, FBT002
    project_root: str = ".",
) -> dict[str, Any]:
    """
    Find functions, classes, imports, and patterns in the project repository.

    Args:
        pattern_type: One of ['functions', 'classes', 'imports', 'calls', 'variables', 'decorators']
        search_term: Specific name to search for (optional, if not provided returns all)
        file_path: Specific file to search in (optional, if not provided searches all .py files)
        include_usage: Whether to include where the pattern is used/called
        project_root: Root directory of the project

    Returns:
        dict: Results with matches and summary

    """
    valid_patterns = ["functions", "classes", "imports", "calls", "variables", "decorators"]
    if pattern_type not in valid_patterns:
        return {
            "error": f"Invalid pattern_type. Must be one of: {valid_patterns}",
            "matches": [],
            "summary": {"total_found": 0, "files_searched": 0, "pattern_type": pattern_type},
        }

    project_path = Path(project_root).resolve()
    files_to_search = []

    # Determine which files to search
    if file_path:
        file_path_obj = Path(file_path).resolve()
        if file_path_obj.exists() and file_path_obj.suffix == ".py":
            files_to_search = [file_path_obj]
        else:
            return {
                "error": f"File not found or not a Python file: {file_path}",
                "matches": [],
                "summary": {"total_found": 0, "files_searched": 0, "pattern_type": pattern_type},
            }
    else:
        # Find all Python files in the project
        try:
            files_to_search = find_python_files(str(project_path), "*.py")
        except (OSError, PermissionError) as e:
            return {
                "error": f"Error accessing project directory: {e}",
                "matches": [],
                "summary": {"total_found": 0, "files_searched": 0, "pattern_type": pattern_type},
            }

    matches = []
    files_searched = 0

    for file_path_obj in files_to_search:
        try:
            # Ensure we're working with a Path object
            if isinstance(file_path_obj, str):
                file_path_obj = Path(file_path_obj)

            # Skip if not a file or doesn't exist
            if not file_path_obj.is_file():
                continue

            lines = read_file_lines(str(file_path_obj))
            content = "".join(lines)

            files_searched += 1

            # Parse the file with AST
            try:
                tree = parse_ast_from_content(content)
                file_matches = _analyze_ast(tree, str(file_path_obj), lines, pattern_type, search_term)
                matches.extend(file_matches)
            except SyntaxError as e:
                # Skip files with syntax errors, but you might want to log this
                continue

        except (OSError, UnicodeDecodeError, PermissionError) as e:
            # Skip files that can't be read
            continue

    # Find usage locations if requested
    if include_usage and matches:
        matches = _add_usage_locations(matches, files_to_search, pattern_type)

    return {
        "matches": matches,
        "summary": {"total_found": len(matches), "files_searched": files_searched, "pattern_type": pattern_type},
    }


def _analyze_ast(  # noqa: C901
    tree: ast.AST, file_path: str, lines: list[str], pattern_type: str, search_term: str = None
) -> list[dict]:
    """Analyze AST tree to find patterns."""
    matches = []

    class PatternVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            """Visit a function definition node and process it if it matches the pattern type."""
            if pattern_type in ["functions"]:
                self._process_function(node)
            if pattern_type == "decorators" and node.decorator_list:
                self._process_decorators(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            """Visit an async function definition node and process it if it matches the pattern type."""
            if pattern_type in ["functions"]:
                self._process_function(node, is_async=True)
            if pattern_type == "decorators" and node.decorator_list:
                self._process_decorators(node)
            self.generic_visit(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            """Visit a class definition node and process it if it matches the pattern type."""
            if pattern_type == "classes":
                self._process_class(node)
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:
            """Visit an import statement node and process it if it matches the pattern type."""
            if pattern_type == "imports":
                self._process_import(node)
            self.generic_visit(node)

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            """Visit an import-from statement node and process it if it matches the pattern type."""
            if pattern_type == "imports":
                self._process_import_from(node)
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            """Visit a function call node and process it if it matches the pattern type."""
            if pattern_type == "calls":
                self._process_call(node)
            self.generic_visit(node)

        def visit_Assign(self, node: ast.Assign) -> None:
            """Visit an assignment node and process it if it matches the pattern type."""
            self._process_assignment(node)
            self.generic_visit(node)

        def _process_function(self, node: ast.FunctionDef, is_async: bool = False) -> None:
            """
            Process a function or async function node and add it to matches if it matches the search term.

            Args:
                node: The function definition AST node.
                is_async: Whether the function is asynchronous.

            """
            if search_term and search_term != node.name:
                return

            docstring = ast.get_docstring(node) or ""
            func_type = "async function" if is_async else "function"

            # Get function signature
            args = [arg.arg for arg in node.args.args]

            signature = f"def {node.name}({', '.join(args)})"

            matches.append(
                {
                    "name": node.name,
                    "type": func_type,
                    "file": file_path,
                    "line": node.lineno,
                    "definition": signature,
                    "docstring": docstring,
                    "usage_locations": [],
                }
            )

        def _process_class(self, node: ast.ClassDef) -> None:
            """
            Process a class definition node and add it to matches if it matches the search term.

            Args:
                node: The class definition AST node.

            """
            if search_term and search_term != node.name:
                return

            docstring = ast.get_docstring(node) or ""
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif hasattr(ast, "unparse"):
                    bases.append(ast.unparse(base))
                else:
                    bases.append("BaseClass")

            inheritance = f"({', '.join(bases)})" if bases else ""

            matches.append(
                {
                    "name": node.name,
                    "type": "class",
                    "file": file_path,
                    "line": node.lineno,
                    "definition": f"class {node.name}{inheritance}",
                    "docstring": docstring,
                    "usage_locations": [],
                }
            )

        def _process_import(self, node: ast.Import) -> None:
            """
            Process an import statement node and add it to matches if it matches the search term.

            Args:
                node: The import AST node.

            """
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                if search_term and search_term != name:
                    continue

                matches.append(
                    {
                        "name": name,
                        "type": "import",
                        "file": file_path,
                        "line": node.lineno,
                        "definition": f"import {alias.name}" + (f" as {alias.asname}" if alias.asname else ""),
                        "docstring": "",
                        "usage_locations": [],
                    }
                )

        def _process_import_from(self, node: ast.ImportFrom) -> None:
            """
            Process an import-from statement node and add it to matches if it matches the search term.

            Args:
                node: The import-from AST node.

            """
            module = node.module or ""
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                if search_term and search_term != name:
                    continue

                matches.append(
                    {
                        "name": name,
                        "type": "import_from",
                        "file": file_path,
                        "line": node.lineno,
                        "definition": f"from {module} import {alias.name}"
                        + (f" as {alias.asname}" if alias.asname else ""),
                        "docstring": "",
                        "usage_locations": [],
                    }
                )

        def _process_call(self, node: ast.Call) -> None:
            """
            Process a function call node and add it to matches if it matches the search term.

            Args:
                node: The function call AST node.

            """
            # Extract function name from call
            func_name = None
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                func_name = node.func.attr

            if not func_name or (search_term and search_term != func_name):
                return

            context = _get_line_context(lines, node.lineno)

            matches.append(
                {
                    "name": func_name,
                    "type": "function_call",
                    "file": file_path,
                    "line": node.lineno,
                    "definition": context.strip(),
                    "docstring": "",
                    "usage_locations": [],
                }
            )

        def _process_assignment(self, node: ast.Assign) -> None:
            """
            Process an assignment node and add it to matches if it matches the search term.

            Args:
                node: The assignment AST node.

            """
            for target in node.targets:
                if isinstance(target, ast.Name):
                    var_name = target.id
                    if search_term and search_term != var_name:
                        continue

                    context = _get_line_context(lines, node.lineno)

                    matches.append(
                        {
                            "name": var_name,
                            "type": "variable",
                            "file": file_path,
                            "line": node.lineno,
                            "definition": context.strip(),
                            "docstring": "",
                            "usage_locations": [],
                        }
                    )

        def _process_decorators(self, node: ast.FunctionDef) -> None:
            """
            Process decorators of a function or async function node and add them to matches if they match the search
            term.

            Args:
                node: The function or async function AST node.

            """
            for decorator in node.decorator_list:
                dec_name = None
                if isinstance(decorator, ast.Name):
                    dec_name = decorator.id
                elif isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name):
                    dec_name = decorator.func.id

                if not dec_name or (search_term and search_term != dec_name):
                    continue

                context = _get_line_context(lines, decorator.lineno)

                matches.append(
                    {
                        "name": dec_name,
                        "type": "decorator",
                        "file": file_path,
                        "line": decorator.lineno,
                        "definition": context.strip(),
                        "docstring": "",
                        "usage_locations": [],
                    }
                )

    visitor = PatternVisitor()
    visitor.visit(tree)
    return matches


def _get_line_context(lines: list[str], line_no: int, context_lines: int = 0) -> str:
    """Get the line content with optional context."""
    if line_no <= 0 or line_no > len(lines):
        return ""

    start = max(0, line_no - 1 - context_lines)
    end = min(len(lines), line_no + context_lines)

    return "\n".join(lines[start:end])


def _is_definition_line(match: dict, file_path: str, line_no: int) -> bool:
    """Check if the given file path and line number correspond to the definition line of the match."""
    return match["file"] == file_path and match["line"] == line_no


def _process_line(line: str, line_no: int, file_path: str, name_patterns: dict, matches: list[dict]) -> None:
    """Process a single line of code to find and record usage locations for matched names."""
    for name, pattern in name_patterns.items():
        if pattern.search(line):
            for match in matches:
                if match["name"] == name and not _is_definition_line(match, file_path, line_no):
                    match["usage_locations"].append({"file": file_path, "line": line_no, "context": line.strip()})


def _add_usage_locations(matches: list[dict], files_to_search: list, pattern_type: str) -> list[dict]:
    """Find where the identified patterns are used in the codebase."""
    if pattern_type in ["calls", "function_call"]:
        return matches  # Calls are already usage locations

    names_to_find = {match["name"] for match in matches}
    # Pre-compile patterns for all names
    name_patterns = {name: compile_search_pattern(name)[0] for name in names_to_find}

    for file_path_obj in files_to_search:
        try:
            file_path_obj = Path(file_path_obj) if isinstance(file_path_obj, str) else file_path_obj  # noqa: PLW2901

            if not file_path_obj.is_file():
                continue

            lines = read_file_lines(str(file_path_obj))
            file_path_str = str(file_path_obj)
            for line_no, line in enumerate(lines, 1):
                _process_line(line, line_no, file_path_str, name_patterns, matches)
        except (OSError, UnicodeDecodeError, PermissionError):
            continue

    return matches
