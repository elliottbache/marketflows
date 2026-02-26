import copy
from unittest.mock import patch

import pytest

from marketflows import config


class TestProviderConfig:
    def test_provider_config_days_validation(self):
        # test lower bound
        cfg = config.ProviderConfig(
            provider="td-ameritrade",
            days=0,
            flow_types=["narratives"],
            base_assets=[],
            narratives=["ai"],
            range_lower_limits=[],
            asset_groups={},
        )
        assert cfg.days == 1

        # test upper bound
        cfg = config.ProviderConfig(
            provider="td-ameritrade",
            days=500,
            flow_types=["narratives"],
            base_assets=[],
            narratives=["ai"],
            range_lower_limits=[],
            asset_groups={},
        )
        assert cfg.days == 365

    def test_provider_config_deduplication(self):
        # test that duplicate assets and narratives are removed
        cfg = config.ProviderConfig(
            provider="td-ameritrade",
            days=10,
            flow_types=["narratives"],
            base_assets=["us-dollar", "us-dollar", "japan-yen"],
            narratives=["ai", "ai"],
            range_lower_limits=[10.0, 5.0, 10.0, 1.0],
            asset_groups={"Portfolio1": ["nvidia", "nvidia"]},
        )
        assert cfg.base_assets == ["us-dollar", "japan-yen"]
        assert cfg.narratives == ["ai"]
        assert cfg.range_lower_limits == [1.0, 5.0, 10.0]  # Also tests sorting
        assert cfg.asset_groups["Portfolio1"] == ["nvidia"]

    def test_provider_config_reserved_names(self):
        # test that using 'Portfolios' as a key raises an error
        with pytest.raises(ValueError, match="Portfolios is a taken name"):
            config.ProviderConfig(
                provider="td-ameritrade",
                days=10,
                flow_types=["narratives"],
                base_assets=[],
                narratives=["ai"],
                range_lower_limits=[],
                asset_groups={"Portfolios": ["nvidia"]},
            )

    def test_provider_config_ranges_present_if_needed(self):
        # test ranges present if needed
        with pytest.raises(
            ValueError, match="Missing list of lower limits for market cap ranges"
        ):
            config.ProviderConfig(
                provider="td-ameritrade",
                days=10,
                flow_types=["market_cap_ranges"],
                base_assets=[],
                narratives=[],
                range_lower_limits=[],
                asset_groups={},
            )

    def test_provider_config_empty_provider(self):
        # test that provider can be an empty string (for reading saved data)
        cfg = config.ProviderConfig(
            provider="",
            days=10,
            flow_types=["narratives"],
            base_assets=[],
            narratives=["ai"],
            range_lower_limits=[],
            asset_groups={},
        )
        assert cfg.provider == ""


class TestAnalysisConfig:

    def test_analysis_config_success(self):
        """Verify valid input is cleaned (sorted and deduplicated)."""
        cfg = config.AnalysisConfig(
            provider_config=config.ProviderConfig(
                provider="td-ameritrade", days=1, flow_types=[]
            ),
            diff_orders=[2, 0, 1, 2],
            ema_periods=[20, 10, 20, 2],
            smoothing_ema=5,
            is_unit_normalize=True,
        )
        assert cfg.diff_orders == [0, 1, 2]
        assert cfg.ema_periods == [1, 2, 10, 20]
        assert cfg.smoothing_ema == 5
        assert cfg.is_unit_normalize

    def test_analysis_config_negative_smoothing_ema_raises_error(self):
        """Verify negative smoothing EMA triggers ValueError."""
        with pytest.raises(
            ValueError, match="Smoothing EMA periods cannot be negative"
        ):
            config.AnalysisConfig(
                provider_config=config.ProviderConfig(
                    provider="td-ameritrade", days=1, flow_types=[]
                ),
                diff_orders=[1],
                ema_periods=[10],
                smoothing_ema=-5,
                is_unit_normalize=False,
            )

    def test_analysis_config_zero_smoothing_ema(self):
        """Verify 0 smoothing EMA returns 1."""
        cfg = config.AnalysisConfig(
            provider_config=config.ProviderConfig(
                provider="td-ameritrade", days=1, flow_types=[]
            ),
            diff_orders=[1],
            ema_periods=[10],
            smoothing_ema=0,
            is_unit_normalize=False,
        )
        assert cfg.smoothing_ema == 1

    def test_analysis_config_negative_diff_orders_raises_error(self):
        """Verify negative differentiation orders trigger ValueError."""
        with pytest.raises(
            ValueError, match="Differentiation order cannot be negative"
        ):
            config.AnalysisConfig(
                provider_config=config.ProviderConfig(
                    provider="td-ameritrade", days=1, flow_types=[]
                ),
                diff_orders=[-3, -1],
                ema_periods=[10],
                smoothing_ema=5,
                is_unit_normalize=False,
            )

    @pytest.mark.parametrize(
        "input_orders, flow_types, expected",
        [
            (None, ["narratives"], [0]),
            ([], ["narratives"], [0]),
            ([0], ["individual_assets"], [0]),
            ([2], ["individual_assets"], [0, 1, 2]),
            ([1, 3], ["individual_assets"], [0, 1, 2, 3]),
            ([2], ["market_cap_ranges"], [2]),
            ([1, 3], ["market_cap_ranges"], [1, 3]),
        ],
    )
    def test_analysis_config_diff_orders_expansion(
        self, input_orders, flow_types, expected
    ):
        cfg = config.AnalysisConfig(
            provider_config=config.ProviderConfig(
                provider="td-ameritrade",
                days=1,
                flow_types=flow_types,
                asset_groups={"Mine": ["nvidia", "tesla"]},
                narratives=["ai", "pharma"],
                range_lower_limits=[1e9, 1e11],
            ),
            diff_orders=input_orders,
            ema_periods=[10],
            smoothing_ema=5,
            is_unit_normalize=True,
        )
        assert cfg.diff_orders == expected

    def test_analysis_config_zero_values_allowed_for_diff(self):
        """Verify that 0 is acceptable since the check is for < 0."""
        cfg = config.AnalysisConfig(
            provider_config=config.ProviderConfig(
                provider="td-ameritrade", days=1, flow_types=[]
            ),
            diff_orders=[0],
            ema_periods=[1],
            smoothing_ema=1,
            is_unit_normalize=True,
        )
        assert cfg.diff_orders == [0]

    def test_analysis_config_zero_emas_set_to_one(self):
        """Verify 0 EMAs are set to 1."""
        cfg = config.AnalysisConfig(
            provider_config=config.ProviderConfig(
                provider="td-ameritrade", days=1, flow_types=[]
            ),
            diff_orders=[1],
            ema_periods=[0],
            smoothing_ema=0,
            is_unit_normalize=False,
        )
        assert cfg.ema_periods == [1]
        assert cfg.smoothing_ema == 1

    def test_analysis_config_negative_ema_periods_raises_error(self):
        """Verify negative EMA periods trigger ValueError."""
        with pytest.raises(ValueError, match="EMA periods cannot be negative"):
            config.AnalysisConfig(
                provider_config=config.ProviderConfig(
                    provider="td-ameritrade", days=1, flow_types=[]
                ),
                diff_orders=[1],
                ema_periods=[-10],
                smoothing_ema=5,
                is_unit_normalize=False,
            )

    def test_analysis_config_individual_assets_no_asset_groups(self):
        with pytest.raises(ValueError, match="Missing dict of asset groups"):
            config.AnalysisConfig(
                provider_config=config.ProviderConfig(
                    provider="td-ameritrade", days=1, flow_types=["individual_assets"]
                ),
                diff_orders=[3],
                ema_periods=[10],
                smoothing_ema=5,
                is_unit_normalize=True,
            )

    def test_analysis_config_defaults(self):
        """Verify that all None values is successful."""
        cfg = config.AnalysisConfig(
            provider_config=config.ProviderConfig(
                provider="td-ameritrade", days=1, flow_types=[]
            ),
            smoothing_ema=1,
            is_unit_normalize=False,
        )
        assert cfg.diff_orders == [0]
        assert cfg.ema_periods == [1]


def test_plot_config_success():
    """Verify that negatives are made positive, duplicates are removed, and hours_ago
    is sorted."""
    cfg = config.PlotConfig(hours_ago=[-24, -12, 24, 4, 8, 24, 12, 48, 72, 168, 336])
    assert cfg.hours_ago == [4, 8, 12, 24, 48, 72, 168, 336]


class TestLoadConfig:
    def test_load_config_file_not_found(self, tmp_path):
        """Verify it returns defaults if the file does not exist."""
        non_existent = tmp_path / "does_not_exist.toml"
        settings = config._load_config(non_existent)

        assert settings == config._DEFAULTS

    def test_load_config_basic_override(self, tmp_path):
        """Verify top-level keys are replaced correctly."""
        config_file = tmp_path / "config.toml"
        config_file.write_text('key = "new_value"', encoding="utf-8")

        with patch("marketflows.config._DEFAULTS", {"key": "default"}):
            settings = config._load_config(config_file)
            assert settings["key"] == "new_value"

    def test_load_config_nested_update(self, tmp_path):
        """Verify nested dictionaries are updated (shallow merge)."""
        config_file = tmp_path / "config.toml"
        config_file.write_text("[server]\nport = 9000", encoding="utf-8")

        mock_defaults = {"server": {"host": "localhost", "port": 8080}, "other": 123}

        with patch("marketflows.config._DEFAULTS", mock_defaults):
            settings = config._load_config(config_file)

            # 'port' should be updated, 'host' should remain from defaults
            assert settings["server"]["port"] == 9000
            assert settings["server"]["host"] == "localhost"
            assert settings["other"] == 123

    def test_load_config_does_not_mutate_defaults(self, tmp_path):
        config_file = tmp_path / "config.toml"
        config_file.write_text("[providers.coingecko]\ndays = 10\n", encoding="utf-8")

        defaults_before = copy.deepcopy(config._DEFAULTS)
        _ = config._load_config(config_file)
        assert defaults_before == config._DEFAULTS


class TestDeepMerge:
    def test_deep_merge_basic_update(self):
        """Verify top-level keys are updated or added."""
        base = {"a": 1, "b": 2}
        overrides = {"b": 3, "c": 4}

        config._deep_merge(base, overrides)

        assert base == {"a": 1, "b": 3, "c": 4}

    def test_deep_merge_nested_dicts(self):
        """Verify nested dictionaries are merged, not replaced."""
        base = {"providers": {"coingecko": {"days": 91, "assets": ["bitcoin"]}}}
        overrides = {
            "providers": {
                "coingecko": {"days": 10},  # Only update days
                "binance": {"days": 30},  # Add new provider
            }
        }

        config._deep_merge(base, overrides)

        expected = {
            "providers": {
                "coingecko": {"days": 10, "assets": ["bitcoin"]},
                "binance": {"days": 30},
            }
        }
        assert base == expected

    def test_deep_merge_type_conflict(self):
        """Verify that if a value is no longer a dict, it gets replaced."""
        # Base has a dict, but user provides a string
        base = {"analysis": {"ema": 10}}
        overrides = {"analysis": "disabled"}

        config._deep_merge(base, overrides)
        assert base == {"analysis": "disabled"}

    def test_deep_merge_list_replacement(self):
        """Verify lists are replaced entirely."""
        base = {"assets": ["btc", "eth"]}
        overrides = {"assets": ["sol"]}

        config._deep_merge(base, overrides)
        assert base == {"assets": ["sol"]}

    def test_deep_merge_empty_overrides(self):
        """Verify merging empty dict changes nothing."""
        base = {"a": 1}
        config._deep_merge(base, {})
        assert base == {"a": 1}

    def test_deep_merge_deeply_nested(self):
        """Verify it works more than two levels deep."""
        base = {"a": {"b": {"c": 1}}}
        overrides = {"a": {"b": {"d": 2}}}

        config._deep_merge(base, overrides)
        assert base == {"a": {"b": {"c": 1, "d": 2}}}
