import numpy as np
import pandas as pd
import pytest

from marketflows.plots import _helpers as plots_helpers


@pytest.fixture
def symbols():
    return {"nvidia": "NVDA", "tesla": "TSLA", "amazon": "AMZN"}


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


@pytest.mark.parametrize(
    "category, group, groups, flow_type, expected",
    [
        (
            "Equities",
            "amazon",
            ["amazon", "tesla", "nvidia"],
            "individual_assets",
            "AMZN",
        ),
        (
            "Equities",
            "alphabet",
            ["amazon", "tesla", "nvidia"],
            "individual_assets",
            "ALPHABET",
        ),
        ("Portfolios", "stocks", ["stocks", "bonds"], "individual_assets", "Stocks"),
        (
            "Ranges",
            "1000000.0",
            ["1000000.0", "10000000.0", "1000000000.0"],
            "market_cap_ranges",
            "1M < MC < 10M",
        ),
        (
            "Ranges",
            "1000000000.0",
            ["1000000.0", "10000000.0", "1000000000.0"],
            "market_cap_ranges",
            "1B < MC",
        ),
        (
            "Narratives",
            "real-estate",
            ["amazon", "tesla", "nvidia"],
            "narratives",
            "Real estate",
        ),
        (
            "Narratives",
            "real_estate",
            ["amazon", "tesla", "nvidia"],
            "narratives",
            "Real estate",
        ),
    ],
    ids=[
        "normal_symbol",
        "group_not_in_symbols",
        "normal_portfolios",
        "normal_range",
        "top_range",
        "dash_narrative",
        "underscore_narrative",
    ],
)
def test_create_label(category, symbols, group, groups, flow_type, expected):
    assert (
        plots_helpers.create_label(
            category=category,
            symbols=symbols,
            group=group,
            groups=groups,
            flow_type=flow_type,
        )
        == expected
    )


@pytest.mark.parametrize(
    "lower_limit, upper_limit, expected, exc, exc_msg",
    [
        ("100000", "10000000", "100K < MC < 10M", None, ""),
        ("1300000000", None, "1.3B < MC", None, ""),
        (
            "-np.inf",
            "10000000",
            "100K < MC < 10M",
            ValueError,
            "lower_limit must be a float",
        ),
        ("100000", "abc", "100K < MC < 10M", ValueError, "upper_limit must be a float"),
    ],
    ids=["normal", "no_upper_limit", "invalid_lower_limit", "invalid_upper_limit"],
)
def test_create_range_label(lower_limit, upper_limit, expected, exc, exc_msg):
    if exc is None:
        assert (
            plots_helpers._create_range_label(
                lower_limit=lower_limit, upper_limit=upper_limit
            )
            == expected
        )
    else:
        with pytest.raises(exc, match=exc_msg):
            plots_helpers._create_range_label(
                lower_limit=lower_limit, upper_limit=upper_limit
            )


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


@pytest.mark.parametrize(
    "value, expected",
    [
        ("123.45", True),
        ("-0.001", True),
        ("1e3", True),
        (".5", True),
        ("nan", False),
        ("NaN", False),
        ("inf", False),
        ("infinity", False),
        ("-np.inf", False),
        ("abc", False),
        ("12.34.56", False),
        (None, False),
        ("", False),
    ],
    ids=[
        "float",
        "negative",
        "scientific",
        "no_leading_decimal",
        "nan",
        "NaN",
        "inf",
        "infinity",
        "-np.inf",
        "plain_text",
        "extra_decimal",
        "None",
        "empty",
    ],
)
def test_is_float(value, expected):
    assert plots_helpers._is_float(value) == expected


@pytest.mark.parametrize(
    "value, expected, exc, exc_msg",
    [
        (1000000000000, "1T", None, None),
        (1000000000, "1B", None, None),
        (100000000, "100M", None, None),
        (1500000, "1.5M", None, None),
        (950000, "950K", None, None),
        (500, "500", None, None),
        (0, "0", None, None),
        (-10, "", ValueError, "Market cap cannot be negative"),
    ],
    ids=["T", "B", "M", "decimal", "K", "no_suffix", "zero", "raise"],
)
def test_format_market_cap(value, expected, exc, exc_msg):
    if exc is None:
        assert plots_helpers._format_market_cap(value) == expected
    else:
        with pytest.raises(exc, match=exc_msg):
            plots_helpers._format_market_cap(value)
