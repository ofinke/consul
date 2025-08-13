import re
from pathlib import Path

import pathspec
from langchain_core.tools import tool


def load_ignore_patterns(ignore_file: str = ".gitignore") -> pathspec.PathSpec | None:
    """Load ignore patterns from a .gitignore file if it exists."""
    ignore_path = Path(ignore_file)
    if ignore_path.exists():
        with ignore_path.open("r", encoding="utf-8") as f:
            return pathspec.PathSpec.from_lines("gitwildmatch", f)
    return None


@tool
def find(
    pattern_type: str,
    search_term: str,
    project_root: str = ".",
) -> dict:
    """
    Find where a definition is located in the project.

    Args:
        pattern_type: 'filename', 'function', 'class', or 'raw'
        search_term: name to search for
        project_root: root directory to search

    Returns:
        dict: { "matches": [file paths], "summary": {...} }

    """
    project_path = Path(project_root).resolve()
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

    # Try grep first if available
    # grep_cmd = shutil.which("grep")
    # if platform.system() == "Linux" and grep_cmd:
    #     try:
    #         result = subprocess.run(
    #             [grep_cmd, "-rlE", regex_pattern, str(project_path)], capture_output=True, text=True, check=False
    #         )
    #         files = [Path(line).resolve() for line in result.stdout.splitlines()]
    #         # Apply ignore filter if needed
    #         if ignore_spec:
    #             files = [f for f in files if not ignore_spec.match_file(str(f.relative_to(project_path)))]
    #         matches = [str(f) for f in files]
    #         return {"matches": [str(f) for f in files]}
    #     # Fall back to Python scanning
    #     except Exception as e:
    #         logger.warning(f"grep command failed: {e!s}, fallback to python regex implementation.")

    # Python fallback scanning
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
        except (OSError, UnicodeDecodeError):
            continue

    return {"matches": matches}
