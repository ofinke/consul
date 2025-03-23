from pathlib import Path


def load_file_content(file_path: str) -> str:
    """
    Loads the content of a file into a single string.

    Args:
        file_path (str): The path to the file, either absolute or relative.

    Returns:
        str: The content of the file as a single string.

    Raises:
        FileNotFoundError: If the file does not exist at the specified path.
        IOError: If an error occurs while reading the file.

    """
    try:
        with Path.open(file_path, encoding="utf-8") as file:
            content = file.read()

    except FileNotFoundError as e:
        msg = f"The file at {file_path} was not found."
        raise FileNotFoundError(msg) from e
    except OSError as e:
        msg = f"An error occurred while reading the file: {e}"
        raise OSError(msg) from e
    else:
        return content
