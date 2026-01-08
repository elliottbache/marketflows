"""
Module for secret credentials.
"""

from pathlib import Path

from marketflows._helpers import validate_file

_MAX_KEY_FILE_BYTES = 1024 * 1024


def read_api_key(api_key_path: Path | None = None) -> str:
    """
    Read the API key from file.

    Defaults to ./api_key.txt if no path is provided.  The file should
    only contain the API key and nothing else.

    Args:
        api_key_path  (Path, optional): the API key path. Defaults to None.

    Returns:
         (str): the API key, removing leading and trailing whitespace.

    Raises:
        FileNotFoundError: If the file does not exist.
        IsADirectoryError: If the path is a directory.
        ValueError: If the file is too large or empty.
    """
    # if no file path is provided, then it is api_key.txt in cwd
    if api_key_path is None:
        api_key_path = Path.cwd() / "api_key.txt"

    # check that file is valid
    try:
        validate_file(api_key_path)
    except FileNotFoundError as e:
        raise FileNotFoundError(f"API key file not found. {api_key_path}") from e
    except IsADirectoryError as e:
        raise IsADirectoryError(f"API key file is a directory. {api_key_path}") from e

    # check that file is not larger than allowed read size
    if api_key_path.stat().st_size > _MAX_KEY_FILE_BYTES:
        raise ValueError("API key file too large.")

    api_key = api_key_path.read_text("utf-8").strip()

    # check for empty key
    if not api_key:
        raise ValueError(f"API key is empty. {api_key_path}")

    # remove leading and trailing whitespace and return
    return api_key
