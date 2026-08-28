from contextlib import contextmanager
from importlib import resources
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from marketflows import app
from marketflows.providers.base import ProviderData, ProviderWindow


def _fake_provider(
    *,
    asset_mcs: dict[str, pd.DataFrame] | None = None,
    symbols: dict[str, str] | None = None,
    narrative_assets: dict[str, set[str]] | None = None,
    freq: str = "5min",
    min_timestamp: pd.Timestamp | None = None,
    max_timestamp: pd.Timestamp | None = None,
):
    return SimpleNamespace(
        load_data=lambda: ProviderData(
            asset_mcs=asset_mcs or {},
            symbols=symbols or {},
            narrative_assets=narrative_assets or {},
        ),
        define_window=lambda: ProviderWindow(
            freq=freq,
            min_timestamp=min_timestamp or pd.Timestamp(0.0, unit="ms", tz="UTC"),
            max_timestamp=max_timestamp or pd.Timestamp(1.0, unit="ms", tz="UTC"),
        ),
    )


class TestRunPipeline:
    def test_passes_paths_and_raises_if_api_key_missing(self, tmp_path, monkeypatch):
        config_path = tmp_path / "config.toml"
        secrets_path = tmp_path / "secrets.toml"
        out_dir = tmp_path / "output_plots"

        provider_config = SimpleNamespace(
            provider="coingecko",
            flow_types=[],
            narratives=[],
            asset_groups={},
            range_lower_limits=[],
            base_assets=["us-dollar"],
        )
        analysis_config = SimpleNamespace()
        plot_config = SimpleNamespace()

        seen: dict[str, object] = {}

        def fake_load_and_validate_config(path: Path):
            seen["config_path"] = path
            return provider_config, analysis_config, plot_config

        def fake_get_provider_credentials(provider: str, *, secrets_path: Path):
            seen["provider"] = provider
            seen["secrets_path"] = secrets_path
            return ""  # simulate missing key

        monkeypatch.setattr(
            app, "load_and_validate_config", fake_load_and_validate_config
        )
        monkeypatch.setattr(
            app, "get_provider_credentials", fake_get_provider_credentials
        )

        with pytest.raises(FileNotFoundError, match="API key was not correctly read"):
            app.run_pipeline(
                config_path=config_path, secrets_path=secrets_path, out_dir=out_dir
            )

        assert seen["config_path"] == config_path
        assert seen["provider"] == "coingecko"
        assert seen["secrets_path"] == secrets_path

    def test_queries_provider_and_builds_master_df(
        self, tmp_path, monkeypatch, df_master
    ):
        provider_config = SimpleNamespace(
            provider="coingecko",
            flow_types=[],  # no plotting branches
            narratives=[],
            asset_groups={},
            range_lower_limits=[],
            base_assets=["us-dollar"],
        )
        analysis_config = SimpleNamespace()
        plot_config = SimpleNamespace()

        calls: dict[str, int] = {"load_data": 0, "master": 0}

        monkeypatch.setattr(
            app,
            "load_and_validate_config",
            lambda _p: (provider_config, analysis_config, plot_config),
        )
        monkeypatch.setattr(app, "get_provider_credentials", lambda *_a, **_k: "KEY")

        def fake_create_provider(*, api_key: str, provider_config):
            assert api_key == "KEY"
            calls["load_data"] += 1
            asset_mcs = {
                "nvidia": pd.DataFrame({"timestamps": [0.0], "market_caps": [1000.0]}),
            }
            symbols = {"nvidia": "nvda"}
            narrative_assets = {"ai": {"nvidia"}}
            return _fake_provider(
                asset_mcs=asset_mcs,
                symbols=symbols,
                narrative_assets=narrative_assets,
            )

        monkeypatch.setattr(app, "create_provider", fake_create_provider)

        def fake_create_master_df(
            asset_mcs, *, freq: str, min_timestamp: float, max_timestamp: float
        ):
            calls["master"] += 1
            assert freq == "5min"
            return df_master

        monkeypatch.setattr(app, "create_master_df", fake_create_master_df)

        def should_not_be_called(*args, **kwargs):
            raise AssertionError("should not be called")

        # Ensure no plotting/analyze helpers run in this test
        monkeypatch.setattr(
            app,
            "_create_plots_and_charts",
            should_not_be_called,
        )
        monkeypatch.setattr(
            app,
            "_analyze_group_data",
            should_not_be_called,
        )

        app.run_pipeline(
            config_path=tmp_path / "config.toml",
            secrets_path=tmp_path / "secrets.toml",
            out_dir=tmp_path / "output_plots",
        )

        assert calls["load_data"] == 1
        assert calls["master"] == 1

    def test_narratives_branch(self, tmp_path, monkeypatch, df_master, df_groups):
        provider_config = SimpleNamespace(
            provider="coingecko",
            flow_types=["narratives"],
            narratives=["ai", "pharma"],
            asset_groups={},
            range_lower_limits=[],
            base_assets=["us-dollar"],
        )
        analysis_config = SimpleNamespace()
        plot_config = SimpleNamespace()

        monkeypatch.setattr(
            app,
            "load_and_validate_config",
            lambda _p: (provider_config, analysis_config, plot_config),
        )
        monkeypatch.setattr(app, "get_provider_credentials", lambda *_a, **_k: "KEY")
        monkeypatch.setattr(
            app,
            "create_provider",
            lambda **_k: _fake_provider(
                symbols={"ai": "AI"},
                narrative_assets={"ai": {"nvidia"}, "pharma": {"tesla"}},
            ),
        )
        monkeypatch.setattr(app, "create_master_df", lambda *_a, **_k: df_master)

        seen: list[dict[str, object]] = []

        monkeypatch.setattr(app, "_analyze_group_data", lambda **_k: df_groups.copy())
        monkeypatch.setattr(
            app, "_create_plots_and_charts", lambda **kwargs: seen.append(kwargs)
        )

        app.run_pipeline(
            config_path=tmp_path / "config.toml",
            secrets_path=tmp_path / "secrets.toml",
            out_dir=tmp_path / "output_plots",
        )

        assert len(seen) == 1
        assert seen[0]["flow_type"] == "narratives"
        assert seen[0]["category"] == "Narratives"
        assert seen[0]["groups"] == ["ai", "pharma"]

    def test_individual_assets_branch(
        self, tmp_path, monkeypatch, df_master, df_groups
    ):
        provider_config = SimpleNamespace(
            provider="coingecko",
            flow_types=["individual_assets"],
            narratives=[],
            asset_groups={"Mine": ["nvidia", "tesla"], "Alt": ["amazon"]},
            range_lower_limits=[],
            base_assets=["us-dollar"],
        )
        analysis_config = SimpleNamespace()
        plot_config = SimpleNamespace()

        monkeypatch.setattr(
            app,
            "load_and_validate_config",
            lambda _p: (provider_config, analysis_config, plot_config),
        )
        monkeypatch.setattr(app, "get_provider_credentials", lambda *_a, **_k: "KEY")
        monkeypatch.setattr(app, "create_provider", lambda **_k: _fake_provider())
        monkeypatch.setattr(app, "create_master_df", lambda *_a, **_k: df_master)

        seen_analyze: list[dict[str, object]] = []
        seen_plots: list[dict[str, object]] = []

        def fake_analyze(**kwargs):
            seen_analyze.append(kwargs)
            return df_groups.copy()

        monkeypatch.setattr(app, "_analyze_group_data", fake_analyze)
        monkeypatch.setattr(
            app, "_create_plots_and_charts", lambda **kwargs: seen_plots.append(kwargs)
        )

        app.run_pipeline(
            config_path=tmp_path / "config.toml",
            secrets_path=tmp_path / "secrets.toml",
            out_dir=tmp_path / "output_plots",
        )

        # Per group (2) + portfolios (1) = 3 output calls
        assert len(seen_plots) == 3
        assert {c["category"] for c in seen_plots} == {"Mine", "Alt", "Portfolios"}

        # Two calls should pass df_groups (per-group assets), one should pass group_assets (portfolio aggregates)
        assert sum(1 for c in seen_analyze if c.get("df_groups") is not None) == 2
        assert sum(1 for c in seen_analyze if c.get("group_assets") is not None) == 1

    def test_market_cap_ranges_branch(
        self, tmp_path, monkeypatch, df_master, df_long, df_buckets
    ):
        provider_config = SimpleNamespace(
            provider="coingecko",
            flow_types=["market_cap_ranges"],
            narratives=[],
            asset_groups={},
            range_lower_limits=[899.0, 900.0, 901.0],
            base_assets=["us-dollar"],
        )
        analysis_config = SimpleNamespace()
        plot_config = SimpleNamespace()

        monkeypatch.setattr(
            app,
            "load_and_validate_config",
            lambda _p: (provider_config, analysis_config, plot_config),
        )
        monkeypatch.setattr(app, "get_provider_credentials", lambda *_a, **_k: "KEY")
        monkeypatch.setattr(app, "create_provider", lambda **_k: _fake_provider())
        monkeypatch.setattr(app, "create_master_df", lambda *_a, **_k: df_master)

        monkeypatch.setattr(app, "prepare_cap_ranges", lambda **_k: df_long)
        monkeypatch.setattr(app, "aggregate_cap_ranges", lambda **_k: df_buckets)
        monkeypatch.setattr(
            app, "calculate_range_metrics", lambda **_k: df_buckets.copy()
        )

        seen: list[dict[str, object]] = []
        monkeypatch.setattr(
            app, "_create_plots_and_charts", lambda **kwargs: seen.append(kwargs)
        )

        app.run_pipeline(
            config_path=tmp_path / "config.toml",
            secrets_path=tmp_path / "secrets.toml",
            out_dir=tmp_path / "output_plots",
        )

        assert len(seen) == 1
        assert seen[0]["flow_type"] == "market_cap_ranges"
        assert seen[0]["category"] == "Ranges"
        assert seen[0]["groups"] == ["899.0", "900.0", "901.0"]

    def test_tutorial_uses_packaged_config_and_local_data(
        self, tmp_path, monkeypatch, df_master
    ):
        def _should_not_be_called(*_a, **_k):
            raise AssertionError("should not be called")

        @contextmanager
        def _as_file_ctx(p: Path):
            # Mimic importlib.resources.as_file(...) returning a real pathlib.Path
            yield p

        config_path = tmp_path / "tutorial_config.toml"
        config_path.write_text('provider = "coingecko"\n', encoding="utf-8")

        # Force app.py to treat tutorial_config_path() as "some resource"
        monkeypatch.setattr(app, "tutorial_config_path", lambda: config_path)

        # If app.py uses importlib.resources.as_file, patch it to yield our config_path
        monkeypatch.setattr(
            resources, "as_file", lambda _traversable: _as_file_ctx(config_path)
        )

        # Record that load_and_validate_config got called with the tutorial config path
        seen = {"cfg_path": None}

        provider_config = SimpleNamespace(
            provider="coingecko",
            flow_types=[],  # avoid plotting branches here
            narratives=[],
            asset_groups={},
            range_lower_limits=[],
            base_assets=["us-dollar"],
        )
        analysis_config = SimpleNamespace()
        plot_config = SimpleNamespace()

        def fake_load_and_validate_config(path: Path):
            seen["cfg_path"] = path
            return provider_config, analysis_config, plot_config

        monkeypatch.setattr(
            app, "load_and_validate_config", fake_load_and_validate_config
        )

        # In tutorial mode we must NOT touch secrets/provider network
        monkeypatch.setattr(app, "get_provider_credentials", _should_not_be_called)
        monkeypatch.setattr(app, "create_provider", _should_not_be_called)

        # Provide tutorial data
        tutorial_data = SimpleNamespace(
            asset_mcs={
                "nvidia": pd.DataFrame({"timestamps": [0.0], "market_caps": [1.0]})
            },
            symbols={"nvidia": "nvda"},
            narrative_assets={"ai": {"nvidia"}},
        )
        monkeypatch.setattr(app, "load_tutorial_data", lambda: tutorial_data)

        # Stub the rest of the pipeline pieces
        monkeypatch.setattr(
            app,
            "define_frequency_min_and_max_timestamp",
            lambda _pc: ("5min", 0.0, 1.0),
        )
        monkeypatch.setattr(app, "create_master_df", lambda *_a, **_k: df_master)

        # Ensure no plotting happens in this test
        monkeypatch.setattr(app, "_create_plots_and_charts", _should_not_be_called)
        monkeypatch.setattr(app, "_analyze_group_data", _should_not_be_called)

        app.run_pipeline(
            config_path=tmp_path / "ignored.toml",
            secrets_path=tmp_path / "ignored_secrets.toml",
            out_dir=tmp_path / "out",
            is_tutorial=True,
        )

        assert seen["cfg_path"] == config_path


def test_analyze_group_data_uses_aggregate_groups_when_df_groups_none(
    monkeypatch, df_master, tmp_path
):
    df_agg = pd.DataFrame({"Mine": [3.0, 4.0, 5.0]}, index=df_master.index)
    df_out = pd.DataFrame({"Mine": [1.0, 1.1, 1.2]}, index=df_master.index)

    seen: dict[str, object] = {}

    out_dir = tmp_path / "output_plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    def fake_aggregate_groups(*, group_assets, df_master):
        seen["group_assets"] = group_assets
        return df_agg

    def fake_calculate_group_metrics(
        *, base_assets, df_base, df_groups, analysis_config
    ):
        seen["base_assets"] = base_assets
        seen["df_groups_passed"] = df_groups
        return df_out

    monkeypatch.setattr(app, "aggregate_groups", fake_aggregate_groups)
    monkeypatch.setattr(app, "calculate_group_metrics", fake_calculate_group_metrics)

    out = app._analyze_group_data(
        group_assets={"Mine": {"nvidia", "tesla"}},
        df_master=df_master,
        base_assets=["us-dollar"],
        df_base=None,
        analysis_config=SimpleNamespace(),
    )

    pd.testing.assert_frame_equal(out, df_out)
    assert seen["group_assets"] == {"Mine": {"nvidia", "tesla"}}
    assert seen["base_assets"] == ["us-dollar"]
    pd.testing.assert_frame_equal(seen["df_groups_passed"], df_agg)


def test_create_plots_and_charts_calls_plotters(monkeypatch, df_groups, tmp_path):
    calls: dict[str, dict[str, object]] = {}

    out_dir = tmp_path / "output_plots"
    out_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        app, "plot_charts", lambda **kwargs: calls.setdefault("plot_charts", kwargs)
    )
    monkeypatch.setattr(
        app,
        "create_category_tables",
        lambda **kwargs: calls.setdefault("tables", kwargs),
    )

    app._create_plots_and_charts(
        flow_type="narratives",
        category="Narratives",
        groups=["ai"],
        symbols={"ai": "AI"},
        base_assets=["us-dollar"],
        provider_config=SimpleNamespace(),
        analysis_config=SimpleNamespace(),
        plot_config=SimpleNamespace(),
        df=df_groups,
        out_dir=out_dir,
    )

    assert "plot_charts" in calls
    assert "tables" in calls
    assert calls["plot_charts"]["category"] == "Narratives"
    assert calls["tables"]["category"] == "Narratives"
