"""Table rendering.

Generates PNG percent-gain tables over configured time offsets for each category
and base asset.
"""

import datetime
import logging
from pathlib import Path
from typing import cast

import humanize
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colormaps
from matplotlib.figure import Figure

from marketflows._helpers import name_column
from marketflows.config import PlotConfig, ProviderConfig
from marketflows.plots._helpers import (
    create_label,
    create_nice_plot_text,
    find_last_valid_time,
)
from marketflows.types import FlowType

logger = logging.getLogger(__name__)


def create_category_tables(
    *,
    flow_type: FlowType,
    category: str,
    symbols: dict[str, str],
    groups: list[str],
    df: pd.DataFrame,
    provider_config: ProviderConfig,
    plot_config: PlotConfig,
    out_dir: Path,
) -> None:
    """Create tables for the specific category.

    Args:
        flow_type: the flow type we want to collect data for
        category: used as prefix for title and file name
        symbols: symbol for each asset/group
        groups: the labels of the rows in the table
        df: dataframe containing all data (and possibly more)
        provider_config: the configuration settings for providers
        plot_config: the configuration settings for plotting
        out_dir: directory where tables are saved

    Examples:

    """
    for base_asset in provider_config.base_assets:
        _create_table(
            flow_type=flow_type,
            category=category,
            base_asset=base_asset,
            symbols=symbols,
            groups=groups,
            df=df,
            hours_ago=plot_config.hours_ago,
            out_dir=out_dir,
        )


def _create_table(
    *,
    flow_type: FlowType,
    category: str,
    base_asset: str,
    symbols: dict[str, str],
    groups: list[str],
    df: pd.DataFrame,
    hours_ago: list[int],
    out_dir: Path | None = None,
    ax: matplotlib.axes.Axes | None = None,
) -> Path:
    """Create table for the specific category and base_asset."""
    df_gains = _calculate_groups_gains(
        base_asset=base_asset, groups=groups, df=df, hours_ago=hours_ago
    )
    if df_gains.empty:
        logger.warning(
            f"No gains to plot for {category} category and {base_asset} base asset"
        )
        return Path() if out_dir is None else out_dir

    # define column names
    column_names = [
        humanize.naturaldelta(datetime.timedelta(hours=hours)) for hours in hours_ago
    ]

    # define row names
    row_names = df_gains.columns.to_list()
    for idx, row_name in enumerate(row_names):
        row_names[idx] = create_label(
            category=category,
            symbols=symbols,
            group=row_name,
            groups=groups,
            flow_type=flow_type,
        )

    # set up cell colors so that largest magnitude defines deepest red or green.  Colors
    # are "symmetric" around white
    max_val = max(abs(df_gains.min().min()), abs(df_gains.max().max()))
    norm = plt.Normalize(-max_val, max_val)
    cmap = colormaps["RdYlGn"]
    colors = cmap(norm(np.transpose(df_gains.values)))

    # create plot
    if ax is None:
        fig, ax = plt.subplots()
        is_ax = False
    else:
        fig = cast(Figure, ax.figure)
        is_ax = True

    # create table
    rounded_values = np.transpose(np.round(df_gains.values, 1))
    str_values = rounded_values.astype(str)
    cell_values = str_values.tolist()
    the_table = ax.table(
        cellText=cell_values,
        loc="center",
        colLabels=column_names,
        rowLabels=row_names,
        cellLoc="center",
        cellColours=colors,
    )

    # change format
    ax.axis("off")
    the_table.auto_set_font_size(False)
    the_table.set_fontsize(8)

    # set title
    ax.set_title(
        create_nice_plot_text(
            text_type="plot_title",
            group=category,
            base_asset=base_asset,
        )
    )

    # save figure
    if out_dir is None:
        out_dir = Path("output_plots")

    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = "_percent_gains_table.png"
    plot_filename = (
        create_nice_plot_text(
            text_type="file_name",
            group=category,
            base_asset=base_asset,
        )
        + suffix
    )
    out_path = out_dir / Path(plot_filename)

    fig.savefig(out_path, bbox_inches="tight", pad_inches=0.05)

    if not is_ax:
        plt.close(fig)

    return out_path


def _calculate_groups_gains(
    *,
    base_asset: str = "us-dollar",
    groups: list[str],
    df: pd.DataFrame,
    hours_ago: list[int],
) -> pd.DataFrame:
    """Calculate the gains for all groups of a specific category.

    The last valid time for all of these related groups is used to set time offsets.

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2000-01-01", periods=3, freq="h", tz="UTC")
        >>> df = pd.DataFrame(
        ...     {
        ...         "a_by_us-dollar": [100.0, 110.0, 121.0],
        ...         "b_by_us-dollar": [200.0, 180.0, 160.0],
        ...     },
        ...     index=idx,
        ... )
        >>> out = _calculate_groups_gains(
        ...     base_asset="us-dollar",
        ...     groups=["a", "b"],
        ...     df=df,
        ...     hours_ago=[1, 2],
        ... )
        >>> out.round(2).to_dict("list")
        {'a': [10.0, 21.0], 'b': [-11.11, -20.0]}
    """
    # define column names
    col_names = dict()
    for group in groups:
        col_name = name_column(original_column=group, base_asset=base_asset)
        if col_name in df.columns:
            col_names[group] = col_name

    if not col_names:
        logger.warning(f"No group found in dataframe.  Groups: {groups}")
        return pd.DataFrame()

    # find last valid time that has data for all columns (except null columns)
    last_time = find_last_valid_time(df[col_names.values()])
    if last_time is None:
        logger.warning(f"No valid time for all rows.  Groups: {groups}")
        return pd.DataFrame()

    # create dataframe with percent gains for different offsets
    df_gains_list = list()
    for group in groups:
        if group not in col_names:
            continue

        gains = _calculate_gains(
            ser=df.loc[:last_time, col_names[group]],
            hours_ago=hours_ago,
            last_time=last_time,
        )

        # change column name to only leave group for table row labels
        gains.name = group

        if not gains.isna().all():
            df_gains_list.append(gains)

    if df_gains_list:
        return pd.concat(df_gains_list, axis=1)
    else:
        return pd.DataFrame()


def _calculate_gains(
    *, ser: pd.Series, hours_ago: list[int], last_time: pd.Timestamp
) -> pd.Series:
    """Calculate the gains for the specific group with a specific base asset.

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2000-01-01", periods=3, freq="h", tz="UTC")
        >>> ser = pd.Series([100.0, 80.0, 120.0], index=idx)
        >>> out = _calculate_gains(ser=ser, hours_ago=[1, 2], last_time=idx[-1])
        >>> out.round(2).to_list()
        [50.0, 20.0]
    """
    # create DataFrame with indexes at specific times
    hours_ago = hours_ago.copy()
    hours_ago.insert(0, 0)
    idx = last_time - pd.to_timedelta(hours_ago, unit="h")

    # create DataFrame with interpolated values
    gains = _interpolate_series(indexes=idx, ser=ser)

    # calculate % difference with current time for each offset
    gains = (gains.iloc[0] - gains) / gains * 100.0

    # replace inf with nan
    gains.replace([np.inf, -np.inf], np.nan, inplace=True)

    return gains[1:]


def _interpolate_series(*, indexes: pd.DatetimeIndex, ser: pd.Series) -> pd.Series:
    """Interpolate a series using a linear interpolation.

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2000-01-01", periods=2, freq="h", tz="UTC")
        >>> ser = pd.Series([0.0, 10.0], index=idx)
        >>> q = pd.DatetimeIndex([idx[0] + pd.Timedelta(minutes=30)])
        >>> _interpolate_series(indexes=q, ser=ser).iloc[0]
        np.float64(5.0)
    """
    ser = ser.copy().sort_index()
    union_idx = ser.index.union(indexes)
    return ser.reindex(union_idx).interpolate(method="time").loc[indexes]
