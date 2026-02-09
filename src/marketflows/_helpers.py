"""Helper functions"""

from pathlib import Path

import pandas as pd


def validate_file(file_path: Path) -> None:

    # check that file exists
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    # check that is not a directory
    if file_path.is_dir():
        raise IsADirectoryError(file_path)


def find_first_valid_time(df: pd.DataFrame) -> pd.Timestamp | None:
    """Find first valid time for given dataframe.

    For time to be valid, all values in a row must be a number.  If one of the columns
    has no valid data, it will be ignored.
    """
    first_indices = df.apply(lambda x: x.first_valid_index())
    valid_indices = first_indices.dropna()
    if valid_indices.empty:
        return None
    else:
        return valid_indices.max()
