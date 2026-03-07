"""Aggregation helpers for analysis.

Builds a master time index, aggregates assets into groups and market-cap ranges,
and prepares long-form data for bucketed range calculations.
"""

import pandas as pd


def create_master_df(
    asset_mcs: dict[str, pd.DataFrame],
    *,
    freq: str,
    min_timestamp: pd.Timestamp,
    max_timestamp: pd.Timestamp,
) -> pd.DataFrame:
    """Create a master dataframe from the asset market caps.

    Creates timestamps from frequency and min timestamp, interpolating the market caps
    of all other assets to these timestamps.

    Args:
        asset_mcs: the asset market caps
        freq: frequency to interpolate to
        min_timestamp: the min timestamp used to create timestamps
        max_timestamp: the max timestamp used to create timestamps

    Returns:
        master dataframe

    Examples:
        >>> import pandas as pd
        >>> asset_mcs = {
        ...     "nvidia": pd.DataFrame(
        ...         {"timestamps": [0, 1000], "market_caps": [10.0, 20.0]}
        ...     )
        ... }
        >>> df = create_master_df(asset_mcs, freq="1s", min_timestamp=pd.Timestamp(0, unit="ms", tz="UTC"), max_timestamp=pd.Timestamp(1000, unit="ms", tz="UTC"))
        >>> df.to_dict("list")
        {'nvidia': [10.0, 20.0]}
        >>> df.index.name
        'Datetime'
    """
    time_index = pd.date_range(
        start=min_timestamp, end=max_timestamp, freq=freq, name="Datetime"
    ).floor("s")
    df_master = pd.DataFrame(index=time_index)

    for asset, asset_mc in asset_mcs.items():
        df_asset = asset_mc.copy()
        df_asset["Datetime"] = pd.to_datetime(
            df_asset["timestamps"], unit="ms", utc=True
        )
        df_asset = df_asset.set_index("Datetime")
        df_asset = df_asset.sort_index()
        df_combined = df_master.join(df_asset[["market_caps"]], how="outer")
        df_combined = df_combined.rename(columns={"market_caps": asset})
        df_combined[asset] = df_combined[asset].interpolate(
            method="time", limit_direction="both"
        )
        df_master = df_combined.reindex(df_master.index)

    return df_master


def aggregate_groups(
    *,
    group_assets: dict[str, set[str]] | None,
    df_master: pd.DataFrame,
) -> pd.DataFrame:
    """Sum market caps of assets from each group together.

    Args:
        group_assets: for each group, the set of assets within it
        df_master: market caps for all the assets with one master datetime index

    Returns:
        dataframe of market caps for each group at each master datetime

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2020-01-01", periods=2, freq="1s", tz="UTC", name="Datetime")
        >>> df_master = pd.DataFrame({"a": [10.0, 11.0], "b": [20.0, 19.0]}, index=idx)
        >>> group_assets = {"grp": {"a", "b"}}
        >>> aggregate_groups(group_assets=group_assets, df_master=df_master).to_dict("list")
        {'grp': [30.0, 30.0]}
    """
    df_groups = pd.DataFrame(index=df_master.index)
    if not group_assets:
        return df_groups
    for group, assets in group_assets.items():
        _validate_assets(assets, df_master=df_master, group=group)
        df_group = df_master[list(assets)]
        df_groups[group] = df_group.sum(axis=1)

    return df_groups


def prepare_cap_ranges(
    *,
    range_lower_limits: list[float],
    df_master: pd.DataFrame,
) -> pd.DataFrame:
    """Prepare data for calculating market cap range values, growth, and inflection.

    Args:
        range_lower_limits: the lower limits of each of the market cap ranges
        df_master: market caps for all the assets with one master datetime index

    Returns:
        DataFrame with each asset after another

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2020-01-01", periods=2, freq="1s", tz="UTC", name="Datetime")
        >>> df_master = pd.DataFrame({"a": [40.0, 60.0], "b": [1.0, 2.0]}, index=idx)
        >>> df_long = prepare_cap_ranges(range_lower_limits=[50.0], df_master=df_master)
        >>> sorted(df_long["asset"].unique().tolist())
        ['a']
        >>> df_long["lower_limit"].dropna().unique().tolist()
        [50.0]
        >>> df_long.index.name
        'Datetime'
    """
    if len(range_lower_limits) == 0:
        return pd.DataFrame()

    # all assets in given ranges
    assets = _define_bucket_assets(range_lower_limits, df_master=df_master)

    # create df with date, asset, market cap
    df_long = _create_long_df(df_master=df_master, assets=assets)

    # assign bucket for each row
    for lower_limit in sorted(range_lower_limits):
        df_long.loc[df_long["market_caps"] > lower_limit, "lower_limit"] = lower_limit

    # define index name
    df_long.index.name = "Datetime"

    return df_long


def _validate_assets(
    assets: set[str], *, df_master: pd.DataFrame, group: str = ""
) -> None:
    """Raise if the assets are not in the master dataframe.

    Examples:
        >>> import pandas as pd
        >>> df_master = pd.DataFrame({"a": [1.0]})
        >>> _validate_assets({"a"}, df_master=df_master, group="ok")  # no error
        >>> _validate_assets({"missing"}, df_master=df_master, group="g1")
        Traceback (most recent call last):
        ...
        ValueError: Master DataFrame does not contain required assets in group.  Group: g1, required assets: {'missing'}
    """
    columns_set = set(df_master.columns)
    if not assets <= columns_set:
        raise ValueError(
            f"Master DataFrame does not contain required assets in group.  "
            f"Group: {group}, required assets: {assets}"
        )


def _define_bucket_assets(
    range_lower_limits: list[float], *, df_master: pd.DataFrame
) -> set[str]:
    """Define all the assets that will be bucketed.

    Args:
        range_lower_limits: the lower limits of each of the market cap ranges
        df_master: market caps for all the assets with one master datetime index

    Returns:
        set of all the assets
    """
    min_limit = min(range_lower_limits)
    bucket_assets = df_master.columns[df_master.iloc[-1] > min_limit].to_list()

    return set(bucket_assets)


def _create_long_df(*, df_master: pd.DataFrame, assets: set[str]) -> pd.DataFrame:
    """Create dataframe with ``Datetime``, ``asset``, and ``market_caps`` headers

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2020-01-01", periods=2, freq="1s", tz="UTC", name="Datetime")
        >>> df_master = pd.DataFrame({"a": [1.0, 2.0], "b": [10.0, 20.0]}, index=idx)
        >>> out = _create_long_df(df_master=df_master, assets={"b", "a"})
        >>> out.columns.tolist()
        ['asset', 'market_caps']
        >>> out["asset"].unique().tolist()
        ['a', 'b']
        >>> out.groupby("asset")["market_caps"].sum().to_dict()
        {'a': 3.0, 'b': 30.0}
    """
    df_list = [
        pd.DataFrame(
            {"asset": asset, "market_caps": df_master[asset]}, index=df_master.index
        )
        for asset in sorted(assets)
    ]
    long_df = pd.concat(df_list)

    return long_df


def aggregate_cap_ranges(
    *, df_long: pd.DataFrame, bucket_column: str = "lower_limit"
) -> pd.DataFrame:
    """Sum market caps of assets from each group together.

    Args:
        df_long: market caps for all the assets with one master datetime index
            organized into blocks of one asset after another
        bucket_column: name of column that contains buckets

    Returns:
        dataframe of market caps for each group at each master datetime

    Examples:
        >>> import pandas as pd
        >>> idx = pd.date_range("2020-01-01", periods=2, freq="1s", tz="UTC", name="Datetime")
        >>> index = pd.Index([idx[0], idx[0], idx[1], idx[1]], name="Datetime")
        >>> df_long = pd.DataFrame(
        ...     {"asset": ["a", "b", "a", "b"], "market_caps": [10.0, 20.0, 11.0, 19.0], "lower_limit": [0.0, 0.0, 0.0, 0.0]},
        ...     index=index,
        ... )
        >>> aggregate_cap_ranges(df_long=df_long).to_dict("list")
        {0.0: [30.0, 30.0]}
    """
    # groupby date, bucket and sum
    group = df_long.groupby(by=["Datetime", bucket_column])["market_caps"].sum()

    # unstack
    df_buckets = group.unstack(level=-1)

    return df_buckets


def aggregate_cap_range_growths(
    *,
    df_long: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate growths for each market cap bucket.

    Args:
        df_long: market caps for all the assets with one master datetime index
            organized into blocks of one asset after another

    Returns:
        dataframe of market cap growths for each bucket at each master datetime
    """
    # add column with lower_limit bucket from previous time step (t-1)
    df_long_prev = df_long.copy()
    df_long_prev["prev_lower_limit"] = df_long_prev.groupby("asset")[
        "lower_limit"
    ].shift(1)

    # create current time step's buckets
    df_buckets = aggregate_cap_ranges(df_long=df_long, bucket_column="lower_limit")

    # create buckets with previous time step's (t-1) lower limits and sum
    df_buckets_prev = aggregate_cap_ranges(
        df_long=df_long_prev, bucket_column="prev_lower_limit"
    )

    # shift buckets and define 2nd derivative terms
    M1 = df_buckets.shift(1)
    M0 = df_buckets_prev

    # calculate time step for derivative = (x1-x0)/(dt)
    diff_series = pd.to_timedelta(df_buckets.index.to_series().diff())
    dt = diff_series.dt.total_seconds()

    df_out = M0 - M1
    df_out = df_out.div(dt, axis=0)

    return df_out


def aggregate_cap_range_inflections(
    *,
    df_long: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate inflections for each market cap bucket.

    Args:
        df_long: market caps for all the assets with one master datetime index
            organized into blocks of one asset after another

    Returns:
        dataframe of market cap inflections for each bucket at each master datetime
    """
    # add column with lower_limit bucket from previous time step (t-1)
    df_long_prev = df_long.copy()
    df_long_prev["prev_lower_limit"] = df_long_prev.groupby("asset")[
        "lower_limit"
    ].shift(1)

    # add column with lower_limit bucket from before previous time step (t-2)
    df_long_prev_prev = df_long.copy()
    df_long_prev_prev["prev_prev_lower_limit"] = df_long_prev_prev.groupby("asset")[
        "lower_limit"
    ].shift(2)

    # create buckets with this time step's t lower limits and sum
    df_buckets = aggregate_cap_ranges(df_long=df_long, bucket_column="lower_limit")

    # create buckets with previous time step's (t-1) lower limits and sum
    df_buckets_prev = aggregate_cap_ranges(
        df_long=df_long_prev, bucket_column="prev_lower_limit"
    )

    # create buckets with before previous time step's (t-2) lower limits and sum
    df_buckets_prev_prev = aggregate_cap_ranges(
        df_long=df_long_prev_prev, bucket_column="prev_prev_lower_limit"
    )

    # shift buckets and define 2nd derivative terms
    M2 = df_buckets.shift(2)
    M1 = df_buckets_prev.shift(1)
    M0 = df_buckets_prev_prev

    # calculate time step for derivative = (x1-x0)/(dt)
    diff_series = pd.to_timedelta(df_buckets.index.to_series().diff())
    dt = diff_series.dt.total_seconds()

    df_out = M0 - 2 * M1 + M2
    df_out = df_out.div(dt.pow(2), axis=0)

    return df_out
