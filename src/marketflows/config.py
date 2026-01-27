from dataclasses import dataclass

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
        range_lower_limits (list[float]): the lower limits of each of the ranges
        asset_groups (dict[str, list[str]]): groups of assets as would be the case for multiple portfolios
            containing (often) different assets
    """

    days: int
    flow_types: list[FlowType]
    base_assets: list[str]
    narratives: list[str]
    range_lower_limits: list[float]
    asset_groups: dict[str, list[str]]


# function to tie all other config functions together: load_and_validate_config

# function read config file

# function define graphs we want from matrix or cherry-pick

# function create asset list: create_asset_list

# function error check input


# validate_config

#   check that we have range values if market_cap_ranges

# check that range values are in ascending order

# remove USD from base_coins
