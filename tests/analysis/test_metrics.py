import logging

import numpy as np
import pandas as pd
import pytest

from marketflows.analysis import metrics
from marketflows.config import AnalysisConfig


def test_calculate_group_metrics_success(df_master, df_groups):
    # make 2 other base assets
    base_assets = ["us-dollar", "japan-yen", "china-yuan"]
    df_base = pd.DataFrame(index=df_master.index)
    df_base["japan-yen"] = df_master["amazon"] * 2
    df_base["china-yuan"] = df_master["nvidia"] * 2

    # set first record as NaN to force normalization from the second record
    first_index = df_base.index[0]
    df_base.loc[first_index, "japan-yen"] = np.nan

    analysis_config = AnalysisConfig(None, [3], 10)

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
    )
    pd.testing.assert_series_equal(
        df_groups["ai"] / df_groups.loc[first_index, "ai"],
        df["ai_by_us-dollar"],
        check_names=False,
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
    )

    # check that EMAs are correctly calculated
    df_groups_mod = df_groups.copy()
    df_groups_mod["expected_ema"] = [
        1.000000,
        0.950050,
        1.024975,
        1.112388,
        1.206044,
        1.352772,
    ]
    pd.testing.assert_series_equal(
        df_groups_mod["expected_ema"],
        df["ai_by_us-dollar_ema3"],
        atol=1e-6,
        check_names=False,
    )

    # check that 2nd derivative is calculated correctly
    df_groups_mod["expected_diff"] = [
        np.nan,
        np.nan,
        6.054552e-07,
        5.487459e-07,
        4.926431e-07,
        4.754952e-07,
    ]
    pd.set_option("display.max_rows", None)
    print(f"\ndf.columns: \n{df.columns}")
    pd.testing.assert_series_equal(
        df_groups_mod["expected_diff"],
        df["ai_by_us-dollar_inflection"],
        rtol=1e-6,
        check_names=False,
    )

    # check that unit values are correctly calculated
    df_groups_mod["pharma_by_us-dollar_unit"] = [np.nan, 0.0, 1.0, 1.0, 1.0, 1.0]
    df_groups_mod["ai_by_us-dollar_unit"] = [np.nan, 1.0, 0.0, 0.0, 0.0, 0.0]
    pd.testing.assert_series_equal(
        df_groups_mod["pharma_by_us-dollar_unit"],
        df["pharma_by_us-dollar_unit"],
        rtol=1e-6,
        check_names=False,
    )
    pd.testing.assert_series_equal(
        df_groups_mod["ai_by_us-dollar_unit"],
        df["ai_by_us-dollar_unit"],
        rtol=1e-6,
        check_names=False,
    )


class TestCalculateRangeMetrics:
    def test_calculate_range_metrics_success(self, df_master, df_buckets, df_long):
        # make 2 other base assets
        base_assets = ["us-dollar", "japan-yen", "china-yuan"]
        df_master_mod = df_master.copy()
        df_master_mod["japan-yen"] = df_master_mod["amazon"] * 2
        df_master_mod["china-yuan"] = df_master_mod["nvidia"] * 2

        # set first record as NaN to force normalization from the second record
        first_index = df_master_mod.index[0]
        df_master_mod.loc[first_index, "japan-yen"] = np.nan
        second_index = df_master_mod.index[1]
        df_master_mod.loc[second_index, "japan-yen"] = np.nan

        analysis_config = AnalysisConfig([0, 1, 2], [3], 10)

        df = metrics.calculate_range_metrics(
            base_assets=base_assets,
            df_ranges=df_buckets,
            df_long=df_long,
            df_master=df_master_mod,
            analysis_config=analysis_config,
        )

        # check initial columns are normalized and have their names changed correctly
        first_index = df_master_mod.index[1]
        pd.testing.assert_series_equal(
            df_buckets[899.0] / df_buckets.loc[first_index, 899.0],
            df["899.0_by_us-dollar"],
            check_names=False,
        )
        pd.testing.assert_series_equal(
            df_buckets[900.0] / df_buckets.loc[first_index, 900.0],
            df["900.0_by_us-dollar"],
            check_names=False,
        )
        pd.testing.assert_series_equal(
            df_buckets[901.0] / df_buckets.loc[first_index, 901.0],
            df["901.0_by_us-dollar"],
            check_names=False,
        )

        # check that EMAs are correctly calculated
        df_buckets_mod = df_buckets.copy()
        df_buckets_mod["expected_ema"] = [3.329268, 2.164634, 2.913248]
        pd.testing.assert_series_equal(
            df_buckets_mod["expected_ema"],
            df["901.0_by_us-dollar_ema3"],
            atol=1e-6,
            check_names=False,
        )

        # check that 2nd derivative is calculated correctly
        df_buckets_mod["expected_diff"] = [np.nan, np.nan, 1.108647e-05]
        pd.testing.assert_series_equal(
            df_buckets_mod["expected_diff"],
            df["901.0_by_us-dollar_inflection"],
            rtol=1e-6,
            check_names=False,
        )

    def test_calculate_range_metrics_no_long_df_success(self, df_master, df_buckets):
        # make 2 other base assets
        base_assets = ["us-dollar", "amazon", "tesla"]

        analysis_config = AnalysisConfig(None, [3, 20], None)

        df = metrics.calculate_range_metrics(
            base_assets=base_assets,
            df_ranges=df_buckets,
            df_master=df_master,
            analysis_config=analysis_config,
            range_lower_limits=[899.0, 900.0, 901.0],
        )

        # check initial columns are normalized and have their names changed correctly
        first_index = df_master.index[1]
        pd.testing.assert_series_equal(
            df_buckets[899.0] / df_buckets.loc[first_index, 899.0],
            df["899.0_by_us-dollar"],
            check_names=False,
        )
        pd.testing.assert_series_equal(
            df_buckets[900.0] / df_buckets.loc[first_index, 900.0],
            df["900.0_by_us-dollar"],
            check_names=False,
        )
        pd.testing.assert_series_equal(
            df_buckets[901.0] / df_buckets.loc[first_index, 901.0],
            df["901.0_by_us-dollar"],
            check_names=False,
        )

        # check that EMAs are correctly calculated
        first_index = df_master.index[1]
        df_buckets_mod = df_buckets.copy()
        df_buckets_mod["expected_ema"] = [3.329268, 2.164634, 2.913248]
        pd.testing.assert_series_equal(
            df_buckets_mod["expected_ema"],
            df["901.0_by_us-dollar_ema3"],
            atol=1e-6,
            check_names=False,
        )

        # check that 2nd derivative is calculated correctly
        df_buckets_mod["expected_diff"] = [np.nan, np.nan, 1.108647e-05]
        pd.testing.assert_series_equal(
            df_buckets_mod["expected_diff"],
            df["901.0_by_us-dollar_inflection"],
            rtol=1e-6,
            check_names=False,
        )


@pytest.mark.parametrize(
    "ema_periods, ema_periods_out, exc, exc_msg",
    [
        (None, [1], None, None),
        ([1], [1], None, None),
        ([10, 20], [1, 10, 20], None, None),
        ([1.5, 2.5], None, TypeError, "EMA periods should be integers"),
    ],
    ids=["none_emas", "ema1", "multiple emas", "non_int_emas"],
)
def test_initialize_ema_periods(ema_periods, ema_periods_out, exc, exc_msg):
    if exc is None:
        ema_periods_mod = metrics._initialize_ema_periods(ema_periods)
        assert ema_periods_mod == ema_periods_out
    else:
        with pytest.raises(exc, match=exc_msg):
            _ = metrics._initialize_ema_periods(ema_periods)


@pytest.mark.parametrize(
    "diff_orders, diff_orders_out, exc, exc_msg",
    [
        (None, [0, 1, 2], None, None),
        ([], [0, 1, 2], None, None),
        ([1, 3], [0, 1, 2, 3], None, None),
        ([1.5, 2.5], None, TypeError, "Differentiation orders should be integers"),
    ],
    ids=["none_orders", "empty_orders", "multiple emas", "non_int_emas"],
)
def test_initialize_diff_orders(diff_orders, diff_orders_out, exc, exc_msg):
    if exc is None:
        diff_orders_mod = metrics._initialize_diff_orders(diff_orders)
        assert diff_orders_mod == diff_orders_out
    else:
        with pytest.raises(exc, match=exc_msg):
            _ = metrics._initialize_diff_orders(diff_orders)


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


def test_normalize_df_with_base_asset_success(df_master, df_groups):
    base_asset = "japan-yen"
    df_base = pd.DataFrame(index=df_master.index)
    df_base["japan-yen"] = df_master["amazon"] * 2
    df_base["china-yuan"] = df_master["amazon"] * 0
    df_out = metrics._normalize_df_with_base_asset(
        df_groups, base_asset=base_asset, df_base=df_base
    )

    df_groups_mod = df_groups.copy()
    df_groups_mod["expected_pharma_by_japan-yen"] = (
        df_groups_mod["pharma"] / df_base["japan-yen"]
    )
    df_groups_mod["expected_ai_by_japan-yen"] = (
        df_groups_mod["ai"] / df_base["japan-yen"]
    )

    pd.testing.assert_series_equal(
        df_groups_mod["expected_pharma_by_japan-yen"],
        df_out["pharma_by_japan-yen"],
        check_names=False,
    )
    pd.testing.assert_series_equal(
        df_groups_mod["expected_ai_by_japan-yen"],
        df_out["ai_by_japan-yen"],
        check_names=False,
    )
    assert "expected_ai_by_china-yuan" not in df_out.columns


def test_drop_non_number_columns_success(caplog):
    caplog.set_level(logging.DEBUG)
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


def test_calculate_ema_success(df_groups):
    df_groups_mod = df_groups.copy()
    df_groups_mod["expected_ema"] = [1001, 951, 1026, 1113.5, 1207.25, 1354.125]
    group = "ai"
    ema_period = 3
    df_groups_mod = df_groups_mod.rename(columns={"ai": "ai_by_us-dollar"})
    df_groups_mod = df_groups_mod.rename(columns={"pharma": "pharma_by_us-dollar"})

    df_out = metrics._calculate_ema(
        df=df_groups_mod, group=group, ema_period=ema_period
    )

    pd.testing.assert_series_equal(
        df_out["pharma_by_us-dollar"], df_groups_mod["pharma_by_us-dollar"]
    )
    pd.testing.assert_series_equal(
        df_groups_mod["expected_ema"],
        df_out["ai_by_us-dollar_ema3"],
        atol=1e-6,
        check_names=False,
    )


class TestCalculateDerivative:
    def test_calculate_derivative_first_success(self, df_groups):
        df_groups_mod = df_groups.copy()
        df_groups_mod["expected_diff"] = [
            np.nan,
            -0.333333,
            -0.151515,
            -0.063361,
            0.008765,
            0.128384,
        ]
        group = "ai"
        df_groups_mod = df_groups_mod.rename(columns={"ai": "ai_by_us-dollar"})
        df_groups_mod = df_groups_mod.rename(columns={"pharma": "pharma_by_us-dollar"})

        df_out = metrics._calculate_derivative(
            df=df_groups_mod, group=group, diff_order=1
        )

        pd.testing.assert_series_equal(
            df_out["pharma_by_us-dollar"], df_groups_mod["pharma_by_us-dollar"]
        )
        pd.testing.assert_series_equal(
            df_groups_mod["expected_diff"],
            df_out["ai_by_us-dollar_growth"],
            atol=1e-6,
            check_names=False,
        )

    def test_calculate_derivative_second_success(self, df_groups):
        df_groups_mod = df_groups.copy()
        df_groups_mod["expected_diff"] = [
            np.nan,
            np.nan,
            0.000606,
            0.000549,
            0.000493,
            0.000476,
        ]
        group = "ai"
        df_groups_mod["ai_by_us-dollar_growth"] = [
            np.nan,
            -0.333333,
            -0.151515,
            -0.063361,
            0.008765,
            0.128384,
        ]
        df_groups_mod["pharma_by_us-dollar"] = df_groups_mod["pharma"]

        df_out = metrics._calculate_derivative(
            df=df_groups_mod, group=group, diff_order=2
        )

        pd.testing.assert_series_equal(
            df_out["pharma_by_us-dollar"], df_groups_mod["pharma"], check_names=False
        )
        pd.testing.assert_series_equal(
            df_groups_mod["expected_diff"],
            df_out["ai_by_us-dollar_inflection"],
            atol=1e-6,
            check_names=False,
        )


def test_normalize_by_current_timestep_success(df_groups):
    df_groups_mod = df_groups.copy()
    df_groups_mod = df_groups_mod.rename(
        columns={"pharma": "pharma_by_us-dollar", "ai": "ai_by_us-dollar"}
    )
    df_groups_mod["ai_by_us-dollar"] = df_groups_mod["pharma_by_us-dollar"] * 2.0
    df_groups_mod["energy_by_us-dollar"] = df_groups_mod["pharma_by_us-dollar"] * 1.5
    df_groups_mod["pharma_by_us-dollar_growth"] = (
        df_groups_mod["pharma_by_us-dollar"] * 2.0
    )
    df_groups_mod["ai_by_us-dollar_growth"] = df_groups_mod["pharma_by_us-dollar"] * 1.2
    df_groups_mod["energy_by_us-dollar_growth"] = df_groups_mod["pharma_by_us-dollar"]
    df_unit = metrics._normalize_by_current_timestep(df_groups_mod)

    expected = pd.DataFrame(index=df_groups_mod.index)
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
