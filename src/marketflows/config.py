import copy
import logging
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, get_args

from marketflows.types import FlowType

_DEFAULTS = {
    "provider": "coingecko",
    "providers": {
        "coingecko": {
            "base_assets": ["bitcoin"],
            "days": 91,
            "narratives": ["made-in-usa", "ai"],
            "range_lower_limits": [1e9, 1e10],
            "flow_types": ["narratives", "individual_assets", "market_cap_ranges"],
            "asset_groups": {"Top": ["bitcoin", "ethereum", "binancecoin"], "Risk": ["the-open-network", "zcash", "world-liberty-financial"]},
        },
    },
    "analysis": {
        "ema_periods": [20],
        "diff_orders": [0, 1, 2],
        "smoothing_ema": 10,
        "is_unit_normalize": True,
    },
    "plots": {"hours_ago": [4, 8, 12, 24, 48, 72, 168, 336, 672]},
}

logger = logging.getLogger(__name__)


@dataclass
class ProviderConfig:
    """Create a dataclass to hold the configuration values for the providers.

    Attributes:
        provider (str): name of provider.  Leave as "" to read saved data from last
            run
        days (int): the number of days we want to collect data for
        flow_types (list[FlowType]): the list of flow types we want to collect data for
        base_assets (list[str]): assets used as base currency (e.g. EUR, JPY, etc.).
            These must be in decreasing MC order.
        narratives (list[str]): list of narratives to be graphed
        range_lower_limits (list[float]): the lower limits of each of the market cap ranges
        asset_groups (dict[str, set[str]]): groups of assets as would be the case for multiple portfolios
            containing (often) different assets

    Examples:
        >>> ProviderConfig(provider="td-ameritrade", days=10, flow_types=["narratives"], narratives=["ai"])
        ProviderConfig(provider='td-ameritrade', days=10, flow_types=['narratives'], base_assets=['us-dollar'], narratives=['ai'], range_lower_limits=[], asset_groups={})
    """

    provider: str
    days: int
    flow_types: list[FlowType]
    base_assets: list[str] = field(default_factory=list)
    narratives: list[str] = field(default_factory=list)
    range_lower_limits: list[float] = field(default_factory=list)
    asset_groups: dict[str, list[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.days < 1:
            logger.warning(
                f"days must be greater than or equal to 1 but were "
                f"defined as {self.days}.  Resetting to 1."
            )
            self.days = 1
        elif self.days > 365:
            logger.warning(
                f"days must be less than or equal to 365 but were defined "
                f"as {self.days}.  Resetting to 365."
            )
            self.days = 365

        # deduplicate
        self.flow_types = list(dict.fromkeys(self.flow_types))
        # ensure we only have allowed flow types
        allowed = get_args(FlowType)
        for flow_type in self.flow_types:
            if flow_type not in allowed:
                raise ValueError(f"flow_type must be in allowed list: {allowed}")

        # deduplicate and make us-dollar first element
        self.base_assets = [
            asset for asset in dict.fromkeys(self.base_assets) if asset != "us-dollar"
        ]
        self.base_assets.insert(0, "us-dollar")

        # check that base assets don't have underscores
        for asset in self.base_assets:
            if "_" in asset:
                raise ValueError("Base asset cannot contain underscore.")

        # check that we have narratives list if using this flow type
        if "narratives" in self.flow_types and not self.narratives:
            raise ValueError("Missing narratives list.")
        # deduplicate
        self.narratives = list(dict.fromkeys(self.narratives))

        # check that we have range lower limits if using this flow type
        if "market_cap_ranges" in self.flow_types and not self.range_lower_limits:
            raise ValueError("Missing list of lower limits for market cap ranges.")
        # deduplicate and sort
        self.range_lower_limits = sorted(set(self.range_lower_limits))

        # check that we have asset groups if we use individual asset flow type
        if "individual_assets" in self.flow_types and not self.asset_groups:
            raise ValueError("Missing dict of asset groups.")

        # check that we don't use a reserved name for one of the asset groups
        taken_names = {"Narratives", "Portfolios", "Ranges"}
        for group in self.asset_groups:
            if group in taken_names:
                raise ValueError(
                    f"{group} is a taken name.  "
                    f"Redefine this name in {self.asset_groups}"
                )
            # deduplicate
            self.asset_groups[group] = list(dict.fromkeys(self.asset_groups[group]))


@dataclass
class AnalysisConfig:
    """Create a dataclass to hold the configuration values for analysis.

    Attributes:
        provider_config: provider config
        smoothing_ema: EMA period for smoothing growth and inflection data
        is_unit_normalize: will we be creating plots that are normalized at each time
            step?
        diff_orders (list[int]): the orders of differentiation where 0 is no
            differentiation, 1 is the first derivative (growth), and 2 is the
            2nd derivative (inflection)
        ema_periods: EMA periods
    """

    provider_config: ProviderConfig
    smoothing_ema: int
    is_unit_normalize: bool
    diff_orders: list[int] = field(default_factory=list)
    ema_periods: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._check_is_positive(self.smoothing_ema, "Smoothing EMA periods")
        if self.smoothing_ema == 0:
            self.smoothing_ema = 1

        # at least have diff order 0
        if not self.diff_orders:
            self.diff_orders = [0]
        # make sure all diff orders are integers
        if not all(isinstance(x, int) for x in self.diff_orders):
            raise TypeError("Differentiation orders should be integers.")
        # create list up to highest diff order if narratives or individual assets
        if (
            "narratives" in self.provider_config.flow_types
            or "individual_assets" in self.provider_config.flow_types
        ):
            self._check_is_positive(max(self.diff_orders), "Differentiation order")
            self.diff_orders = list(range(max(self.diff_orders) + 1))
        else:
            for diff_order in self.diff_orders:
                self._check_is_positive(diff_order, "Differentiation order")
            self.diff_orders = sorted(set(self.diff_orders))

        # at least have ema period 1 (on EMA)
        if not self.ema_periods:
            self.ema_periods = [1]
        # make sure all EMA periods are integers
        if not all(isinstance(x, int) for x in self.ema_periods):
            raise TypeError("EMA periods should be integers.")
        # make sure all EMA periods are at least 1
        for idx, ema_period in enumerate(self.ema_periods):
            self._check_is_positive(ema_period, "EMA periods")
            if ema_period == 0:
                self.ema_periods[idx] = 1
        # deduplicate and sort
        self.ema_periods = sorted(set(self.ema_periods))
        # require EMA period 1 as the first element
        if self.ema_periods[0] != 1:
            self.ema_periods.insert(0, 1)

    def _check_is_positive(self, value: int, text: str) -> None:
        if value < 0:
            raise ValueError(f"{text} cannot be negative: {value}")


@dataclass
class PlotConfig:
    """Create a dataclass to hold the configuration values for plots.

    Attributes:
        hours_ago: list of offsets for tables columns
    """

    hours_ago: list[int]

    def __post_init__(self) -> None:
        # make negative hours_ago positive
        for idx, hour_ago in enumerate(self.hours_ago):
            if hour_ago < 0:
                self.hours_ago[idx] = abs(hour_ago)
        # deduplicate and sort
        self.hours_ago = sorted(set(self.hours_ago))


def load_and_validate_config(
    config_file: Path,
) -> tuple[ProviderConfig, AnalysisConfig, PlotConfig]:
    """Load and validate the config file.

    This does deep merge (i.e. it will descend into each nested item and only replace matching keys.
    """
    settings = _load_config(config_file)

    if "providers" in settings:
        provider = settings["provider"]
        prov = settings["providers"].get(provider)
        if not isinstance(prov, dict):
            raise ValueError("This provider has no settings.")
        provider_config = ProviderConfig(provider=provider, **prov)
    else:
        raise ValueError("Provider settings must be defined.")

    if "analysis" in settings:
        analysis_config = AnalysisConfig(
            provider_config=provider_config, **settings["analysis"]
        )
    else:
        raise ValueError("Analysis settings must be defined.")

    if "plots" in settings:
        plot_config = PlotConfig(**settings["plots"])
    else:
        raise ValueError("Plot settings must be defined.")

    return provider_config, analysis_config, plot_config


def get_provider_credentials(
    provider: str, secrets_path: Path = Path("secrets.toml")
) -> str:
    if not provider:
        return ""

    path = Path(secrets_path)
    if not path.exists():
        raise FileNotFoundError(f"{path} does not exist.  API key cannot be read.")

    try:
        with open(path, "rb") as f:
            secrets = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(f"API keys TOML file {path} contains an error.") from e

    # returns the specific API key for that provider, or raise if not found
    provider_dict = secrets.get(provider)
    if provider_dict is None:
        raise ValueError(f"This provider {provider} is not in secrets TOML file {path}")
    if "api_key" not in provider_dict:
        raise ValueError(
            f"No API keys found for {provider} in secrets TOML file {path}"
        )

    api_key = provider_dict.get("api_key")
    if not isinstance(api_key, str):
        raise TypeError(f"API key is invalid type: {type(api_key)}.  Should be str")

    return api_key


def _load_config(
    config_file: Path,
) -> dict[str, Any]:
    """Load the config file.

    This does a deep merge (i.e. it will only replace nested items with the same key."""
    settings = copy.deepcopy(_DEFAULTS)

    config_path = Path(config_file)
    if config_path.exists():
        with open(config_path, "rb") as f:
            user_config = tomllib.load(f)
            _deep_merge(settings, user_config)
    else:
        logger.warning(
            f"No configuration file found (checked {config_file}).  Using defaults."
        )

    return settings


def _deep_merge(base: dict[str, Any], overrides: dict[str, Any]) -> None:
    """Merges base with overrides replacing base values when both are
    available.

    Examples:
        >>> base = {"a": 1, "b": {"x": 1, "y": 2}}
        >>> overrides = {"b": {"y": 99}, "c": 3}
        >>> _deep_merge(base, overrides)
        >>> base
        {'a': 1, 'b': {'x': 1, 'y': 99}, 'c': 3}
    """
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
