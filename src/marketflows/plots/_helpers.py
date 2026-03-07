import logging

import numpy as np
import pandas as pd

from marketflows._helpers import find_first_valid_time, name_column
from marketflows.types import FlowType

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


def find_last_valid_time(df: pd.DataFrame) -> pd.Timestamp | None:
    """Find last valid time for given dataframe.

    For time to be valid, all values in a row must be a number.  If one of the columns
    has no valid data, it will be ignored.

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2020-01-01", periods=3, freq="1s", tz="UTC")
        >>> df = pd.DataFrame({"a": [1.0, 2.0, None], "b": [1.0, 2.0, 3.0]}, index=idx)
        >>> find_last_valid_time(df) == idx[1]
        True
    """
    last_indices = df.apply(lambda x: x.last_valid_index())
    valid_indices = last_indices.dropna()
    if valid_indices.empty:
        return None
    else:
        return valid_indices.min()


def create_nice_plot_text(
    *,
    text_type: str,
    group: str,
    base_asset: str = "us-dollar",
    diff_order: int = 0,
    ema_period: int = 1,
    smooth_periods: int = 10,
    is_unit: bool = False,
) -> str:
    """Create nice plot text for title or file name.

    Args:
        text_type: ``plot_title`` or ``file_name``
        group: first string in text
        base_asset: base asset to use
        diff_order: differentiation order
        ema_period: EMA periods (not the smoothing EMA periods)
        smooth_periods: EMA periods used for smoothing after all calculations.  These
            are not used for ranges since EMA periods are not used before
            differentiation as for narratives and asset groups.
        is_unit: is this plot normalized at each time step?

    Returns:
        string to be used for title or file name

    Examples:
        >>> create_nice_plot_text(text_type="file_name", group="narratives")
        'narratives_MC_by_us-dollar'
        >>> create_nice_plot_text(text_type="plot_title", group="narratives")
        'narratives MC by us-dollar'
        >>> create_nice_plot_text(text_type="file_name", group="narratives",
        ...                       diff_order=1, is_unit=True)
        'narratives_MC_by_us-dollar_growth_smooth10_unit'
    """
    plot_text = name_column(
        original_column="MC",
        base_asset=base_asset,
        ema_period=ema_period,
        diff_order=diff_order,
        is_unit=is_unit,
    )
    plot_text = group + "_" + plot_text

    if text_type == "file_name":
        if diff_order > 0:
            # make sure unit comes after smooth
            if len(plot_text) > 5 and plot_text[-5:] == "_unit":
                base = plot_text[:-5]
                plot_text = base + "_smooth" + str(smooth_periods) + "_unit"
            else:
                plot_text += "_smooth" + str(smooth_periods)

    elif text_type == "plot_title":
        plot_text = " ".join(plot_text.split("_"))
    else:
        raise ValueError("text_type must be plot_title or file_name.")

    return plot_text.strip()


def split_column(column: str) -> dict[str, str]:
    """Take column name and extract its different parameters."""
    out = {"ema_period": "1", "diff_order": "0", "is_unit": "False"}

    core = column
    if core.endswith("_unit"):
        out["is_unit"] = "True"
        core = core[: -len("_unit")]

    if "_by_" not in core:
        out["group"] = core
        return out

    group, _, tail = core.partition("_by_")
    out["group"] = group

    parts = tail.split("_")
    if parts:
        out["base_asset"] = parts[0]

    for part in parts[1:]:
        if part.startswith("ema"):
            out["ema_period"] = part[len("ema") :]
        elif part == "growth":
            out["diff_order"] = "1"
        elif part == "inflection":
            out["diff_order"] = "2"
        elif part.startswith("deriv"):
            out["diff_order"] = part[len("deriv") :]

    return out


def create_label(
    *,
    category: str,
    symbols: dict[str, str],
    group: str,
    groups: list[str],
    flow_type: FlowType,
) -> str:
    """Create label.

    Raises:
        ValueError if flow_type is not narratives, market_cap_ranges, or individual_assets.
    """
    if flow_type == "market_cap_ranges":
        idx = groups.index(group)
        upper_limit = groups[idx + 1] if idx < len(groups) - 1 else None
        label = _create_range_label(lower_limit=group, upper_limit=upper_limit)
    elif flow_type == "individual_assets" and category == "Portfolios":
        label = group.capitalize()
    elif flow_type == "individual_assets":
        label = symbols.get(group, group).upper()
    elif flow_type == "narratives":
        if not group:
            return ""
        label = group[0].upper()
        if len(group) > 1:
            label += group[1:]
        label = " ".join(" ".join(label.strip().split("_")).strip().split("-"))
    else:
        raise ValueError(
            "flow_type must be narratives, market_cap_ranges, or individual_assets."
        )

    return label


def _create_range_label(*, lower_limit: str, upper_limit: str | None = None) -> str:
    """Create a range label."""
    if not _is_float(lower_limit):
        raise ValueError("lower_limit must be a float.")
    range_label = _format_market_cap(float(lower_limit))

    range_label += " < MC"

    if upper_limit is not None:
        if not _is_float(upper_limit):
            raise ValueError("upper_limit must be a float.")
        range_label += " < " + _format_market_cap(float(upper_limit))

    return range_label


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
    reduced_columns = []
    for column in df.columns:
        column_params = split_column(column)

        if groups is not None and column_params["group"] not in groups:
            continue
        if base_asset is not None and column_params.get("base_asset") != base_asset:
            continue
        if ema_period is not None and column_params.get("ema_period") != str(
            ema_period
        ):
            continue
        if diff_order is not None and column_params.get("diff_order") != str(
            diff_order
        ):
            continue
        if is_unit is not None and (column_params.get("is_unit") == "True") != is_unit:
            continue

        reduced_columns.append(column)

    return reduced_columns


def _define_shifted_index(*, df: pd.DataFrame, periods: int) -> pd.Timestamp | None:
    """Shift origin for given periods."""
    last_time = find_last_valid_time(df)
    if last_time is None:
        return None

    loc = df.index.get_loc(last_time)
    last_index = loc.start if isinstance(loc, slice) else int(loc)
    first_index = last_index - periods if last_index - periods >= 0 else 0
    indices = df.index.to_list()

    return indices[first_index]


def _is_float(value: str) -> bool:
    try:
        float(value)
        return np.isfinite(float(value))
    except (ValueError, TypeError):
        return False


def _format_market_cap(n: float) -> str:
    """Format a market cap value as an abbreviated string (e.g. 1.2B for 1200000000).

    Raises:
        ValueError if market cap is negative
    """
    if n < 0:
        raise ValueError("Market cap cannot be negative.")

    for unit in ["", "K", "M", "B", "T"]:
        if n < 1000.0:
            # Return as int if it's a clean 100, else 1 decimal
            return f"{int(n)}{unit}" if n == int(n) else f"{n:.1f}{unit}"
        n /= 1000.0
    return f"{n:.1f}P"
