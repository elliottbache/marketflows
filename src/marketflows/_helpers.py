"""Helper functions"""

from pathlib import Path


def validate_file(file_path: Path) -> None:

    # check that file exists
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    # check that is not a directory
    if file_path.is_dir():
        raise IsADirectoryError(file_path)
