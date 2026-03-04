import logging

import numpy as np
import pandas as pd

from marketflows._helpers import _order_suffixes, find_first_valid_time, name_column
from marketflows.analysis.aggregates import (
    aggregate_cap_range_growths,
    aggregate_cap_range_inflections,
    prepare_cap_ranges,
)
from marketflows.config import AnalysisConfig, ProviderConfig

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
        if first_valid_time is None:
            continue

        for group in df_groups.columns:
            ser = _normalize_with_first_time(
                df_by_base=df,
                col=group,
                base_asset=base_asset,
                first_valid_time=first_valid_time,
            )
            if not ser.isna().all():
                df[name_column(original_column=group, base_asset=base_asset)] = ser
            else:
                continue

            # calculate derivatives of EMAs
            for diff_order in analysis_config.diff_orders:
                for ema_period in analysis_config.ema_periods:
                    if ema_period > 1:
                        df = _calculate_ema(
                            df=df,
                            group=group,
                            base_asset=base_asset,
                            ema_period=ema_period,
                        )  # diff_order defaults to 0 and _calculate_ema skips if
                        # already calculated

                    if diff_order > 0:
                        df = _calculate_derivative(
                            df=df,
                            group=group,
                            base_asset=base_asset,
                            ema_period=ema_period,
                            diff_order=diff_order,
                            smoothing_ema=analysis_config.smoothing_ema,
                        )
        df_list.append(df)

    if not df_list:
        return pd.DataFrame(index=df_groups.index)

    df_out = pd.concat(df_list, axis=1)

    # add columns normalized with values between 0 and 1 across groups at each timestep
    if analysis_config.is_unit_normalize:
        df_out = pd.concat([df_out, _normalize_by_current_timestep(df_out)], axis=1)

    return df_out


def calculate_range_metrics(
    *,
    df_master: pd.DataFrame | None = None,
    df_ranges: pd.DataFrame,
    df_long: pd.DataFrame | None = None,
    provider_config: ProviderConfig,
    analysis_config: AnalysisConfig,
) -> pd.DataFrame:
    """Calculate metrics for market cap ranges.

    Given a dataframe of market cap ranges (each range is specified by its lower limit
    e.g. df_ranges.columns = [1e9, 1e10, 1e11]), normalize with base currency,
    normalize with time, calculate up to 2nd derivative, and smooth with EMAs.  The
    data (original, 1st derivative, or 2nd derivative) is normalized with the original
    data for each base asset.

    Args:
        df_master: dataframe with all individual asset data
        df_ranges: dataframe with the market cap ranges for which we are
            calculating metrics
        df_long: market caps for all the assets with one master datetime index
            organized into blocks of one asset after another
        provider_config: configuration parameters for provider module
        analysis_config: configuration parameters for analysis module


    Returns:
        dataframe with all columns necessary for plotting

    Notes:
        - If the first valid time is not a valid time for a column (this can happen
          when the valid records do not coincide for the base asset and the asset,
          causing a mostly missing record column), the first valid time for that
          column is used instead of the first valid time for all columns
    """
    if max(analysis_config.diff_orders) > 2:
        raise ValueError(
            "Differentiation orders larger than 2 for market cap ranges "
            + "are not implemented.  Do you really need these "
            + "differentiation orders?"
        )
    if max(analysis_config.diff_orders) > 0 and (df_long is None or df_long.empty):
        if provider_config.range_lower_limits is None:
            raise ValueError("Range lower limits cannot be None for market cap ranges")

        if df_master is None:
            raise ValueError("df_master cannot be None for calculating df_long")

        df_long = prepare_cap_ranges(
            range_lower_limits=provider_config.range_lower_limits, df_master=df_master
        )

    if df_long is None:
        raise ValueError(
            "df_long must be defined for growth and inflection calculations"
        )

    df_list = list()
    # calculate derivatives
    for diff_order in analysis_config.diff_orders:

        match diff_order:
            case 1:
                df_order = aggregate_cap_range_growths(df_long=df_long)
                df_order.columns = df_order.columns.astype(str) + "_growth"
            case 2:
                df_order = aggregate_cap_range_inflections(df_long=df_long)
                df_order.columns = df_order.columns.astype(str) + "_inflection"
            case 0:
                df_order = df_ranges
            case _:
                logger.warning(
                    f"Market cap ranges {diff_order}th derivative is "
                    f"undefined.  Continuing to next differentiation order."
                )
                continue

        for base_asset in provider_config.base_assets:
            # first normalize each range with base assets
            df = _normalize_df_with_base_asset(
                df_order, base_asset=base_asset, df_base=df_master
            )
            df = _drop_non_number_columns(df)

            df_no_diff = _normalize_df_with_base_asset(
                df_ranges, base_asset=base_asset, df_base=df_master
            )

            surviving_buckets = _find_surviving_buckets(
                df_original=df_ranges,
                df=df,
                base_asset=base_asset,
                diff_order=diff_order,
            )
            if not surviving_buckets:
                continue

            df_survivors = _normalize_df_with_base_asset(
                df_ranges[surviving_buckets], base_asset=base_asset, df_base=df_master
            )

            first_valid_time = find_first_valid_time(df_survivors)
            if first_valid_time is None:
                continue

            for bucket in surviving_buckets:
                ser = _normalize_with_first_time(
                    df_by_base=df,
                    df_no_diff=df_no_diff,
                    col=bucket,
                    base_asset=base_asset,
                    first_valid_time=first_valid_time,
                    diff_order=diff_order,
                )
                if not ser.isna().all():
                    df[
                        name_column(
                            original_column=bucket,
                            base_asset=base_asset,
                            diff_order=diff_order,
                        )
                    ] = ser

                # calculate EMAs
                for ema_period in analysis_config.ema_periods:
                    if ema_period > 1:
                        df = _calculate_ema(
                            df=df,
                            group=bucket,
                            base_asset=base_asset,
                            ema_period=ema_period,
                            diff_order=diff_order,
                        )

            df_list.append(df)

    if not df_list:
        return pd.DataFrame(index=df_ranges.index)

    df_out = pd.concat(df_list, axis=1)

    # add columns normalized with values between 0 and 1 across groups at each timestep
    if analysis_config.is_unit_normalize:
        df_out = pd.concat([df_out, _normalize_by_current_timestep(df_out)], axis=1)

    return df_out


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


def _find_surviving_buckets(
    *, df_original: pd.DataFrame, df: pd.DataFrame, base_asset: str, diff_order: int
) -> list[str]:
    """Make a list of the surviving buckets after differentiation."""
    surviving_buckets = list()
    for bucket in df_original.columns:
        diff_col = name_column(
            original_column=bucket,
            base_asset=base_asset,
            diff_order=diff_order,
        )
        if diff_col in df.columns and not df[diff_col].isna().all():
            surviving_buckets.append(bucket)

    return surviving_buckets


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


def _normalize_with_first_time(
    *,
    df_by_base: pd.DataFrame,
    df_no_diff: pd.DataFrame | None = None,
    col: str,
    base_asset: str,
    first_valid_time: pd.Timestamp,
    diff_order: int = 0,
) -> pd.Series:
    """Normalize series with first valid record.

    First valid record occurs when all non-nan columns have a valid row.
    """
    # get name for column with base asset and without differentiation
    col_by_base_no_diff = name_column(
        original_column=col, base_asset=base_asset, diff_order=0
    )
    col_by_base = name_column(
        original_column=col, base_asset=base_asset, diff_order=diff_order
    )

    if df_no_diff is None:
        df_no_diff = df_by_base.copy()

    # skip columns with no valid data
    if col_by_base not in df_by_base.columns or first_valid_time is None:
        return pd.Series(data=np.nan, index=df_by_base.index)

    # get first valid record from df with base asset at first valid time
    first_valid_record = pd.to_numeric(
        df_no_diff.at[first_valid_time, col_by_base_no_diff], errors="coerce"
    )

    if pd.isna(first_valid_record):
        raise ValueError(f"{first_valid_record} not in {col_by_base} column.")

    # normalize this column by its first valid record
    if first_valid_record == 0:
        ser = pd.Series(data=np.nan, index=df_by_base.index)
    else:
        ser = df_by_base[col_by_base] / first_valid_record

    return ser


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
    smoothing_ema: int | None = 10,
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
    if smoothing_ema is None:
        smoothing_ema = 1
    df_out[column] = _smooth_series(df_out[column], ema_period=smoothing_ema)

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
        [_get_suffix(column) for column in df.columns if "_by_" in column]
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
