import logging
import math
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure, SubFigure

from marketflows._helpers import (
    find_first_valid_time,
    find_last_valid_time,
    name_column,
    split_column,
)

_DEFAULT_GROWTH_PERIODS = 50  # periods in growth window
_DEFAULT_INFLECTION_PERIODS = 12  # periods in inflection window
_DEFAULT_X_SIZE = 6.4 * 1.5  # window horizontal size
_DEFAULT_Y_SIZE = 4.8 * 1.5  # window vertical size
_DEFAULT_PADDING = 0.05  # padding around graph
_DEFAULT_ASSETS_PER_COLUMN = 8  # in the legend

logger = logging.getLogger(__name__)


# plot_all_graphs (don't read data, it should be passed in)
def plot_charts(
    *,
    category: str,
    df: pd.DataFrame,
    groups: list[str],
    symbols: dict[str, str],
    base_assets: list[str],
    diff_orders: list[int],
    ema_periods: list[int],
) -> None:
    """Plot all charts for flow type.

    Args:
        df: DataFrame with all data we want to use
        groups: list of group names that we want to plot.  If the data for a group is
            not in df, this group is not plotted.
        base_assets: list of base assets
        diff_orders: list of derivative orders
        ema_periods: list of ema periods

    """
    """# ERASE ME!!
    import pickle
    with open("plot_charts.pkl", "wb") as f:
        pickle.dump(category, f)
        pickle.dump(df, f)
        pickle.dump(groups, f)
        pickle.dump(symbols, f)
        pickle.dump(base_assets, f)
        pickle.dump(diff_orders, f)
        pickle.dump(ema_periods, f)"""

    """import pickle
    with open("plot_charts.pkl", "rb") as f:
        category = pickle.load(f)
        df = pickle.load(f)
        groups = pickle.load(f)
        symbols = pickle.load(f)
        base_assets = pickle.load(f)
        diff_orders = pickle.load(f)
        ema_periods = pickle.load(f)"""

    for base_asset in base_assets:
        for diff_order in diff_orders:
            for ema_period in ema_periods:
                out_dir = _plot_single_chart(
                    category=category,
                    groups=groups,
                    symbols=symbols,
                    df=df,
                    base_asset=base_asset,
                    ema_period=ema_period,
                    diff_order=diff_order,
                )
                logger.debug(f"{out_dir} created.")


def _plot_single_chart(
    *,
    category: str,
    groups: list[str],
    symbols: dict[str, str],
    df: pd.DataFrame,
    base_asset: str = "us-dollar",
    ema_period: int = 1,
    diff_order: int = 0,
    ax: matplotlib.axes.Axes | None = None,
    out_path: Path | None = None,
) -> Path:
    """Plot single chart."""
    graph_origin = _define_graph_origin(
        df=df,
        groups=groups,
        base_asset=base_asset,
        ema_period=ema_period,
        diff_order=diff_order,
    )

    # enlarge plot
    plt.rcParams["figure.figsize"] = [_DEFAULT_X_SIZE, _DEFAULT_Y_SIZE]

    # create plot
    fig: Figure | SubFigure
    if ax is None:
        fig, ax = plt.subplots()
    else:
        fig = ax.figure

    igroup = 0
    min_mc, max_mc = np.inf, -np.inf
    for group in groups:

        column_name = name_column(
            original_column=group,
            base_asset=base_asset,
            ema_period=ema_period,
            diff_order=diff_order,
        )

        # make sure the column exists since columns without valid records should have
        # been dropped
        if column_name not in df.columns:
            continue

        # make sure that data to be graphed falls within dataframe datetime range
        first_time = graph_origin
        if pd.isnull(first_time):
            first_time = df.index[0]

        x = df.loc[first_time:].index
        y = df.loc[first_time:, column_name]
        if x.empty or y.empty:
            continue

        # update mins and maxes to scale
        min_mc = min(y.min(), min_mc)
        max_mc = max(y.max(), max_mc)

        # define label and marker for legend in plot
        igroup += 1
        marker = _define_marker(igroup)
        label = symbols.get(group, group)

        ax.plot(x, y, marker=marker, label=label)

    # beautify the x-labels
    fig.autofmt_xdate()

    # set limits for y axis
    min_mc = (
        (1 - _DEFAULT_PADDING) * min_mc
        if min_mc > 0
        else (1 + _DEFAULT_PADDING) * min_mc
    )
    max_mc = (
        (1 + _DEFAULT_PADDING) * max_mc
        if max_mc > 0
        else (1 - _DEFAULT_PADDING) * max_mc
    )

    ax.set_ylim(min_mc, max_mc)

    ax.grid(True, which="both")
    ax.legend(loc="upper left", ncol=_define_ncol(groups))
    ax.set_title(
        _create_nice_plot_text(
            text_type="plot_title",
            group=category,
            base_asset=base_asset,
            diff_order=diff_order,
            ema_period=ema_period,
        )
    )

    # create file
    if out_path is None:
        plot_folder = Path("plots")
        if not plot_folder.is_dir():
            Path.mkdir(plot_folder)
        plot_filename = _create_nice_plot_text(
            text_type="file_name",
            group=category,
            base_asset=base_asset,
            diff_order=diff_order,
            ema_period=ema_period,
        )
        out_path = plot_folder / Path(plot_filename + ".png")

    fig.figure.savefig(out_path)
    # plt.show()

    plt.close(fig.figure)

    return out_path


def _define_graph_origin(
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
    group_columns = _group_columns(
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


def _group_columns(
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
        column_params = split_column(column)

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


def _define_marker(idx: int = 0) -> str:
    """Define the marker for this series."""
    if idx % 5 == 0:
        return "o"
    elif idx % 5 == 1:
        return "s"
    elif idx % 5 == 2:
        return "P"
    elif idx % 5 == 3:
        return "v"
    elif idx % 5 == 4:
        return "*"
    else:
        raise ValueError(f"Invalid marker index: {idx}")


def _define_ncol(groups: list[str]) -> int:
    """Define number of columns in legend."""
    return max(1, math.ceil(len(groups) / _DEFAULT_ASSETS_PER_COLUMN))


def _create_nice_plot_text(
    *,
    text_type: str,
    group: str,
    base_asset: str = "us-dollar",
    diff_order: int = 0,
    ema_period: int = 1,
    smooth_periods: int = 10,
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

    Returns:
        string to be used for title or file name
    """
    plot_text = name_column(
        original_column="MC",
        base_asset=base_asset,
        ema_period=ema_period,
        diff_order=diff_order,
    )
    plot_text = group + "_" + plot_text

    if text_type == "file_name":
        if diff_order > 0:
            plot_text += "_smooth" + str(smooth_periods)
    elif text_type == "plot_title":
        plot_text = " ".join(plot_text.split("_"))
    else:
        raise ValueError("text_type must be plot_title or file_name.")

    return plot_text.strip()
