import numpy as np
import pandas as pd
import pytest

from marketflows.plots import _helpers as plots_helpers


@pytest.mark.parametrize(
    "order, graph_origin",
    [
        (0, pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC")),
        (1, pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC")),
        (2, pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC")),
    ],
)
def test_define_graph_origin(order, graph_origin, df_groups, monkeypatch):
    # set last two records to NaN
    df_groups = df_groups.copy()
    df_groups.loc[pd.Timestamp("1970-01-01 00:20:00+0000", tz="UTC"), :] = np.nan
    df_groups.loc[pd.Timestamp("1970-01-01 00:25:00+0000", tz="UTC"), :] = np.nan

    # reset periods for growth and inflection
    monkeypatch.setattr(plots_helpers, "_DEFAULT_GROWTH_PERIODS", 1)
    monkeypatch.setattr(plots_helpers, "_DEFAULT_INFLECTION_PERIODS", 2)

    origin = plots_helpers.define_graph_origin(df=df_groups, diff_order=order)

    assert origin == graph_origin


class TestFindLastValidTime:
    def test_find_last_valid_time_success(self):
        idx = pd.date_range(
            start="1970-01-01 00:00:00+0000", periods=3, freq="5min", tz="UTC"
        )
        df = pd.DataFrame(
            {"nvidia": [1100, 900, np.nan], "tesla": [1101, np.nan, np.nan]}, index=idx
        )
        last_valid = plots_helpers.find_last_valid_time(df)
        assert last_valid == pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC")

    def test_find_last_valid_time_no_valid(self):
        idx = pd.date_range(
            start="1970-01-01 00:00:00+0000", periods=3, freq="5min", tz="UTC"
        )
        df = pd.DataFrame(
            {"nvidia": [np.nan, np.nan, np.nan], "amazon": [np.nan, np.nan, np.nan]},
            index=idx,
        )
        last_valid = plots_helpers.find_last_valid_time(df)
        assert last_valid is None


def test_create_nice_plot_text():
    plot_title = plots_helpers.create_nice_plot_text(
        text_type="plot_title",
        group="Narratives",
        base_asset="japan-yen",
        ema_period=5,
        diff_order=1,
    )
    assert plot_title == "Narratives MC by japan-yen ema5 growth"

    file_name = plots_helpers.create_nice_plot_text(
        text_type="file_name",
        group="Narratives",
        base_asset="japan-yen",
        ema_period=5,
        diff_order=1,
    )
    assert file_name == "Narratives_MC_by_japan-yen_ema5_growth_smooth10"


def test_split_column_success():
    column = "amabyderivzon_ema1.5_growth_by_china-yuan"
    column_out = plots_helpers.split_column(column)

    assert column_out == {
        "group": "amabyderivzon",
        "base_asset": "china-yuan",
        "ema_period": "1.5",
        "diff_order": "1",
        "is_unit": "False",
    }


def test_make_group_columns_success():
    df = pd.DataFrame(
        {
            "nvidia_by_us-dollar_ema5_growth": [1, 2],
            "nvidia_by_us-dollar_ema15_growth": [1, 2],
            "tesla_by_us-dollar_ema5_growth": [1, 2],
            "tesla_by_us-dollar_ema15_growth": [1, 2],
            "nvidia_by_japan-yen_ema5_growth": [1, 2],
            "nvidia_by_japan-yen_ema15_growth": [1, 2],
        }
    )
    columns = plots_helpers._make_group_columns(
        df, base_asset="us-dollar", ema_period=5
    )
    assert columns == [
        "nvidia_by_us-dollar_ema5_growth",
        "tesla_by_us-dollar_ema5_growth",
    ]


def test_define_shifted_index(df_groups):
    df_groups = df_groups.copy()
    df_groups.loc[pd.Timestamp("1970-01-01 00:25:00+0000", tz="UTC"), :] = np.nan

    last_time = plots_helpers._define_shifted_index(df=df_groups, periods=3)

    assert last_time == pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC")
