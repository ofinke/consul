import json
from pathlib import Path
from typing import Any

from langchain_core.tools import tool
from loguru import logger


@tool
def save_to_file(file_path: str, content: str) -> dict[str, Any]:
    """
    Saves the content to a new file, creating directories if needed. Cannot overwrite already existing files.
    Allowed suffixes: .md, .json, .yml, .yaml, .txt, .csv.

    Input:
        - file_path(str): relative path to a new file.
        - content(str): content of the new file as a string.

    Returns:
        - dict[str, str]: dictionary informing about the tool runtime status.

    """
    try:
        # setup
        allowed_suffixes = [".md", ".json", ".yml", ".yaml", ".txt", ".csv"]
        file_path = Path(file_path)
        suffix = file_path.suffix.lower()

        # check if the file has allowed suffix.
        if suffix not in allowed_suffixes:
            msg = f"File '{file_path}' not created! Allowed file types: {', '.join(allowed_suffixes)}"
            logger.warning(msg)
            return {"status": "failed", "message": msg}

        # Create parent folders if they don't exist
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if file_path.exists():
            msg = f"File already exists: {file_path}"
            logger.warning(msg)
            return {"status": "failed", "message": msg}

        # If saving JSON, pretty-print if possible
        if suffix == ".json":
            try:
                json_obj = json.loads(content)
                content = json.dumps(json_obj, indent=4, ensure_ascii=False)
            except Exception as e:  # noqa: BLE001
                msg = f"Failed to serialize JSON content: {e}"
                logger.warning(msg)
                return {"status": "failed", "message": msg}

        # save content into a file
        file_path.write_text(content, encoding="utf-8")

    except Exception as e:  # noqa: BLE001
        msg = f"Unexpected exception occured: {e!s}"
        logger.warning(msg)
        return {"status": "failed", "message": msg}
    else:
        return {"status": "success", "message": f"File created at {file_path!s}"}
