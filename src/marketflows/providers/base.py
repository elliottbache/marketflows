from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass(frozen=True)
class ProviderData:
    asset_mcs: dict[str, pd.DataFrame]
    symbols: dict[str, str]
    narrative_assets: dict[str, set[str]]


@dataclass(frozen=True)
class ProviderWindow:
    freq: str
    min_timestamp: pd.Timestamp
    max_timestamp: pd.Timestamp


class MarketDataProvider(Protocol):
    def load_data(self) -> ProviderData: ...

    def define_window(self) -> ProviderWindow: ...
