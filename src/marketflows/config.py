from dataclasses import dataclass
from pathlib import Path

from marketflows.types import FlowType


@dataclass
class ProviderConfig:
    """Create a dataclass to hold the configuration values for the providers.

    Attributes:
        days (int): the number of days we want to collect data for
        flow_types (list[FlowType]): the list of flow types we want to collect data for
        base_assets (list[str]): assets used as base currency (e.g. EUR, JPY, etc.).
            These must be in decreasing MC order.
        narratives (list[str]): list of narratives to be graphed
        range_lower_limits (list[float]): the lower limits of each of the market cap ranges
        asset_groups (dict[str, set[str]]): groups of assets as would be the case for multiple portfolios
            containing (often) different assets
    """

    days: int
    flow_types: list[FlowType]
    base_assets: list[str]
    narratives: list[str]
    range_lower_limits: list[float]
    asset_groups: dict[str, list[str]]


@dataclass
class AnalysisConfig:
    """Create a dataclass to hold the configuration values for analysis.

    Attributes:
        diff_orders (list[int]): the orders of differentiation where 0 is no
            differentiation, 1 is the first derivative (growth), and 2 is the
            2nd derivative (inflection)
        ema_periods: EMA periods
        smoothing_ema: EMA period for smoothing growth and inflection data
    """

    diff_orders: list[int]
    ema_periods: list[int]
    smooth_ema: int
    is_unit_normalize: bool


# add base_assets, diff orders and ema periods initialization here since it is used everywhere
# don't forget to remove initialize_base_assets and whatever for diff_orders in other
# modules


# function to tie all other config functions together: load_and_validate_config
def load_and_validate_config(
    config_file: Path,
) -> tuple[ProviderConfig, AnalysisConfig]:
    """Load and validate the config file."""
    # load and read file

    # curate data

    provider_config = ProviderConfig(
        91,
        ["narratives", "individual_assets", "market_cap_ranges"],
        ["bitcoin"],
        ["made-in-usa", "aave-tokens"],
        [1e9, 1e10],
        {"Bullmind": ["zano", "superfarm"], "cryptocapo": ["haha", "mstr2100"]},
    )
    # this is a test provider_config.  Erase this later!!!
    analysis_config = AnalysisConfig([0, 1, 2], [20], 10, True)

    return provider_config, analysis_config


def initialize_base_assets(base_assets: list[str] | None = None) -> list[str]:
    """Create base_assets list if not already created and add us-dollar."""
    if base_assets is None:
        base_assets = list()
    if not base_assets or base_assets[0] != "us-dollar":
        base_assets.insert(0, "us-dollar")

    return base_assets


# function read config file

# read hours ago for tables

# function define graphs we want from matrix or cherry-pick

# function create asset list: create_asset_list

# function error check input

# remove duplicate narratives

# function to rename groups that have same name as narrative

# validate_config

#   check that we have range values if market_cap_ranges

# check that range values are in ascending order

# remove USD from base_coins

# return ProviderConfig and AnalysisConfig
