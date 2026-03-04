import json

import pandas as pd

from marketflows.tutorial import data


def test_tutorial_config_path_uses_packaged_location(tmp_path, monkeypatch):
    # Patch importlib.resources.files(...) to return our tmp directory.
    monkeypatch.setattr(data.resources, "files", lambda _pkg: tmp_path)

    p = data.tutorial_config_path()
    assert str(p).endswith("config.toml")


def test_load_tutorial_data_reads_csv_and_meta(tmp_path, monkeypatch):
    # Patch importlib.resources.files(...) to return our tmp directory.
    monkeypatch.setattr(data.resources, "files", lambda _pkg: tmp_path)

    # Create tutorial files in tmp_path
    (tmp_path / "config.toml").write_text('provider = "coingecko"\n', encoding="utf-8")

    df_long = pd.DataFrame(
        {
            "asset": ["bitcoin", "bitcoin", "ethereum", "ripple", "solana"],
            "timestamps": ["0", "1000", "0", "0", "0"],  # strings on purpose (coercion)
            "market_caps": ["1.5", "2.5", "10.0", "10.0", "10.0"],  # strings on purpose
        }
    )
    df_long.to_csv(tmp_path / "coingecko_market_caps.csv", index=False)

    meta = {
        "symbols": {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "ripple": "XRP",
            "solana": "SOL",
        },
        "narrative_assets": {
            "layer-1": ["bitcoin", "ethereum"],
            "made-in-usa": ["ripple", "solana"],
        },
    }
    (tmp_path / "meta.json").write_text(json.dumps(meta), encoding="utf-8")

    out = data.load_tutorial_data()

    assert set(out.asset_mcs) == {"bitcoin", "ethereum", "ripple", "solana"}
    assert set(out.symbols) == {"bitcoin", "ethereum", "ripple", "solana"}
    assert out.symbols["bitcoin"] == "BTC"
    assert out.narrative_assets["layer-1"] == {"bitcoin", "ethereum"}

    # DataFrames should have expected columns and numeric values
    btc = out.asset_mcs["bitcoin"]
    assert list(btc.columns) == ["timestamps", "market_caps"]
    assert btc["timestamps"].dtype.kind in {"i", "u", "f"}  # numeric
    assert btc["market_caps"].dtype.kind == "f"

    # Values should be correctly parsed
    assert btc["timestamps"].to_list() == [0, 1000]
    assert btc["market_caps"].to_list() == [1.5, 2.5]
