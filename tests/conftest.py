import matplotlib

matplotlib.use("Agg")
import numpy as np
import pandas as pd
import pytest
import requests

from marketflows.providers import coingecko


@pytest.fixture
def narrative():
    return "made-in-usa"


@pytest.fixture(scope="session")
def coingecko_api_key():
    return "my_api_key"


@pytest.fixture
def coin():
    return "bitcoin"


@pytest.fixture(scope="session")
def api_session(coingecko_api_key):
    with requests.Session() as s:
        s.headers.update({coingecko.COINGECKO_HEADER_KEY_API: coingecko_api_key})
        yield s


@pytest.fixture
def df_master():
    df = pd.DataFrame()
    df.index = [
        pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC"),
        pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC"),
        pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"),
    ]
    df["amazon"] = [1002, 902, 1102]
    df["nvidia"] = [1000, 900, 1100]
    df["tesla"] = [1001, 901, 1101]

    return df


@pytest.fixture
def df_long(df_master):
    df = pd.DataFrame(
        {
            "asset": sorted(["amazon", "nvidia", "tesla"] * 3),
            "market_caps": [1002, 902, 1102, 1000, 900, 1100, 1001, 901, 1101],
            "lower_limit": [
                901.0,
                901.0,
                901.0,
                901.0,
                899.0,
                901.0,
                901.0,
                900.0,
                901.0,
            ],
        },
        index=df_master.index.append(df_master.index.append(df_master.index)),
    )
    df.index.name = "Datetime"

    return df


@pytest.fixture
def df_buckets(df_master):
    df = pd.DataFrame(
        {
            899.0: [np.nan, 900.0, np.nan],
            900.0: [np.nan, 901.0, np.nan],
            901.0: [3003.0, 902.0, 3303.0],
        },
        index=df_master.index,
    )
    df.index.name = "Datetime"

    return df


@pytest.fixture
def df_groups():
    df = pd.DataFrame()
    df.index = [
        pd.Timestamp("1970-01-01 00:00:00+0000", tz="UTC"),
        pd.Timestamp("1970-01-01 00:05:00+0000", tz="UTC"),
        pd.Timestamp("1970-01-01 00:10:00+0000", tz="UTC"),
        pd.Timestamp("1970-01-01 00:15:00+0000", tz="UTC"),
        pd.Timestamp("1970-01-01 00:20:00+0000", tz="UTC"),
        pd.Timestamp("1970-01-01 00:25:00+0000", tz="UTC"),
    ]
    df["pharma"] = [1000.0, 900.0, 1100.0, 1200.0, 1300.0, 1500.0]
    df["ai"] = [1001.0, 901.0, 1101.0, 1201.0, 1301.0, 1501.0]

    return df
