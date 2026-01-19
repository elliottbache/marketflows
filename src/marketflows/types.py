from typing import Literal

FlowType = Literal["narratives", "market_cap_ranges", "individual_assets"]

AssetMarketCaps = dict[str, dict[str, list[float]]]
