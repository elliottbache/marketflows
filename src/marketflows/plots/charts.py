import logging
import math
from pathlib import Path
from typing import cast

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from marketflows._helpers import name_column
from marketflows.plots._helpers import create_nice_plot_text, define_graph_origin

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
        category: category of chart used as prefix in title and filename
        df: DataFrame with all data we want to use
        groups: list of group names that we want to plot.  If the data for a group is
            not in df, this group is not plotted.
        symbols: symbol for each asset/group
        base_assets: list of base assets
        diff_orders: list of derivative orders
        ema_periods: list of ema periods

    """
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
    graph_origin = define_graph_origin(
        df=df,
        groups=groups,
        base_asset=base_asset,
        ema_period=ema_period,
        diff_order=diff_order,
    )

    # enlarge plot
    plt.rcParams["figure.figsize"] = [_DEFAULT_X_SIZE, _DEFAULT_Y_SIZE]

    # create plot
    if ax is None:
        fig, ax = plt.subplots(figsize=(_DEFAULT_X_SIZE, _DEFAULT_Y_SIZE))
    else:
        fig = cast(Figure, ax.figure)

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

    if igroup == 0:
        raise ValueError("No series to plot (no matching columns).")

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
        create_nice_plot_text(
            text_type="plot_title",
            group=category,
            base_asset=base_asset,
            diff_order=diff_order,
            ema_period=ema_period,
        )
    )

    # create file
    if out_path is None:
        plot_folder = Path("output_plots")
        plot_folder.mkdir(parents=True, exist_ok=True)
        plot_filename = create_nice_plot_text(
            text_type="file_name",
            group=category,
            base_asset=base_asset,
            diff_order=diff_order,
            ema_period=ema_period,
        )
        out_path = plot_folder / Path(plot_filename + ".png")

    fig.savefig(out_path)
    # plt.show()

    plt.close(fig.figure)

    return out_path


def _define_marker(idx: int = 0) -> str:
    """Define the marker for this series.

    Examples:
        >>> [_define_marker(i) for i in range(5)]
        ['o', 's', 'P', 'v', '*']
    """
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
    """Define number of columns in legend.

    Examples:
        >>> _define_ncol(["a"])
        1
        >>> _define_ncol(list("abcdefgh"))  # 8 assets, 8 per column
        1
        >>> _define_ncol(list("abcdefghi"))  # 9 assets -> 2 columns
        2
    """
    return max(1, math.ceil(len(groups) / _DEFAULT_ASSETS_PER_COLUMN))
