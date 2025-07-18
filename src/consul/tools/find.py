import ast
import re
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


@tool
def find_patterns(
    pattern_type: str,
    search_term: str = None,
    file_path: str = None,
    include_usage: bool = True,
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
            files_to_search = [f for f in project_path.rglob("*.py") if f.is_file()]
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

            with open(file_path_obj, "r", encoding="utf-8") as file:
                content = file.read()
                lines = content.splitlines()

            files_searched += 1

            # Parse the file with AST
            try:
                tree = ast.parse(content)
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


def _analyze_ast(
    tree: ast.AST, file_path: str, lines: list[str], pattern_type: str, search_term: str = None
) -> list[dict]:
    """Analyze AST tree to find patterns."""
    matches = []

    class PatternVisitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node):
            if pattern_type in ["functions"]:
                self._process_function(node)
            if pattern_type == "decorators" and node.decorator_list:
                self._process_decorators(node)
            self.generic_visit(node)

        def visit_AsyncFunctionDef(self, node):
            if pattern_type in ["functions"]:
                self._process_function(node, is_async=True)
            if pattern_type == "decorators" and node.decorator_list:
                self._process_decorators(node)
            self.generic_visit(node)

        def visit_ClassDef(self, node):
            if pattern_type == "classes":
                self._process_class(node)
            self.generic_visit(node)

        def visit_Import(self, node):
            if pattern_type == "imports":
                self._process_import(node)
            self.generic_visit(node)

        def visit_ImportFrom(self, node):
            if pattern_type == "imports":
                self._process_import_from(node)
            self.generic_visit(node)

        def visit_Call(self, node):
            if pattern_type == "calls":
                self._process_call(node)
            self.generic_visit(node)

        def visit_Assign(self, node):
            if pattern_type == "variables":
                self._process_assignment(node)
            self.generic_visit(node)

        def _process_function(self, node, is_async=False):
            if search_term and search_term != node.name:
                return

            docstring = ast.get_docstring(node) or ""
            func_type = "async function" if is_async else "function"

            # Get function signature
            args = []
            for arg in node.args.args:
                args.append(arg.arg)
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

        def _process_class(self, node):
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

        def _process_import(self, node):
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

        def _process_import_from(self, node):
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

        def _process_call(self, node):
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

        def _process_assignment(self, node):
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

        def _process_decorators(self, node):
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


def _add_usage_locations(matches: list[dict], files_to_search: list, pattern_type: str) -> list[dict]:
    """Find where the identified patterns are used in the codebase."""
    if pattern_type in ["calls", "function_call"]:
        return matches  # Calls are already usage locations

    # Create a map of names to find
    names_to_find = {match["name"] for match in matches}

    for file_path_obj in files_to_search:
        try:
            # Ensure we're working with a Path object
            if isinstance(file_path_obj, str):
                file_path_obj = Path(file_path_obj)

            # Skip if not a file
            if not file_path_obj.is_file():
                continue

            with open(file_path_obj, "r", encoding="utf-8") as file:
                lines = file.readlines()

            for line_no, line in enumerate(lines, 1):
                for name in names_to_find:
                    # Simple regex to find usage (can be improved)
                    if re.search(rf"\b{re.escape(name)}\b", line):
                        # Add to all matches with this name
                        for match in matches:
                            if match["name"] == name:
                                # Don't add the definition line as usage
                                if match["file"] == str(file_path_obj) and match["line"] == line_no:
                                    continue

                                match["usage_locations"].append(
                                    {"file": str(file_path_obj), "line": line_no, "context": line.strip()}
                                )

        except (OSError, UnicodeDecodeError, PermissionError) as e:
            continue

    return matches
