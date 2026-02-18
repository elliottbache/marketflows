import numpy as np
import pandas as pd

from marketflows import _helpers


class TestFindFirstValidTime:
    def test_find_first_valid_time_success(self):
        idx = pd.date_range(
            start="1970-01-01 00:00:00+0000", periods=3, freq="5min", tz="UTC"
        )
        df = pd.DataFrame({"nvidia": [np.nan, 900, 1100]}, index=idx)
        first_valid = _helpers.find_first_valid_time(df)
        assert first_valid == pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC")

    def test_find_first_valid_time_no_valid(self):
        idx = pd.date_range(
            start="1970-01-01 00:00:00+0000", periods=3, freq="5min", tz="UTC"
        )
        df = pd.DataFrame(
            {"nvidia": [np.nan, np.nan, np.nan], "amazon": [np.nan, np.nan, np.nan]},
            index=idx,
        )
        first_valid = _helpers.find_first_valid_time(df)
        assert first_valid is None


class TestFindLastValidTime:
    def test_find_last_valid_time_success(self):
        idx = pd.date_range(
            start="1970-01-01 00:00:00+0000", periods=3, freq="5min", tz="UTC"
        )
        df = pd.DataFrame(
            {"nvidia": [1100, 900, np.nan], "tesla": [1101, np.nan, np.nan]}, index=idx
        )
        last_valid = _helpers.find_last_valid_time(df)
        assert last_valid == pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC")

    def test_find_last_valid_time_no_valid(self):
        idx = pd.date_range(
            start="1970-01-01 00:00:00+0000", periods=3, freq="5min", tz="UTC"
        )
        df = pd.DataFrame(
            {"nvidia": [np.nan, np.nan, np.nan], "amazon": [np.nan, np.nan, np.nan]},
            index=idx,
        )
        last_valid = _helpers.find_last_valid_time(df)
        assert last_valid is None


def test_name_column_success():
    original_column = "blah"
    base_asset = "nvidia"
    ema_period = 20
    diff_order = 1
    column_name = _helpers.name_column(
        original_column=original_column,
        base_asset=base_asset,
        ema_period=ema_period,
        diff_order=diff_order,
    )
    assert (
        column_name
        == original_column + "_by_" + base_asset + "_ema" + str(ema_period) + "_growth"
    )


def test_split_column_success():
    column = "amabyderivzon_ema1.5_growth_by_china-yuan"
    column_out = _helpers.split_column(column)

    assert column_out == {
        "group": "amabyderivzon",
        "base_asset": "china-yuan",
        "ema_period": "1.5",
        "diff_order": "1",
        "is_unit": "False",
    }


def test_order_suffixes_success(df_groups):
    column = "amabyderivzon_ema1.5_deriv200_by_china-yuan"
    column_out = _helpers._order_suffixes(column)

    assert column_out == "amabyderivzon_by_china-yuan_ema1.5_deriv200"
