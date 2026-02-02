import numpy as np
import pandas as pd
import pytest

from marketflows.analysis import aggregates


@pytest.fixture
def df_master():
    df = pd.DataFrame()
    df.index = [
        pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC"),
        pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC"),
        pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"),
    ]
    df["bitcoin"] = [1000, 900, 1100]
    df["usd-coin"] = [1001, 901, 1101]
    df["solana"] = [1002, 902, 1102]

    return df


@pytest.fixture
def range_lower_limits():
    return [899, 900, 901]


@pytest.fixture
def df_long(df_master):
    df = pd.DataFrame(
        {
            "asset": sorted(["bitcoin", "solana", "usd-coin"] * 3),
            "market_caps": [1000, 900, 1100, 1002, 902, 1102, 1001, 901, 1101],
            "lower_limit": [
                901.0,
                899.0,
                901.0,
                901.0,
                901.0,
                901.0,
                901.0,
                900.0,
                901.0,
            ],
        },
        index=df_master.index.append(df_master.index.append(df_master.index)),
    )
    df.index.name = "Datetime"

    return df


@pytest.fixture
def df_buckets(df_master):
    df = pd.DataFrame(
        {
            899.0: [np.nan, 900.0, np.nan],
            900.0: [np.nan, 901.0, np.nan],
            901.0: [3003.0, 902.0, 3303.0],
        },
        index=df_master.index,
    )
    df.index.name = "Datetime"

    return df


@pytest.fixture
def df_growth(df_master):
    df = pd.DataFrame(
        {
            899.0: [np.nan, np.nan, 0.666667],
            900.0: [np.nan, np.nan, 0.666667],
            901.0: [np.nan, -1.000000, 0.666667],
        },
        index=df_master.index,
    )
    df.index.name = "Datetime"

    return df


def test_create_master_df_success():
    timestamps1 = [0, 450000, 500000, 600000, 700000, 800000, 900000, 1000000]
    timestamps2 = [410000, 500000, 700000, 800000, 900000, 1010000, 1100000, 1600000]
    market_caps1 = [1000, 910, 1100, 1200, 1300, 1500, 1700, 1800]
    market_caps2 = [1001, 904, 1104, 1202, 1302, 1502, 1702, 1802]
    asset_market_caps = {
        "bitcoin": pd.DataFrame(
            {"timestamps": timestamps1, "market_caps": market_caps1}
        ),
        "ethereum": pd.DataFrame(
            {"timestamps": timestamps2, "market_caps": market_caps2}
        ),
    }
    freq = "5Min"
    min_timestamp = pd.to_datetime(timestamps1[0], unit="ms", utc=True)
    max_timestamp = pd.to_datetime(timestamps2[-1], unit="ms", utc=True)
    df_master = aggregates.create_master_df(
        asset_market_caps,
        freq=freq,
        min_timestamp=min_timestamp,
        max_timestamp=max_timestamp,
    )
    print(list(df_master.index))
    print(df_master)
    assert list(df_master.index) == [
        pd.to_datetime(0.0, unit="ms", utc=True),
        pd.to_datetime(300.0, unit="s", utc=True),
        pd.to_datetime(600.0, unit="s", utc=True),
        pd.to_datetime(900.0, unit="s", utc=True),
        pd.to_datetime(1200.0, unit="s", utc=True),
        pd.to_datetime(1500.0, unit="s", utc=True),
    ]
    assert list(df_master["bitcoin"]) == [1000.0, 940.0, 1200.0, 1700.0, 1800.0, 1800.0]
    assert list(df_master["ethereum"]) == [
        1001.0,
        1001.0,
        1004.0,
        1302.0,
        1722.0,
        1782.0,
    ]


def test_aggregate_groups(df_master):
    group = "mine"
    group_assets = {group: {"bitcoin", "usd-coin"}}
    df_groups = aggregates.aggregate_groups(
        group_assets=group_assets, df_master=df_master
    )

    df_out = pd.DataFrame(index=df_master.index)
    df_out[group] = df_master["bitcoin"] + df_master["usd-coin"]
    assert df_out.equals(df_groups)


def test_validate_assets_raise(df_master):
    assets = {"bitcoin", "ethereum"}
    with pytest.raises(
        ValueError, match="Master DataFrame does not contain required assets in group"
    ):
        aggregates._validate_assets(assets, df_master=df_master)


def test_prepare_cap_ranges_success(range_lower_limits, df_master, df_long):
    df = aggregates.prepare_cap_ranges(
        df_master=df_master, range_lower_limits=range_lower_limits
    )
    df = df.sort_values(by=["asset", "Datetime"])
    assert df_long.equals(df)


def test_define_bucket_assets_success(df_master, range_lower_limits):
    df_master["solana"] = [700, 600, 800]
    bucket_assets = aggregates._define_bucket_assets(
        range_lower_limits, df_master=df_master
    )
    assert bucket_assets <= {"usd-coin", "bitcoin"}


def test_create_long_df_success(df_master, df_long):
    assets = {"bitcoin", "solana", "usd-coin"}
    df = aggregates._create_long_df(df_master=df_master, assets=assets)
    df.index.name = "Datetime"
    df = df.sort_values(by=["asset", "Datetime"])
    df_long = df_long.drop("lower_limit", axis=1)
    assert df_long.equals(df)


def test_aggregate_cap_ranges_success(df_long):
    df_buckets = aggregates.aggregate_cap_ranges(
        df_long=df_long, bucket_column="lower_limit"
    )

    # first row
    expected = pd.Series([np.nan, np.nan, 3003.0], index=df_buckets.columns)
    actual = df_buckets.loc[pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC"), :]
    pd.testing.assert_series_equal(expected, actual, check_names=False)

    # second row
    expected = pd.Series([900.0, 901.0, 902.0], index=df_buckets.columns)
    actual = df_buckets.loc[pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC"), :]
    pd.testing.assert_series_equal(expected, actual, check_names=False)

    # third row
    expected = pd.Series([np.nan, np.nan, 3303.0], index=df_buckets.columns)
    actual = df_buckets.loc[pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"), :]
    pd.testing.assert_series_equal(expected, actual, check_names=False)


def test_aggregate_cap_range_growths_success(df_long):
    df_growth = aggregates.aggregate_cap_range_growths(df_long=df_long)

    # second row
    expected = pd.Series([np.nan, np.nan, -1.000000], index=df_growth.columns)
    actual = df_growth.loc[pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC"), :]
    pd.testing.assert_series_equal(expected, actual, check_names=False)

    # third row
    expected = pd.Series([0.666667, 0.666667, 0.666667], index=df_growth.columns)
    actual = df_growth.loc[pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"), :]
    pd.testing.assert_series_equal(expected, actual, check_names=False)


def test_aggregate_cap_range_inflections_with_defaults_success(df_long):
    """Test where we supply df_buckets_current, df_buckets_prev, df_derivative."""
    df_inflection = aggregates.aggregate_cap_range_inflections(df_long=df_long)

    # third row
    expected = pd.Series([np.nan, np.nan, 0.01], index=df_inflection.columns)
    actual = df_inflection.loc[pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"), :]
    pd.testing.assert_series_equal(expected, actual, check_names=False)
