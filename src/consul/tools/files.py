from pathlib import Path

from langchain_core.tools import tool
from loguru import logger


@tool
def save_to_file(path: str, content: str) -> str:
    """Saves the content to a new file, creating directories if needed. Allowed suffixes: .md, .py."""
    # setup
    allowed_suffixes = [".md", ".py"]
    file_path = Path(path)
    suffix = file_path.suffix.lower()

    # check if the file has allowed suffix.
    if suffix not in allowed_suffixes:
        msg = f"File '{file_path}' not created! Allowed file types: {', '.join(allowed_suffixes)}"
        logger.warning(msg)
        return msg

    # Create parent folders if they don't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    if file_path.exists():
        msg = f"File already exists: {file_path}"
        logger.error(msg)
        raise FileExistsError(msg)
    file_path.write_text(content, encoding="utf-8")
    return f"File created at {file_path!s}"
