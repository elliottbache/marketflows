# ERASE THIS FUNCTION MAYBE!!!
# %%
from pathlib import Path

import pandas as pd


def read_raw_data(folder: Path) -> dict[str, pd.DataFrame]:
    """Read the raw data from a specific folder.

    This allows us to bypass the API query and can be used in debugging.  This
    is not meant to be used in production.  The raw data files are named
    ``raw_data_{coin}.csv``.

    Args:
        folder: the folder where the raw data lives.

    Returns:
        dict of DataFrames for each coin holding timestamps and market caps
    """
    coinCharts = dict()
    for file in folder.iterdir():
        print(f"\nfile: {file}")
        coin = file.name.split("raw_data_")[1]
        coin = coin.split(".csv")[0]
        coinCharts[coin] = pd.read_csv(file)

    return coinCharts


# ERASE THESE LINES!!!
if __name__ == "__main__":
    """from marketflows.config import ProviderConfig
    provider_config = ProviderConfig(
        2,
        ["narratives", "individual_assets", "market_cap_ranges"],
        ["bitcoin"],
        ["made-in-usa"],
        [1e9, 1e10],
        {"Bullmind": ["zano", "superfarm"], "cryptocapo": ["haha", "mstr2100"]},
    )"""
    from pathlib import Path

    print(Path.cwd())
    raw_folder = Path("/home/ebache/marketflows/PRIVATE/raw_data")
    coinCharts = read_raw_data(raw_folder)


# %%
