import matplotlib.pyplot as plt

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
    charts.plot_charts(
        category="Narratives",
        df=df_groups,
        groups=["pharma", "ai"],
        symbols={"pharma": "Rx", "ai": "AI"},
        base_assets=["us-dollar"],
        ema_periods=[1, 5],
        diff_orders=[0, 1, 2],
    )

    assert len(calls) == len(["us-dollar"]) * len([0, 1, 2]) * len([1, 5])
    for call in calls:
        assert call["category"] == "Narratives"
        assert call["base_asset"] == "us-dollar"
        assert call["ema_period"] in [1, 5]
        assert call["diff_order"] in [0, 1, 2]
        assert call["groups"] == ["pharma", "ai"]
        assert call["symbols"] == {"pharma": "Rx", "ai": "AI"}


def test_plot_single_chart_adds_lines(df_groups, tmp_path):
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


def test_plot_single_chart_creates_file(df_groups, tmp_path):
    df_groups = df_groups.copy()
    df_groups = df_groups.rename(
        columns={"pharma": "pharma_by_us-dollar", "ai": "ai_by_us-dollar"}
    )
    out_file = tmp_path / "test.png"
    out_file = charts._plot_single_chart(
        category="Narratives",
        groups=["pharma", "ai"],
        symbols={"pharma": "Rx", "ai": "AI"},
        df=df_groups,
        out_path=out_file,
    )
    assert out_file.exists()
    assert out_file.stat().st_size > 0
    assert out_file.suffix == ".png"


def test_create_nice_plot_text():
    plot_title = charts._create_nice_plot_text(
        text_type="plot_title",
        group="Narratives",
        base_asset="japan-yen",
        ema_period=5,
        diff_order=1,
    )
    assert plot_title == "Narratives MC by japan-yen ema5 growth"

    file_name = charts._create_nice_plot_text(
        text_type="file_name",
        group="Narratives",
        base_asset="japan-yen",
        ema_period=5,
        diff_order=1,
    )
    assert file_name == "Narratives_MC_by_japan-yen_ema5_growth_smooth10"
