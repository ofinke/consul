import re
from pathlib import Path
from typing import LiteralString

import pathspec
from loguru import logger


def load_ignore_patterns(ignore_file: str = ".gitignore") -> pathspec.PathSpec | None:
    """Load ignore patterns from a .gitignore file if it exists."""
    ignore_path = Path(ignore_file)
    if ignore_path.exists():
        with ignore_path.open("r", encoding="utf-8") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    logger.warning("Couldn't resolve .gitignore file.")
    return None


def find(
    pattern_type: LiteralString,
    search_term: str,
    path: str | None = None,
) -> dict:
    """
    Search for a pattern based on path and in all of its subdirectories.

    Args:
        pattern_type (str): what to search for, options: 'filename', 'function', 'class', or 'raw'.
        search_term (str): name to search for
        path (str | None): relative or absolute path to start search in. Defaults to current working directory.

    Returns:
        dict: { "matches": [file paths], "summary": {...} }

    """
    project_path = Path(path).resolve() if path else Path.cwd()
    ignore_spec = load_ignore_patterns(Path.cwd() / ".gitignore")

    # lookup filenames
    if pattern_type == "filename":
        matches = []
        for file_path in project_path.rglob("*"):
            rel_path = file_path.relative_to(project_path)
            if ignore_spec and ignore_spec.match_file(str(rel_path)):
                continue
            if search_term in file_path.name:  # or use regex
                matches.append(str(file_path.resolve()))
        return {"matches": matches}

    # Build regex pattern
    patterns = {
        "function": rf"^\s*def\s+{re.escape(search_term)}\s*\(",
        "class": rf"^\s*class\s+{re.escape(search_term)}\s*(\(|:)",
        "raw": re.escape(search_term),
    }
    regex_pattern = patterns.get(pattern_type, patterns["raw"])

    # Python scanning
    matches = []
    files_scanned = 0
    regex = re.compile(regex_pattern)

    for file_path in project_path.rglob("*.py"):
        rel_path = file_path.relative_to(project_path)
        if ignore_spec and ignore_spec.match_file(str(rel_path)):
            continue
        try:
            with file_path.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if regex.search(line):
                        matches.append(str(file_path))
                        break  # Only need to know the file contains the definition
            files_scanned += 1
        except (OSError, UnicodeDecodeError) as e:
            logger.warning(f"Encountered exception during python file scanning: {e!s}")
            continue

    return {"matches": matches}
