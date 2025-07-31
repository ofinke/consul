import ast
import re
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=128)
def find_python_files(project_root: str, file_pattern: str) -> list[Path]:
    """Return a list of Python files matching the pattern under project_root."""
    project_path = Path(project_root).resolve()
    return [f for f in project_path.glob(file_pattern) if f.is_file()]


@lru_cache(maxsize=256)
def read_file_lines(file_path: str) -> list[str]:
    """Read file and return its lines, or raise OSError/UnicodeDecodeError."""
    with Path(file_path).open("r", encoding="utf-8", errors="ignore") as f:
        return f.readlines()


@lru_cache(maxsize=128)
def parse_ast_from_content(content: str) -> ast.Module:
    """Parse AST from file content."""
    return ast.parse(content)


def compile_search_pattern(query: str) -> tuple[re.Pattern, bool]:
    """Compile a regex pattern from the query string."""
    is_regex = query.startswith("/") and query.endswith("/")
    pattern = re.compile(query[1:-1]) if is_regex else re.compile(re.escape(query), re.IGNORECASE)
    return pattern, is_regex
