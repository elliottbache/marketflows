import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from matplotlib.table import Table

from marketflows.config import PlotConfig, ProviderConfig
from marketflows.plots import tables as plots_tables
from marketflows.types import FlowType


@pytest.fixture
def hours_ago():
    return [4, 8, 12, 24, 48, 72, 168, 336, 672]


def test_create_category_tables(monkeypatch, df_groups):
    df_groups = df_groups.copy()
    provider_config = ProviderConfig(
        days=1,
        flow_types=["individual_assets"],
        base_assets=["us-dollar", "japan-yen", "china-yuan"],
        asset_groups={"Portfolio1": ["nvidia", "tesla"]},
    )
    plot_config = PlotConfig(hours_ago=[4, 8])

    calls = []

    def mock_create_table(
        *,
        flow_type: FlowType,
        category: str,
        base_asset: str,
        symbols: dict[str, str],
        groups: list[str],
        df: pd.DataFrame,
        hours_ago: list[int],
    ) -> None:
        calls.append(base_asset)

    monkeypatch.setattr(plots_tables, "_create_table", mock_create_table)

    plots_tables.create_category_tables(
        flow_type="narratives",
        category="Narratives",
        symbols={"pharma": "Rx", "ai": "AI"},
        groups=["pharma", "ai"],
        df=df_groups,
        provider_config=provider_config,
        plot_config=plot_config,
    )

    assert len(calls) == len(provider_config.base_assets)
    for idx in range(len(calls)):
        assert calls[idx] == provider_config.base_assets[idx]


class TestCreateTable:
    def test_create_table_adds_lines(self, df_groups, tmp_path, hours_ago):
        df_groups = df_groups.copy()
        df_groups.index = pd.date_range(
            end=pd.Timestamp("1971-01-01 00:00:00+0000", tz="UTC"),
            periods=6,
            freq="100h",
        )
        df_groups = df_groups.rename(
            columns={
                "pharma": "pharma_by_us-dollar",
                "ai": "ai_by_us-dollar",
            }
        )

        fig, ax = plt.subplots()
        out_file = tmp_path / "test.png"
        _ = plots_tables._create_table(
            flow_type="narratives",
            category="Narratives",
            base_asset="us-dollar",
            symbols={"pharma": "Rx", "ai": "AI"},
            groups=["pharma", "ai"],
            df=df_groups,
            hours_ago=hours_ago,
            ax=ax,
            out_path=out_file,
        )

        # assert that a title was added
        assert ax.get_title() is not None

        # assert that the axes were turned off
        assert ax.axison is False

        # check that exactly one table was made
        tables = [child for child in ax.get_children() if isinstance(child, Table)]
        assert len(tables) == 1
        the_table = tables[0]

        # verify table size
        assert (
            len(the_table.get_celld())
            == (len(df_groups.columns) + 1) * (len(hours_ago) + 1) - 1
        )

        plt.close(fig)

    def test_create_table_creates_file(self, df_groups, tmp_path, hours_ago):
        df_groups = df_groups.copy()
        df_groups.index = pd.date_range(
            end=pd.Timestamp("1971-01-01 00:00:00+0000", tz="UTC"),
            periods=6,
            freq="100h",
        )
        df_groups = df_groups.rename(
            columns={"pharma": "pharma_by_us-dollar", "ai": "ai_by_us-dollar"}
        )

        out_file = tmp_path / "test.png"
        out_file = plots_tables._create_table(
            flow_type="narratives",
            category="Narratives",
            base_asset="us-dollar",
            symbols={"pharma": "Rx", "ai": "AI"},
            groups=["pharma", "ai"],
            df=df_groups,
            hours_ago=hours_ago,
            out_path=out_file,
        )
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        assert out_file.suffix == ".png"


@pytest.mark.parametrize(
    "pharma_values, ai_values, pharma_values_exp, ai_values_exp, last_time_exp",
    [
        (
            [1000.0, 900.0, 1100.0, 1200.0, 1300.0, 1500.0],
            [1001.0, 901.0, 1101.0, 1201.0, 1301.0, 1501.0],
            [
                0.53619,
                1.07817,
                1.62602,
                3.30579,
                6.83761,
                10.61947,
                21.75325,
                45.91440,
                np.nan,
            ],
            [
                0.53583,
                1.07744,
                1.62492,
                3.30351,
                6.83274,
                10.61164,
                21.73560,
                45.86978,
                np.nan,
            ],
            pd.Timestamp("1971-01-01 00:00:00+0000", tz="UTC"),
        ),
        (
            [1000.0, 900.0, 1100.0, 1200.0, 1300.0, 0.0],
            [1001.0, 901.0, 1101.0, 1201.0, 1301.0, 1501.0],
            [-100.0, -100.0, -100.0, -100.0, -100.0, -100.0, -100.0, -100.0, np.nan],
            [
                0.53583,
                1.07744,
                1.62492,
                3.30351,
                6.83274,
                10.61164,
                21.73560,
                45.86978,
                np.nan,
            ],
            pd.Timestamp("1971-01-01 00:00:00+0000", tz="UTC"),
        ),
        (
            [1000.0, 900.0, 1100.0, 1200.0, 1300.0, np.nan],
            [1001.0, 901.0, 1101.0, 1201.0, 1301.0, 1501.0],
            [
                0.308642,
                0.619195,
                0.931677,
                1.880878,
                3.833866,
                5.863192,
                14.840989,
                38.888889,
                np.nan,
            ],
            [
                0.3084040092521203,
                0.6187161639597834,
                0.9309542280837859,
                1.8794048551292091,
                3.830806065442937,
                5.8584214808787635,
                14.8278905560459,
                38.847385272145145,
                np.nan,
            ],
            pd.Timestamp("1970-12-27 20:00:00+0000", tz="UTC"),
        ),
        (
            [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
            [1001.0, 901.0, 1101.0, 1201.0, 1301.0, 1501.0],
            [np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan],
            [
                0.53583,
                1.07744,
                1.62492,
                3.30351,
                6.83274,
                10.61164,
                21.73560,
                45.86978,
                np.nan,
            ],
            pd.Timestamp("1971-01-01 00:00:00+0000", tz="UTC"),
        ),
    ],
    ids=["normal", "no_group", "second_to_last_valid_time", "no_valid_records"],
)
def test_calculate_groups_gains(
    df_groups,
    pharma_values,
    ai_values,
    pharma_values_exp,
    ai_values_exp,
    last_time_exp,
    hours_ago,
):
    df_groups = df_groups.copy()
    df_groups.index = pd.date_range(
        end=pd.Timestamp("1971-01-01 00:00:00+0000", tz="UTC"), periods=6, freq="100h"
    )
    df_groups["pharma_by_us-dollar"] = pharma_values
    df_groups["ai_by_us-dollar"] = ai_values

    df_out = plots_tables._calculate_groups_gains(
        groups=["pharma_by_us-dollar", "ai_by_us-dollar"],
        df=df_groups,
        hours_ago=hours_ago,
    )

    df_exp = pd.DataFrame(
        data={
            "pharma_by_us-dollar": pharma_values_exp,
            "ai_by_us-dollar": ai_values_exp,
        },
        index=last_time_exp - pd.to_timedelta(hours_ago, unit="h"),
        dtype=np.float64,
    )
    df_exp = df_exp.dropna(how="all", axis=1)
    print(f"df_exp: {df_exp}")
    pd.testing.assert_frame_equal(df_out, df_exp, atol=1e-4, check_names=False)


@pytest.mark.parametrize(
    "pharma_values, last_time, pharma_values_exp",
    [
        (
            [1000.0, 900.0, 1100.0, 1200.0, 1300.0, 1500.0],
            pd.Timestamp("1971-01-01 00:00:00+0000", tz="UTC"),
            [
                0.53619,
                1.07817,
                1.62602,
                3.30579,
                6.83761,
                10.61947,
                21.75325,
                45.91440,
                np.nan,
            ],
        ),
        (
            [1000.0, 900.0, 1100.0, 1200.0, 1300.0, 0.0],
            pd.Timestamp("1971-01-01 00:00:00+0000", tz="UTC"),
            [-100.0, -100.0, -100.0, -100.0, -100.0, -100.0, -100.0, -100.0, np.nan],
        ),
        (
            [1000.0, 900.0, 1100.0, 1200.0, 1300.0, np.nan],
            pd.Timestamp("1970-12-27 20:00:00+0000", tz="UTC"),
            [
                0.308642,
                0.619195,
                0.931677,
                1.880878,
                3.833866,
                5.863192,
                14.840989,
                38.888889,
                np.nan,
            ],
        ),
    ],
    ids=["normal", "zero_last_value", "missing_last_value"],
)
def test_calculate_gains(
    df_groups, pharma_values, last_time, pharma_values_exp, hours_ago
):
    df_groups = df_groups.copy()
    df_groups.index = pd.date_range(
        end=pd.Timestamp("1971-01-01 00:00:00+0000", tz="UTC"), periods=6, freq="100h"
    )
    df_groups["pharma"] = pharma_values

    # pharma
    ser_out = plots_tables._calculate_gains(
        ser=df_groups["pharma"], hours_ago=hours_ago, last_time=last_time
    )
    ser_exp = pd.Series(
        data=pharma_values_exp,
        index=last_time - pd.to_timedelta(hours_ago, unit="h"),
        dtype=np.float64,
    )
    print(f"ser_exp: {ser_exp}")
    pd.testing.assert_series_equal(ser_out, ser_exp, atol=1e-4, check_names=False)


def test_interpolate_series(df_groups):
    indexes = df_groups.index - pd.to_timedelta(2, unit="m")

    # pharma
    ser_out = plots_tables._interpolate_series(indexes=indexes, ser=df_groups["pharma"])
    ser_exp = pd.Series(
        data=[np.nan, 940.0, 1020.0, 1160.0, 1260.0, 1420.0], index=indexes
    )
    pd.testing.assert_series_equal(ser_out, ser_exp, rtol=1e-6, check_names=False)

    # ai
    ser_out = plots_tables._interpolate_series(indexes=indexes, ser=df_groups["ai"])
    ser_exp = pd.Series(
        data=[np.nan, 941.0, 1021.0, 1161.0, 1261.0, 1421.0], index=indexes
    )
    pd.testing.assert_series_equal(ser_out, ser_exp, rtol=1e-6, check_names=False)
