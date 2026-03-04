import json
from dataclasses import dataclass
from importlib import resources
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class TutorialData:
    """Local tutorial dataset shipped with the package."""

    asset_mcs: dict[str, pd.DataFrame]
    symbols: dict[str, str]
    narrative_assets: dict[str, set[str]]


def tutorial_config_path() -> resources.abc.Traversable:
    """Return the packaged tutorial config.toml."""
    return resources.files("marketflows.tutorial").joinpath("config.toml")


def load_tutorial_data() -> TutorialData:
    """Load packaged tutorial provider output (no network, no secrets)."""
    base = resources.files("marketflows.tutorial")
    csv_path = base.joinpath("coingecko_market_caps.csv")
    meta_path = base.joinpath("meta.json")

    with csv_path.open("r", encoding="utf-8") as f:
        df_long = pd.read_csv(f)

    # expected columns: asset, timestamps (ms), market_caps
    asset_mcs: dict[str, pd.DataFrame] = {}
    for asset, g in df_long.groupby("asset", sort=False):
        df_asset = g[["timestamps", "market_caps"]].copy()
        df_asset["timestamps"] = pd.to_numeric(df_asset["timestamps"], errors="coerce")
        df_asset["market_caps"] = pd.to_numeric(
            df_asset["market_caps"], errors="coerce"
        )
        asset_mcs[str(asset)] = df_asset.reset_index(drop=True)

    with meta_path.open("r", encoding="utf-8") as f:
        meta: dict[str, Any] = json.load(f)

    symbols = dict(meta.get("symbols", {}))
    narrative_assets_raw = dict(meta.get("narrative_assets", {}))
    narrative_assets = {k: set(v) for k, v in narrative_assets_raw.items()}

    return TutorialData(
        asset_mcs=asset_mcs, symbols=symbols, narrative_assets=narrative_assets
    )
