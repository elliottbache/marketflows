import numpy as np
import pandas as pd

from marketflows import _helpers


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
        is_unit=True,
    )
    assert (
        column_name
        == original_column
        + "_by_"
        + base_asset
        + "_ema"
        + str(ema_period)
        + "_growth"
        + "_unit"
    )


class TestOrderSuffixes:
    def test_success(self, df_groups):
        column = "amabyderivzon_ema1.5_deriv200_by_china-yuan"
        column_out = _helpers._order_suffixes(column)

        assert column_out == "amabyderivzon_by_china-yuan_ema1.5_deriv200"

    def test_preserves_prefix_underscores(self):
        col = "made_in_usa_growth_by_us-dollar"
        assert _helpers._order_suffixes(col) == "made_in_usa_by_us-dollar_growth"


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


def test_snake_case_to_text_success():
    column = " _amabyderivzon_ema1.5_deriv200_by_china-yuan__"
    column_out = _helpers.snake_case_to_text(column)

    assert column_out == "Amabyderivzon ema1.5 deriv200 by china-yuan"
