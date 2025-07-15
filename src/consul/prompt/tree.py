import fnmatch
import os
from pathlib import Path

from consul.prompt.registry import register

HARDCODED_IGNORES: list[str] = [".git", ".DS_Store", "__pycache__", ".venv", ".env"]


def _parse_gitignore(gitignore_path: Path) -> list[str]:
    """
    Parse a .gitignore file and return a list of patterns.

    Args:
        gitignore_path (Path): Path to the .gitignore file.

    Returns:
        list[str]: Patterns specified in the .gitignore file.

    """
    patterns: list[str] = []
    try:
        with gitignore_path.open("r") as f:
            for line in f:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                patterns.append(stripped)
    except FileNotFoundError:
        pass
    return patterns


def _matches_any(patterns: list[str], rel_path: str) -> bool:
    """
    Check if a relative path matches any of the given patterns.

    Args:
        patterns (list[str]): List of glob patterns.
        rel_path (str): Path to check, using '/' as separator.

    Returns:
        bool: True if rel_path matches any pattern, otherwise False.

    """
    for pattern in patterns:
        if "/" in pattern:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
        elif fnmatch.fnmatch(Path(rel_path).name, pattern):
            return True
    return False


@register
def get_project_tree() -> str:
    """
    Generate the folder tree structure from the current working directory,
    respecting .gitignore files and hardcoded ignore patterns.

    Returns:
        str: The string representation of the folder tree.

    """
    root_path: Path = Path.cwd()

    def tree(
        dir_path: Path,
        prefix: str = "",
        accumulated_patterns: list[str] | None = None,
        rel_path: str = "",
    ) -> list[str]:
        """
        Recursively traverse directories and build the tree, with ignore patterns.

        Args:
            dir_path (Path): Directory to traverse.
            prefix (str): Current indentation prefix for pretty-printing.
            accumulated_patterns (list[str]): Patterns inherited from parents.
            rel_path (str): Relative path from root directory.

        Returns:
            list[str]: Tree lines for this directory.

        """
        if accumulated_patterns is None:
            accumulated_patterns = []
        local_gitignore = dir_path / ".gitignore"
        local_patterns = _parse_gitignore(local_gitignore)
        patterns: list[str] = accumulated_patterns + local_patterns + HARDCODED_IGNORES

        try:
            entries = sorted(dir_path.iterdir(), key=lambda p: p.name)
        except PermissionError:
            return []

        # If at the root, skip .gitignore itself
        entries = [
            e for e in entries if not (rel_path == "" and e.name == ".gitignore")
        ]

        kept_entries: list[Path] = []
        for entry in entries:
            rel_entry_path = str(Path(rel_path) / entry.name).replace(os.sep, "/")
            if not _matches_any(patterns, rel_entry_path):
                kept_entries.append(entry)

        lines: list[str] = []
        for idx, entry in enumerate(kept_entries):
            connector = "└─ " if idx == len(kept_entries) - 1 else "├─ "
            lines.append(prefix + connector + entry.name)
            if entry.is_dir():
                extension = "    " if idx == len(kept_entries) - 1 else "│   "
                new_rel_path = str(Path(rel_path) / entry.name).replace(os.sep, "/")
                lines += tree(entry, prefix + extension, patterns, new_rel_path)
        return lines

    result: list[str] = [root_path.name + "/"]
    result += tree(root_path)
    return "\n".join(result)
