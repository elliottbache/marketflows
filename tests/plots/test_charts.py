import matplotlib.pyplot as plt
import pytest

from marketflows.config import AnalysisConfig, ProviderConfig
from marketflows.plots import charts


def test_plot_charts_success(df_groups, monkeypatch):

    calls = list()

    def fake_plot_single_chart(**kwargs):
        calls.append(kwargs)
        return "fake.png"

    monkeypatch.setattr(charts, "_plot_single_chart", fake_plot_single_chart)

    df_groups = df_groups.copy()
    df_groups = df_groups.rename(
        columns={"pharma": "pharma_by_us-dollar", "ai": "ai_by_us-dollar"}
    )
    provider_config = ProviderConfig(
        days=1,
        flow_types=["narratives"],
        base_assets=["us-dollar"],
        narratives=["pharma", "ai"],
    )
    analysis_config = AnalysisConfig(
        provider_config=provider_config,
        diff_orders=[0, 1, 2],
        ema_periods=[1, 5],
        smoothing_ema=10,
        is_unit_normalize=True,
    )

    charts.plot_charts(
        flow_type="narratives",
        category="Narratives",
        df=df_groups,
        groups=provider_config.narratives,
        symbols={"pharma": "Rx", "ai": "AI"},
        base_assets=["us-dollar"],
        analysis_config=analysis_config,
    )

    assert len(calls) == len(["us-dollar"]) * len([0, 1, 2]) * len([1, 5]) * 2
    for call in calls:
        assert call["flow_type"] == "narratives"
        assert call["category"] == "Narratives"
        assert call["base_asset"] == "us-dollar"
        assert call["ema_period"] in [1, 5]
        assert call["diff_order"] in [0, 1, 2]
        assert call["groups"] == ["pharma", "ai"]
        assert call["symbols"] == {"pharma": "Rx", "ai": "AI"}


class TestPlotSingleChart:
    def test_plot_single_chart_adds_lines(self, df_groups, tmp_path):
        tmp_file = tmp_path / "test.png"
        df_groups = df_groups.copy()
        df_groups = df_groups.rename(
            columns={
                "pharma": "pharma_by_us-dollar_ema5_growth",
                "ai": "ai_by_us-dollar_ema5_growth",
            }
        )
        fig, ax = plt.subplots()
        _ = charts._plot_single_chart(
            flow_type="narratives",
            category="Narratives",
            groups=["pharma", "ai"],
            symbols={"pharma": "Rx", "ai": "AI"},
            df=df_groups,
            base_asset="us-dollar",
            ema_period=5,
            diff_order=1,
            ax=ax,
            out_path=tmp_file,
        )
        assert len(ax.get_lines()) == len(df_groups.columns)
        assert ax.get_title() is not None
        assert ax.get_legend() is not None
        plt.close(fig)

    def test_plot_single_chart_creates_file(self, df_groups, tmp_path):
        df_groups = df_groups.copy()
        df_groups = df_groups.rename(
            columns={"pharma": "pharma_by_us-dollar", "ai": "ai_by_us-dollar"}
        )
        out_file = tmp_path / "test.png"
        out_file = charts._plot_single_chart(
            flow_type="narratives",
            category="Narratives",
            groups=["pharma", "ai"],
            symbols={"pharma": "Rx", "ai": "AI"},
            df=df_groups,
            out_path=out_file,
        )
        assert out_file.exists()
        assert out_file.stat().st_size > 0
        assert out_file.suffix == ".png"


class TestDefineMarker:
    @pytest.mark.parametrize(
        "idx, expected",
        [
            (0, "o"),
            (1, "s"),
            (2, "P"),
            (3, "v"),
            (4, "*"),
            (5, "o"),  # Test modulo reset
            (10, "o"),  # Test start of third cycle
        ],
        ids=["o", "s", "P", "v", "*", "o_with_second_modulo", "o_with_modulo"],
    )
    def test_define_marker_mapping(self, idx, expected):
        assert charts._define_marker(idx) == expected

    def test_define_marker_is_consistent(self):
        """Ensure the sequence is deterministic across multiple calls."""
        sequence = [charts._define_marker(i) for i in range(5)]
        assert sequence == ["o", "s", "P", "v", "*"]


class TestDefineNcol:
    @pytest.mark.parametrize(
        "num_assets, expected_cols",
        [
            (0, 1),
            (1, 1),
            (8, 1),
            (9, 2),
            (16, 2),
            (17, 3),
        ],
        ids=[
            "empty",
            "one",
            "threshold",
            "threshold_plus_one",
            "two_full_columns",
            "three_columns",
        ],
    )
    def test_define_ncol_logic(self, num_assets, expected_cols):
        test_groups = ["asset"] * num_assets
        assert charts._define_ncol(test_groups) == expected_cols
