import logging

import numpy as np
import pandas as pd
import pytest

from marketflows.analysis import metrics
from marketflows.config import AnalysisConfig, ProviderConfig


def test_calculate_group_metrics_success(df_master, df_groups):
    # make 2 other base assets
    base_assets = ["us-dollar", "japan-yen", "china-yuan"]
    df_base = pd.DataFrame(index=df_master.index)
    df_base["japan-yen"] = df_master["amazon"] * 2
    df_base["china-yuan"] = df_master["nvidia"] * 2

    # set first record as NaN to force normalization from the second record
    first_index = df_base.index[0]
    df_base.loc[first_index, "japan-yen"] = np.nan

    analysis_config = AnalysisConfig(
        provider_config=ProviderConfig(
            provider="td-ameritrade",
            days=1,
            flow_types=["narratives"],
            narratives=["ai"],
        ),
        diff_orders=[0, 1, 2],
        ema_periods=[3],
        smoothing_ema=10,
        is_unit_normalize=True,
    )

    df = metrics.calculate_group_metrics(
        base_assets=base_assets,
        df_groups=df_groups,
        df_base=df_base,
        analysis_config=analysis_config,
    )

    # check initial columns are normalized and have their names changed correctly
    pd.testing.assert_series_equal(
        df_groups["pharma"] / df_groups.loc[first_index, "pharma"],
        df["pharma_by_us-dollar"],
        check_names=False,
        rtol=1e-6,
    )
    pd.testing.assert_series_equal(
        df_groups["ai"] / df_groups.loc[first_index, "ai"],
        df["ai_by_us-dollar"],
        check_names=False,
        rtol=1e-6,
    )

    # check that missing record in base assets cause normalizations from second record
    second_index = df_base.index[1]
    pd.testing.assert_series_equal(
        (df_groups["pharma"] / df_base["japan-yen"])
        / (
            df_groups.loc[second_index, "pharma"]
            / df_base.loc[second_index, "japan-yen"]
        ),
        df["pharma_by_japan-yen"],
        check_names=False,
        rtol=1e-6,
    )

    # check that EMAs are correctly calculated
    df_groups = df_groups.copy()
    df_groups["expected_ema"] = [
        1.000000,
        0.950050,
        1.024975,
        1.112388,
        1.206044,
        1.352772,
    ]
    pd.testing.assert_series_equal(
        df_groups["expected_ema"],
        df["ai_by_us-dollar_ema3"],
        atol=1e-6,
        check_names=False,
    )

    # check that 2nd derivative is calculated correctly
    df_groups["expected_diff"] = [
        np.nan,
        np.nan,
        6.054552e-07,
        5.487459e-07,
        4.926431e-07,
        4.754952e-07,
    ]
    pd.testing.assert_series_equal(
        df_groups["expected_diff"],
        df["ai_by_us-dollar_inflection"],
        atol=1e-6,
        check_names=False,
    )

    # check that unit values are correctly calculated
    df_groups["pharma_by_us-dollar_unit"] = [np.nan, 0.0, 1.0, 1.0, 1.0, 1.0]
    df_groups["ai_by_us-dollar_unit"] = [np.nan, 1.0, 0.0, 0.0, 0.0, 0.0]
    pd.testing.assert_series_equal(
        df_groups["pharma_by_us-dollar_unit"],
        df["pharma_by_us-dollar_unit"],
        rtol=1e-6,
        check_names=False,
    )
    pd.testing.assert_series_equal(
        df_groups["ai_by_us-dollar_unit"],
        df["ai_by_us-dollar_unit"],
        rtol=1e-6,
        check_names=False,
    )


class TestCalculateRangeMetrics:
    def test_calculate_range_metrics_success(self, df_master, df_buckets, df_long):
        # make 2 other base assets
        df_master = df_master.copy()
        df_master["japan-yen"] = df_master["amazon"] * 2
        df_master["china-yuan"] = df_master["nvidia"] * 2

        # set first record as NaN to force normalization from the second record
        first_index = df_master.index[0]
        df_master.loc[first_index, "japan-yen"] = np.nan

        provider_config = ProviderConfig(
            provider="td-ameritrade",
            days=1,
            flow_types=["market_cap_ranges"],
            base_assets=["us-dollar", "japan-yen", "china-yuan"],
            asset_groups={"Mine": ["nvidia"]},
            range_lower_limits=[899.0, 900.0, 901.0],
        )

        analysis_config = AnalysisConfig(
            provider_config=provider_config,
            diff_orders=[0, 1, 2],
            ema_periods=[3],
            smoothing_ema=10,
            is_unit_normalize=False,
        )

        df = metrics.calculate_range_metrics(
            df_ranges=df_buckets,
            df_long=df_long,
            df_master=df_master,
            provider_config=provider_config,
            analysis_config=analysis_config,
        )

        # check initial columns are normalized and have their names changed correctly
        first_index = df_master.index[1]
        pd.testing.assert_series_equal(
            df_buckets[899.0] / df_buckets.loc[first_index, 899.0],
            df["899.0_by_us-dollar"],
            check_names=False,
            rtol=1e-6,
        )
        pd.testing.assert_series_equal(
            df_buckets[900.0] / df_buckets.loc[first_index, 900.0],
            df["900.0_by_us-dollar"],
            check_names=False,
            rtol=1e-6,
        )
        pd.testing.assert_series_equal(
            df_buckets[901.0] / df_buckets.loc[first_index, 901.0],
            df["901.0_by_us-dollar"],
            check_names=False,
            rtol=1e-6,
        )

        # check that EMAs are correctly calculated
        df_buckets = df_buckets.copy()
        df_buckets["expected_ema"] = [3.329268, 2.164634, 2.913248]
        pd.testing.assert_series_equal(
            df_buckets["expected_ema"],
            df["901.0_by_us-dollar_ema3"],
            rtol=1e-6,
            check_names=False,
        )

        # check that 2nd derivative is calculated correctly
        df_buckets["expected_diff"] = [np.nan, np.nan, 3.33e-06]
        pd.testing.assert_series_equal(
            df_buckets["expected_diff"],
            df["901.0_by_us-dollar_inflection"],
            rtol=1e-6,
            check_names=False,
        )

    def test_calculate_range_metrics_no_long_df_success(self, df_master, df_buckets):
        # make 2 other base assets

        provider_config = ProviderConfig(
            provider="td-ameritrade",
            days=1,
            flow_types=["market_cap_ranges"],
            base_assets=["us-dollar"],
            asset_groups={"Mine": ["nvidia"]},
            range_lower_limits=[899.0, 900.0, 901.0],
        )

        analysis_config = AnalysisConfig(
            provider_config=provider_config,
            diff_orders=[0, 2],
            ema_periods=[1],
            smoothing_ema=1,
            is_unit_normalize=False,
        )

        df = metrics.calculate_range_metrics(
            df_ranges=df_buckets,
            df_master=df_master,
            analysis_config=analysis_config,
            provider_config=provider_config,
        )

        print(f"\ndf: \n{df}")
        # check initial columns are normalized and have their names changed correctly
        first_index = df_master.index[1]
        pd.testing.assert_series_equal(
            df_buckets[899.0] / df_buckets.loc[first_index, 899.0],
            df["899.0_by_us-dollar"],
            check_names=False,
            rtol=1e-6,
        )
        pd.testing.assert_series_equal(
            df_buckets[900.0] / df_buckets.loc[first_index, 900.0],
            df["900.0_by_us-dollar"],
            check_names=False,
            rtol=1e-6,
        )
        pd.testing.assert_series_equal(
            df_buckets[901.0] / df_buckets.loc[first_index, 901.0],
            df["901.0_by_us-dollar"],
            check_names=False,
            rtol=1e-6,
        )

        """# check that EMAs are correctly calculated
        df_buckets = df_buckets.copy()
        df_buckets["expected_ema"] = [3.329268, 2.164634, 2.913248]
        pd.testing.assert_series_equal(
            df_buckets["expected_ema"],
            df["901.0_by_us-dollar_ema3"],
            rtol=1e-6,
            check_names=False,
        )"""

        # check that 2nd derivative is calculated correctly
        df_buckets["expected_diff"] = [np.nan, np.nan, 3.33e-06]

        pd.testing.assert_series_equal(
            df_buckets["expected_diff"],
            df["901.0_by_us-dollar_inflection"],
            rtol=1e-6,
            check_names=False,
        )


@pytest.mark.parametrize(
    "base_assets, df_base, exc, exc_msg",
    [
        (["us-dollar"], None, None, None),
        (
            ["japan-yen"],
            pd.DataFrame({"china-yuan": [1]}),
            ValueError,
            "not in base dataframe",
        ),
        (["us-dollar"], pd.DataFrame({"china-yuan": [1]}), None, None),
    ],
    ids=[
        "only_dollars_base_assets",
        "base_asset_not_in_df_base",
        "valid_df_base",
    ],
)
def test_initialize_bases(base_assets, df_base, exc, exc_msg):
    if exc is None:
        df_base_actual = metrics._initialize_bases(base_assets, df_base)
        if df_base is None:
            pd.testing.assert_frame_equal(pd.DataFrame(), df_base_actual)
        else:
            pd.testing.assert_frame_equal(df_base, df_base_actual)
    else:
        with pytest.raises(exc, match=exc_msg):
            _ = metrics._initialize_bases(base_assets, df_base)


def test_find_surviving_buckets_success(df_buckets):
    df_original = df_buckets.copy()  # original buckets are the columns of df_buckets

    base_asset = "us-dollar"
    diff_order = 2

    df = pd.DataFrame(
        {
            "899.0_by_us-dollar_inflection": [np.nan, np.nan, np.nan],
            "900.0_by_us-dollar_inflection": [np.nan, np.nan, np.nan],
            "901.0_by_us-dollar_inflection": [np.nan, np.nan, 0.01],
        },
        index=df_buckets.index,
    )

    surviving = metrics._find_surviving_buckets(
        df_original=df_original,
        df=df,
        base_asset=base_asset,
        diff_order=diff_order,
    )

    assert surviving == [901.0]


def test_normalize_df_with_base_asset_success(df_master, df_groups):
    base_asset = "japan-yen"
    df_base = pd.DataFrame(index=df_master.index)
    df_base["japan-yen"] = df_master["amazon"] * 2
    df_base["china-yuan"] = df_master["amazon"] * 0
    df_out = metrics._normalize_df_with_base_asset(
        df_groups, base_asset=base_asset, df_base=df_base
    )

    df_groups = df_groups.copy()
    df_groups["expected_pharma_by_japan-yen"] = (
        df_groups["pharma"] / df_base["japan-yen"]
    )
    df_groups["expected_ai_by_japan-yen"] = df_groups["ai"] / df_base["japan-yen"]

    pd.testing.assert_series_equal(
        df_groups["expected_pharma_by_japan-yen"],
        df_out["pharma_by_japan-yen"],
        check_names=False,
        rtol=1e-6,
    )
    pd.testing.assert_series_equal(
        df_groups["expected_ai_by_japan-yen"],
        df_out["ai_by_japan-yen"],
        check_names=False,
        rtol=1e-6,
    )
    assert "expected_ai_by_china-yuan" not in df_out.columns


def test_drop_non_number_columns_success(caplog):
    caplog.set_level(logging.DEBUG, logger="marketflows.analysis.metrics")
    df = pd.DataFrame(
        {"china-yuan": [1, np.nan, np.inf], "japan-yen": [-np.inf, np.nan, np.inf]}
    )
    df_out = metrics._drop_non_number_columns(df)
    df_expected = df.copy()
    df_expected.loc[2, "china-yuan"] = np.nan
    df_expected = df_expected.drop(columns="japan-yen")
    pd.testing.assert_frame_equal(df_expected, df_out)

    assert "Dropped non-numeric columns:" in caplog.text
    assert "japan-yen" in caplog.text


class TestNormalizeWithFirstTime:
    def test_normalize_with_first_time_without_df_no_diff(self, df_groups):
        base_asset = "japan-yen"
        first_valid_time = "1970-01-01 00:05:00+0000"
        col = "pharma"

        df_by_base = df_groups.copy()
        df_by_base = df_by_base.rename(
            columns={"pharma": "pharma_by_japan-yen", "ai": "ai_by_japan-yen"}
        )
        df_by_base = df_by_base / 2.0

        ser = metrics._normalize_with_first_time(
            df_by_base=df_by_base,
            col=col,
            base_asset=base_asset,
            first_valid_time=first_valid_time,
        )

        # check pharma has been normalized correctly, and ai has not
        pd.testing.assert_series_equal(
            df_by_base["pharma_by_japan-yen"]
            / df_by_base.loc[first_valid_time, "pharma_by_japan-yen"],
            ser,
            check_names=False,
            rtol=1e-6,
        )

    def test_normalize_with_first_time_with_df_no_diff(self, df_groups):
        base_asset = "japan-yen"
        first_valid_time = "1970-01-01 00:05:00+0000"
        col = "pharma"

        df_by_base = df_groups.copy()
        df_by_base = df_by_base.rename(
            columns={"pharma": "pharma_by_japan-yen", "ai": "ai_by_japan-yen"}
        )
        df_by_base = df_by_base / 2.0

        ser = metrics._normalize_with_first_time(
            df_by_base=df_by_base,
            df_no_diff=df_by_base,
            col=col,
            base_asset=base_asset,
            first_valid_time=first_valid_time,
        )

        # check pharma has been normalized correctly
        pd.testing.assert_series_equal(
            df_by_base["pharma_by_japan-yen"]
            / df_by_base.loc[first_valid_time, "pharma_by_japan-yen"],
            ser,
            check_names=False,
            rtol=1e-6,
        )


def test_calculate_ema_success(df_groups):
    df_groups = df_groups.copy()
    df_groups["expected_ema"] = [1001, 951, 1026, 1113.5, 1207.25, 1354.125]
    group = "ai"
    ema_period = 3
    df_groups = df_groups.rename(columns={"ai": "ai_by_us-dollar"})
    df_groups = df_groups.rename(columns={"pharma": "pharma_by_us-dollar"})

    df_out = metrics._calculate_ema(df=df_groups, group=group, ema_period=ema_period)

    pd.testing.assert_series_equal(
        df_out["pharma_by_us-dollar"], df_groups["pharma_by_us-dollar"]
    )
    pd.testing.assert_series_equal(
        df_groups["expected_ema"],
        df_out["ai_by_us-dollar_ema3"],
        rtol=1e-6,
        check_names=False,
    )


class TestCalculateDerivative:
    def test_calculate_derivative_first_success(self, df_groups):
        df_groups = df_groups.copy()
        df_groups["expected_diff"] = [
            np.nan,
            -0.333333,
            -0.151515,
            -0.063361,
            0.008765,
            0.128384,
        ]
        group = "ai"
        df_groups = df_groups.rename(columns={"ai": "ai_by_us-dollar"})
        df_groups = df_groups.rename(columns={"pharma": "pharma_by_us-dollar"})

        df_out = metrics._calculate_derivative(df=df_groups, group=group, diff_order=1)

        pd.testing.assert_series_equal(
            df_out["pharma_by_us-dollar"], df_groups["pharma_by_us-dollar"]
        )
        pd.testing.assert_series_equal(
            df_groups["expected_diff"],
            df_out["ai_by_us-dollar_growth"],
            atol=1e-6,
            check_names=False,
        )

    def test_calculate_derivative_second_success(self, df_groups):
        df_groups = df_groups.copy()
        df_groups["expected_diff"] = [
            np.nan,
            np.nan,
            0.000606,
            0.000549,
            0.000493,
            0.000476,
        ]
        group = "ai"
        df_groups["ai_by_us-dollar_growth"] = [
            np.nan,
            -0.333333,
            -0.151515,
            -0.063361,
            0.008765,
            0.128384,
        ]
        df_groups["pharma_by_us-dollar"] = df_groups["pharma"]

        df_out = metrics._calculate_derivative(df=df_groups, group=group, diff_order=2)

        pd.testing.assert_series_equal(
            df_out["pharma_by_us-dollar"], df_groups["pharma"], check_names=False
        )
        pd.testing.assert_series_equal(
            df_groups["expected_diff"],
            df_out["ai_by_us-dollar_inflection"],
            atol=1e-6,
            check_names=False,
        )


def test_normalize_by_current_timestep_success(df_groups):
    df_groups = df_groups.copy()
    df_groups = df_groups.rename(
        columns={"pharma": "pharma_by_us-dollar", "ai": "ai_by_us-dollar"}
    )
    df_groups["ai_by_us-dollar"] = df_groups["pharma_by_us-dollar"] * 2.0
    df_groups["energy_by_us-dollar"] = df_groups["pharma_by_us-dollar"] * 1.5
    df_groups["pharma_by_us-dollar_growth"] = df_groups["pharma_by_us-dollar"] * 2.0
    df_groups["ai_by_us-dollar_growth"] = df_groups["pharma_by_us-dollar"] * 1.2
    df_groups["energy_by_us-dollar_growth"] = df_groups["pharma_by_us-dollar"]
    df_unit = metrics._normalize_by_current_timestep(df_groups)

    expected = pd.DataFrame(index=df_groups.index)
    expected["pharma_by_us-dollar_unit"] = 0.0
    expected["ai_by_us-dollar_unit"] = 1.0
    expected["energy_by_us-dollar_unit"] = 0.5
    expected["pharma_by_us-dollar_growth_unit"] = 1.0
    expected["ai_by_us-dollar_growth_unit"] = 0.2
    expected["energy_by_us-dollar_growth_unit"] = 0.0

    pd.testing.assert_frame_equal(expected, df_unit)


def test_get_suffix_success():
    column = "amabyderivzon_by_china-yuan_ema1.5_deriv200"
    column_out = metrics._get_suffix(column)

    assert column_out == "_by_china-yuan_ema1.5_deriv200"
