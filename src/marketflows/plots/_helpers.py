import logging

import pandas as pd

from marketflows._helpers import find_first_valid_time

_DEFAULT_GROWTH_PERIODS = 50  # periods in growth window
_DEFAULT_INFLECTION_PERIODS = 12  # periods in inflection window


logger = logging.getLogger(__name__)


def define_graph_origin(
    *,
    df: pd.DataFrame,
    groups: list[str] | None = None,
    base_asset: str | None = None,
    ema_period: int | None = None,
    diff_order: int | None = None,
    is_unit: bool = False,
) -> pd.Timestamp:
    """Define the graph origin.

    For:
    - 0th order (market caps): origin is given by the first valid time record for the
      whole df (empty columns should have already been removed)
    - 1st order (market cap growth): origin is 50 periods
    - 2nd order (market cap inflection): origin is 12 periods
    If no diff_order is supplied, then the whole DataFrame window is taken for plotting.

    Args:
        df: DataFrame with all data we want to use
        groups: list of group names that we want to plot.
        base_asset: base asset
        ema_period: ema period
        diff_order: derivative order (1=growth, 2=inflection)
        is_unit: if the data has been normalized by each row

    Returns:
        graph origin Datetime
    """
    group_columns = _make_group_columns(
        df,
        groups=groups,
        base_asset=base_asset,
        ema_period=ema_period,
        diff_order=diff_order,
        is_unit=is_unit,
    )
    if diff_order is None or diff_order == 0:
        graph_origin = find_first_valid_time(df[group_columns])
    elif diff_order == 1:
        graph_origin = _define_shifted_index(
            df=df[group_columns],
            periods=_DEFAULT_GROWTH_PERIODS,
        )
    else:
        graph_origin = _define_shifted_index(
            df=df[group_columns],
            periods=_DEFAULT_INFLECTION_PERIODS,
        )

    if diff_order is not None and diff_order > 2:
        logger.debug(
            f"{_DEFAULT_INFLECTION_PERIODS} used to define chart window for "
            f"{diff_order} derivative."
        )

    if graph_origin is None:
        graph_origin = df.index[0]

    return graph_origin


def _make_group_columns(
    df: pd.DataFrame,
    *,
    groups: list[str] | None = None,
    base_asset: str | None = None,
    ema_period: int | None = None,
    diff_order: int | None = None,
    is_unit: bool | None = None,
) -> list[str]:
    """Create a sublist of columns that have the same parameters."""
    reduced_columns = list()
    for column in df.columns:
        column_params = _split_column(column)

        if groups is not None and column_params["group"] not in groups:
            continue
        if (
            base_asset is not None
            and "base_asset" in column_params
            and column_params["base_asset"] != base_asset
        ):
            continue
        if (
            ema_period is not None
            and "ema_period" in column_params
            and column_params["ema_period"] != str(ema_period)
        ):
            continue
        if (
            diff_order is not None
            and "diff_order" in column_params
            and column_params["diff_order"] != str(diff_order)
        ):
            continue
        if is_unit is not None and "is_unit" in column_params:
            this_is_unit = column_params["is_unit"] == "True"
            if this_is_unit != is_unit:
                continue

        reduced_columns.append(column)

    return reduced_columns


def _split_column(column: str) -> dict[str, str]:
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


def _define_shifted_index(*, df: pd.DataFrame, periods: int) -> pd.Timestamp | None:
    """Shift origin for given periods."""
    last_time = _find_last_valid_time(df)
    if last_time is None:
        return None

    loc = df.index.get_loc(last_time)
    last_index = loc.start if isinstance(loc, slice) else int(loc)
    first_index = last_index - periods if last_index - periods >= 0 else 0
    indices = df.index.to_list()

    return indices[first_index]


def _find_last_valid_time(df: pd.DataFrame) -> pd.Timestamp | None:
    """Find last valid time for given dataframe.

    For time to be valid, all values in a row must be a number.  If one of the columns
    has no valid data, it will be ignored.

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2020-01-01", periods=3, freq="1s", tz="UTC")
        >>> df = pd.DataFrame({"a": [1.0, 2.0, None], "b": [1.0, 2.0, 3.0]}, index=idx)
        >>> _find_last_valid_time(df) == idx[1]
        True
    """
    last_indices = df.apply(lambda x: x.last_valid_index())
    valid_indices = last_indices.dropna()
    if valid_indices.empty:
        return None
    else:
        return valid_indices.min()
