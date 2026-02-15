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


def find_first_valid_time(
    df: pd.DataFrame, *, columns: list[str] | None = None
) -> pd.Timestamp | None:
    """Find first valid time for given dataframe.

    For time to be valid, all values in a row must be a number.  If one of the columns
    has no valid data, it will be ignored.  If no columns are supplied, then all
    columns are used.
    """
    if columns is None:
        columns = df.columns.to_list()

    first_indices = df[columns].apply(lambda x: x.first_valid_index())
    valid_indices = first_indices.dropna()
    if valid_indices.empty:
        return None
    else:
        return valid_indices.max()


def find_last_valid_time(df: pd.DataFrame) -> pd.Timestamp | None:
    """Find last valid time for given dataframe.

    For time to be valid, all values in a row must be a number.  If one of the columns
    has no valid data, it will be ignored.
    """
    last_indices = df.apply(lambda x: x.last_valid_index())
    valid_indices = last_indices.dropna()
    if valid_indices.empty:
        return None
    else:
        return valid_indices.max()


def name_column(
    *,
    original_column: str,
    base_asset: str = "us-dollar",
    ema_period: int = 1,
    diff_order: int = 0,
) -> str:
    """Create name for column with base currency."""
    column = str(original_column)
    column += "_by_" + base_asset

    if ema_period > 1:
        column += "_ema" + str(ema_period)

    if diff_order == 0:
        pass
    elif diff_order == 1:
        column += "_growth"
    elif diff_order == 2:
        column += "_inflection"
    else:
        column += "_deriv" + str(diff_order)

    return _order_suffixes(column).strip()


def split_column(column: str) -> dict[str, str]:
    """Take column name and extract its different parameters."""
    substrings = column.split("_")

    column_params = dict()
    column_params["group"] = substrings[0]
    substrings = substrings[1:]
    while len(substrings) > 0:
        if substrings[0] == "by":
            column_params["base_asset"] = substrings[1]
            substrings = substrings[1:]

        elif substrings[0].startswith("ema"):
            column_params["ema_period"] = substrings[0][len("ema") :]

        elif substrings[0].startswith("growth"):
            column_params["diff_order"] = "1"

        elif substrings[0].startswith("inflection"):
            column_params["diff_order"] = "2"

        elif substrings[0].startswith("deriv"):
            column_params["diff_order"] = substrings[0][len("deriv") :]

        elif substrings[0] == "unit":
            column_params["is_unit"] = "True"

        substrings = substrings[1:]

    if "is_unit" not in column_params:
        column_params["is_unit"] = "False"

    return column_params


def _order_suffixes(column: str) -> str:
    """Given a column name with suffixes, return a column with suffixes in deterministic
    order."""
    suffixes = column.split("_")
    prefix = suffixes[0]
    suffixes = suffixes[1:]

    try:
        base_asset = "_" + suffixes[suffixes.index("by") + 1]
    except ValueError:
        base_asset = ""

    diff_order = ""
    for suffix in suffixes:
        if suffix == "growth" or suffix == "inflection" or "deriv" in suffix:
            diff_order = "_" + str(suffix)

    ema_period = ""
    for suffix in suffixes:
        if suffix[:3] == "ema":
            ema_period = "_" + str(suffix)

    return f"{prefix}_by{base_asset}{ema_period}{diff_order}"
