import logging

import numpy as np
import pandas as pd

from marketflows._helpers import _order_suffixes, find_first_valid_time, name_column
from marketflows.analysis.aggregates import (
    aggregate_cap_range_growths,
    aggregate_cap_range_inflections,
    prepare_cap_ranges,
)
from marketflows.config import AnalysisConfig

logger = logging.getLogger(__name__)


def calculate_group_metrics(
    *,
    base_assets: list[str],
    df_base: pd.DataFrame | None = None,
    df_groups: pd.DataFrame,
    analysis_config: AnalysisConfig,
) -> pd.DataFrame:
    """Calculate metrics for groups of or single assets.

    Given a dataframe of assets or groups of assets, normalize with base currency,
    normalize with time, calculate EMAs, calculate derivatives, and
    smooth with EMA (10 by default).  The original data is normalized with the base
    assets.  The derivatives are not normalized with the base assets.

    Args:
        base_assets: list of assets that will be used as base currency (us-dollar is default
            since all data points are in terms of USD)
        df_groups: dataframe with the groups or individual assets for which we are
            calculating metrics
        df_base: dataframe with all base token data
        analysis_config: configuration parameters for analysis module

    Returns:
        dataframe with all columns necessary for plotting

    Raises:
        ValueError: if base_assets are not in df_base
        TypeError: if diff_orders are not all integers
    """
    ema_periods = _initialize_ema_periods(analysis_config.ema_periods)
    diff_orders = _initialize_diff_orders(analysis_config.diff_orders)
    df_base = _initialize_bases(base_assets, df_base)

    df_list = list()
    for base_asset in base_assets:
        # first normalize each group with base assets
        df = _normalize_df_with_base_asset(
            df_groups, base_asset=base_asset, df_base=df_base
        )

        # the data point in the first row that has all valid data
        # (columns with no valid data are not used)
        first_valid_time = find_first_valid_time(df)

        for group in df_groups.columns:
            group_column = name_column(original_column=group, base_asset=base_asset)

            # skip columns with no valid data
            if group_column not in df.columns:
                continue

            # normalize group (for this base asset) with first_valid_time
            first_valid_record = pd.to_numeric(
                df.at[first_valid_time, group_column], errors="coerce"
            )
            if pd.isna(first_valid_record):
                valid_time = find_first_valid_time(df_groups[[group]])
                first_valid_record = df_groups.at[valid_time, group]

            if first_valid_record == 0:
                df[group_column] = np.nan
            else:
                df[group_column] = df[group_column] / first_valid_record

            df = _drop_non_number_columns(df)

            # calculate derivatives of EMAs
            for diff_order in diff_orders:
                for ema_period in ema_periods:
                    if ema_period > 1:
                        df = _calculate_ema(
                            df=df,
                            group=group,
                            base_asset=base_asset,
                            ema_period=ema_period,
                            diff_order=diff_order,
                        )

                    if diff_order > 0:
                        df = _calculate_derivative(
                            df=df,
                            group=group,
                            base_asset=base_asset,
                            ema_period=ema_period,
                            diff_order=diff_order,
                            smooth_ema=analysis_config.smooth_ema,
                        )
        df_list.append(df)

    df_out = pd.concat(df_list, axis=1)

    # add columns normalized with values between 0 and 1 across groups at each timestep
    df_out = pd.concat([df_out, _normalize_by_current_timestep(df_out)], axis=1)

    return df_out


def calculate_range_metrics(
    *,
    base_assets: list[str],
    df_master: pd.DataFrame | None = None,
    df_ranges: pd.DataFrame,
    df_long: pd.DataFrame | None = None,
    range_lower_limits: list[float] | None = None,
    analysis_config: AnalysisConfig | None = None,
) -> pd.DataFrame:
    """Calculate metrics for market cap ranges.

    Given a dataframe of market cap ranges (each range is specified by its lower limit
    e.g. df_ranges.columns = [1e9, 1e10, 1e11]), normalize with base currency,
    normalize with time, calculate up to 2nd derivative, and smooth with EMAs.  The
    data (original, 1st derivative, or 2nd derivative) is normalized with the original
    data for each base asset.

    Args:
        base_assets: list of assets that will be used as base currency (us-dollar is default
            since all data points are in terms of USD)
        df_master: dataframe with all individual asset data
        df_ranges: dataframe with the market cap ranges for which we are
            calculating metrics
        df_long: market caps for all the assets with one master datetime index
            organized into blocks of one asset after another
        range_lower_limits: the lower limits of each of the market cap ranges
        analysis_config: configuration parameters for analysis module


    Returns:
        dataframe with all columns necessary for plotting

    Notes:
        - If the first valid time is not a valid time for a column (this can happen
          when the valid records do not coincide for the base asset and the asset,
          causing a mostly missing record column), the first valid time for that
          column is used instead of the first valid time for all columns
    """
    ema_periods = analysis_config.ema_periods if analysis_config is not None else None
    diff_orders = analysis_config.diff_orders if analysis_config is not None else None

    ema_periods = _initialize_ema_periods(ema_periods)
    diff_orders = _initialize_diff_orders(diff_orders)
    if max(diff_orders) > 2:
        raise ValueError(
            "Differentiation orders larger than 2 for market cap ranges "
            + "are not implemented.  Do you really need these "
            + "differentiation orders?"
        )
    if max(diff_orders) > 0 and (df_long is None or df_long.empty):
        if range_lower_limits is None:
            raise ValueError("Range lower limits cannot be None for market cap ranges")

        if df_master is None:
            raise ValueError("df_master cannot be None for calculating df_long")

        df_long = prepare_cap_ranges(
            range_lower_limits=range_lower_limits, df_master=df_master
        )
    if df_long is None:
        raise ValueError(
            "df_long must be defined for growth and inflection calculations"
        )

    first_valid_times = dict()

    # find first valid time for each base asset
    for base_asset in base_assets:
        # the data point in the first row that has all valid data
        # (columns with no valid data are not used)
        first_valid_times[base_asset] = find_first_valid_time(
            _normalize_df_with_base_asset(
                df_ranges, base_asset=base_asset, df_base=df_master
            )
        )

    df_out = pd.DataFrame(index=df_ranges.index)
    df_list = list()
    # calculate derivatives
    for diff_order in diff_orders:

        match diff_order:
            case 1:
                df_order = aggregate_cap_range_growths(df_long=df_long)
                df_order.columns = df_order.columns.astype(str) + "_growth"
            case 2:
                df_order = aggregate_cap_range_inflections(df_long=df_long)
                df_order.columns = df_order.columns.astype(str) + "_inflection"
            case _:
                df_order = df_ranges

        for base_asset in base_assets:
            # first normalize each range with base assets
            df = _normalize_df_with_base_asset(
                df_order, base_asset=base_asset, df_base=df_master
            )

            first_valid_time = first_valid_times[base_asset]
            for bucket in df_ranges.columns:
                range_column = name_column(
                    original_column=bucket, base_asset=base_asset, diff_order=diff_order
                )

                # skip columns with no valid data
                if range_column not in df.columns or first_valid_time is None:
                    continue

                # define normalizing quantity using first valid record
                first_valid_record = pd.to_numeric(
                    df_ranges.at[first_valid_time, bucket], errors="coerce"
                )
                if pd.isna(first_valid_record):
                    valid_time = find_first_valid_time(df_ranges[[bucket]])
                    first_valid_record = df_ranges.at[valid_time, bucket]

                # normalize bucket (for this base asset) with first_valid_time of
                # original data
                if first_valid_record == 0:
                    df[range_column] = np.nan
                else:
                    df[range_column] = df[range_column] / first_valid_record

                df = _drop_non_number_columns(df)

                # calculate EMAs
                for ema_period in ema_periods:
                    if ema_period > 1:
                        df = _calculate_ema(
                            df=df,
                            group=bucket,
                            base_asset=base_asset,
                            ema_period=ema_period,
                            diff_order=diff_order,
                        )

            df_list.append(df)

    df_out = pd.concat(df_list, axis=1)

    # add columns normalized with values between 0 and 1 across groups at each timestep
    df_out = pd.concat([df_out, _normalize_by_current_timestep(df_out)], axis=1)

    return df_out


def _initialize_ema_periods(ema_periods: list[int] | None = None) -> list[int]:
    """Create EMA period list with 1 (no EMA applied) as the first element.

    Raises:
        TypeError: if EMA periods are not all integers

    Examples:
        >>> _initialize_ema_periods(None)
        [1]
        >>> _initialize_ema_periods([])
        [1]
        >>> _initialize_ema_periods([10, 20])
        [1, 10, 20]
        >>> _initialize_ema_periods([1, 5])
        [1, 5]
    """
    if ema_periods is None or not ema_periods:
        ema_periods = [1]
    else:
        if not all(isinstance(x, int) for x in ema_periods):
            raise TypeError("EMA periods should be integers.")

        if ema_periods[0] != 1:
            ema_periods.insert(0, 1)

    return ema_periods


def _initialize_diff_orders(diff_orders: list[int] | None = None) -> list[int]:
    """Create differentiation orders list with all orders under the highest.

    Raises:
        TypeError: if differentiation orders are not all integers

    Examples:
        >>> _initialize_diff_orders(None)
        [0, 1, 2]
        >>> _initialize_diff_orders([])
        [0, 1, 2]
        >>> _initialize_diff_orders([0])
        [0]
        >>> _initialize_diff_orders([2])
        [0, 1, 2]
        >>> _initialize_diff_orders([1, 3])
        [0, 1, 2, 3]
    """
    if diff_orders is None or not diff_orders:
        return [0, 1, 2]
    else:
        if not all(isinstance(x, int) for x in diff_orders):
            raise TypeError("Differentiation orders should be integers.")

    # intermediate derivatives must be calculated to use _calculate_derivative on
    # higher order derivatives
    diff_orders = list(range(max(diff_orders) + 1))

    return diff_orders


def _initialize_bases(
    base_assets: list[str],
    df_base: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Create base_assets list and df_base DataFrame if not already created.

    Raises:
        ValueError: if base_assets are not in df_base
    """
    for base_asset in base_assets:
        if (
            base_asset != "us-dollar"
            and df_base is not None
            and base_asset not in df_base.columns
        ):
            raise ValueError(f"{base_asset} not in base dataframe.")

    if df_base is None:
        df_base = pd.DataFrame()

    return df_base


def _normalize_df_with_base_asset(
    df_groups: pd.DataFrame,
    *,
    base_asset: str = "us-dollar",
    df_base: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Create a DataFrame with all the columns of df_groups, normalized with the given
    base asset.

    Only include columns with valid data.
    """
    if base_asset == "us-dollar":
        df = _drop_non_number_columns(df_groups)
        df.columns = pd.Index(
            [_order_suffixes(str(column) + "_by_us-dollar") for column in df.columns]
        )
        return df

    if df_base is None:
        df_base = pd.DataFrame()

    if base_asset not in df_base.columns:
        raise ValueError(f"{base_asset} not in dataframe.")

    df = pd.DataFrame(index=df_groups.index)
    for group in df_groups.columns:
        group_column = name_column(original_column=group, base_asset=base_asset)
        df[group_column] = df_groups[group] / df_base[base_asset]
        df = _drop_non_number_columns(df)

    return df


def _drop_non_number_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop columns with non-numeric values (-inf, inf, nan)."""
    df_out = df.replace([np.inf, -np.inf], np.nan)
    df_out = df_out.dropna(axis="columns", how="all")
    dropped_cols = df.columns.difference(df_out.columns).to_list()
    logger.debug(f"Dropped non-numeric columns: {dropped_cols}")

    return df_out


def _calculate_ema(
    *,
    df: pd.DataFrame,
    group: str,
    base_asset: str = "us-dollar",
    ema_period: int = 1,
    diff_order: int = 0,
) -> pd.DataFrame:
    """Calculate EMA data for given dataframe."""
    column = name_column(
        original_column=group,
        base_asset=base_asset,
        ema_period=ema_period,
        diff_order=diff_order,
    )
    if column in df.columns:
        return df

    no_ema_column = name_column(
        original_column=group, base_asset=base_asset, diff_order=diff_order
    )

    df_out = df.copy()
    df_out[column] = (
        df[no_ema_column].ewm(span=ema_period, adjust=False, min_periods=1).mean()
    )
    df_out = _drop_non_number_columns(df_out)

    return df_out


def _calculate_derivative(
    *,
    df: pd.DataFrame,
    group: str,
    base_asset: str = "us-dollar",
    ema_period: int = 1,
    diff_order: int = 1,
    smooth_ema: int | None = 10,
) -> pd.DataFrame:
    """Calculate derivative for given dataframe, smoothing results."""
    column = name_column(
        original_column=group,
        base_asset=base_asset,
        ema_period=ema_period,
        diff_order=diff_order,
    )
    if column in df.columns:
        return df

    integral_column = name_column(
        original_column=group,
        base_asset=base_asset,
        ema_period=ema_period,
        diff_order=diff_order - 1,
    )
    df_out = df.copy()
    diff_series = pd.to_timedelta(df_out.index.to_series().diff())
    dt = diff_series.dt.total_seconds()
    df_out[column] = df_out[integral_column].diff() / dt
    # df[column] = df[integral_column].diff() / (df.index.diff().total_seconds() / interval)

    # smooth out the 1st and 2nd order graphs with EMA10
    if smooth_ema is None:
        smooth_ema = 1
    df_out[column] = _smooth_series(df_out[column], ema_period=smooth_ema)

    df_out = _drop_non_number_columns(df_out)

    return df_out


def _smooth_series(ser: pd.Series, *, ema_period: int | None = 1) -> pd.Series:
    if ema_period is None or ema_period == 1:
        return ser
    else:
        return ser.ewm(span=ema_period, adjust=False, min_periods=1).mean()


def _normalize_by_current_timestep(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalizes each data point with respect to the max and min values for that datetime
    across the different groups.

    If max and min values are the same, we make the normalized values NaN.  Missing
    records are left unchanged.  If a column has no valid values, it is dropped.

    Args:
        df: DataFrame with all groups with datetime indices.

    Returns:
        normalized DataFrame
    """
    # create dict of all suffixes to remove duplicates but keep order
    suffixes = dict.fromkeys(
        [_get_suffix(column) for column in df.columns if "_by" in column]
    )

    # find min and max in each row for each group of suffixes
    mins, maxes = pd.DataFrame(index=df.index), pd.DataFrame(index=df.index)
    for suffix in suffixes:
        mins[suffix] = df.filter(regex=f"{suffix}$").min(axis=1)
        maxes[suffix] = df.filter(regex=f"{suffix}$").max(axis=1)

    # normalize each dataframe using (x - min) / (max - min)
    new_cols = {}
    for column in df.columns:
        suffix = _get_suffix(column)
        denom = maxes[suffix] - mins[suffix]
        unit_series = (df[column] - mins[suffix]) / denom
        new_cols[column + "_unit"] = unit_series.replace([np.inf, -np.inf], np.nan)

    df_out = _drop_non_number_columns(pd.DataFrame(new_cols))

    return df_out


def _get_suffix(column: str) -> str:
    """Given a column name with a suffix, return the suffix.

    Examples:
        >>> _get_suffix("btc_by_us-dollar")
        '_by_us-dollar'
        >>> _get_suffix("1e9_growth_by_us-dollar")
        '_growth_by_us-dollar'
    """
    parts = column.split("_", maxsplit=1)
    if len(parts) < 2:
        raise ValueError("Column must have suffix starting with '_by'.")
    return "_" + parts[1]
