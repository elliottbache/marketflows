"""Helper functions"""

from pathlib import Path

import pandas as pd


def validate_file(file_path: Path) -> None:
    """Validate that file exists and is not directory.

    Raises:
        FileNotFoundError: If file does not exist.
        IsADirectoryError: If is a directory.
    """
    # check that file exists
    if not file_path.exists():
        raise FileNotFoundError(file_path)

    # check that is not a directory
    if file_path.is_dir():
        raise IsADirectoryError(file_path)


def name_column(
    *,
    original_column: str,
    base_asset: str = "us-dollar",
    ema_period: int = 1,
    diff_order: int = 0,
    is_unit: bool = False,
) -> str:
    """Create name for column with base currency, EMA period and diff order.

    Examples:
        >>> name_column(original_column="ai", base_asset="us-dollar", ema_period=3, diff_order=1, is_unit=True)
        'ai_by_us-dollar_ema3_growth_unit'
    """
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

    if is_unit:
        column += "_unit"

    return _order_suffixes(column).strip()


def _order_suffixes(column: str) -> str:
    """Given a column name with suffixes, return a column with suffixes in deterministic
    order."""
    parts = column.split("_")

    prefix_parts: list[str] = []
    base_asset = ""
    ema_period = ""
    diff_order = ""
    is_unit = False

    i = 0
    while i < len(parts):
        p = parts[i]

        if p == "by" and i + 1 < len(parts):
            base_asset = parts[i + 1]
            i += 2
            continue

        if p.startswith("ema"):
            ema_period = p
            i += 1
            continue

        if p in {"growth", "inflection"} or p.startswith("deriv"):
            diff_order = p
            i += 1
            continue

        if p == "unit":
            is_unit = True
            i += 1
            continue

        prefix_parts.append(p)
        i += 1

    prefix = "_".join([x for x in prefix_parts if x])  # drop empty tokens

    out = prefix
    if base_asset:
        out += f"_by_{base_asset}"
    if ema_period:
        out += f"_{ema_period}"
    if diff_order:
        out += f"_{diff_order}"
    if is_unit:
        out += "_unit"

    return out


def find_first_valid_time(
    df: pd.DataFrame, *, columns: list[str] | None = None
) -> pd.Timestamp | None:
    """Find first valid time for given dataframe.

    For time to be valid, all values in a row must be a number.  If one of the columns
    has no valid data, it will be ignored.  If no columns are supplied, then all
    columns are used.

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2020-01-01", periods=3, freq="1s", tz="UTC")
        >>> df = pd.DataFrame({"a": [None, 1.0, 2.0], "b": [None, None, 3.0]}, index=idx)
        >>> find_first_valid_time(df) == idx[2]
        True
    """
    if columns is None:
        columns = df.columns.to_list()

    first_indices = df[columns].apply(lambda x: x.first_valid_index())
    valid_indices = first_indices.dropna()
    if valid_indices.empty:
        return None
    else:
        return valid_indices.max()


def snake_case_to_text(in_text: str) -> str:
    """Convert snake_case text to plain text."""
    if not in_text:
        return ""

    parts = in_text.strip().split("_")
    joined_parts = " ".join(parts).strip()

    if joined_parts:
        out_text = joined_parts[0].upper()
        if len(joined_parts) > 1:
            out_text = out_text + joined_parts[1:]
    else:
        out_text = joined_parts

    return out_text
