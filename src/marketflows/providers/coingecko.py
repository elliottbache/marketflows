"""Set of functions to handle querying CoinGecko."""

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, cast

import pandas as pd
import requests

from marketflows.config import ProviderConfig

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3/coins"
_MAX_COINS_PER_PAGE = 250  # maximum possible on CoinGecko
_DEFAULT_REQUEST_TIMEOUT = 5  # request should not take this long
_DEFAULT_REQUEST_RESET = 60  # time passed until request limit is reset
_DEFAULT_NON_200_SLEEP = 2  # time until next request if non-200 is returned
COINGECKO_HEADER_KEY_API = "x-cg-demo-api-key"  # key in headers dict for API key
_DEFAULT_N_TOP_NARRATIVE_COINS = 10  # number of coins to use when defining narrative

# complex types
CoinList = list[dict[str, str | float]]
CoinChart = dict[str, list[list[float]]]


@dataclass
class GetValues:
    """Create a dataclass to hold the values we want to send with session.get.

    Attributes:
        url (str): URL to be queried
        params (dict[str, str] | None): Dictionary of query parameters
    """

    url: str
    params: dict[str, str] | None


logger = logging.getLogger(__name__)


def load_coingecko_data(
    *,
    api_key: str,
    provider_config: ProviderConfig,
) -> tuple[dict[str, pd.DataFrame], dict[str, str], dict[str, set[str]]]:
    """Entrypoint for all CoinGecko data querying.

    This will query CoinGecko for all the necessary chart data.

    Args:
        api_key: CoinGecko API key
        provider_config: configuration values for the providers

    Returns:
        CoinGecko market cap data for all requested coins, symbol
        for each coin, and a set of coins in each narrative

    Raises:
        ValueError: if flow_type is not yet implemented
    """
    days = provider_config.days
    flow_types = provider_config.flow_types
    base_coins = provider_config.base_assets
    if "us-dollar" in base_coins:
        base_coins.remove("us-dollar")
    narratives = provider_config.narratives
    range_lower_limits = provider_config.range_lower_limits
    coin_groups = {
        key: set(values) for key, values in provider_config.asset_groups.items()
    }

    coins = set()
    symbols = dict()

    # open a session for CoinGecko
    with requests.Session() as session:
        session.headers.update(
            {"accept": "application/json", COINGECKO_HEADER_KEY_API: api_key}
        )

        # add all base and individual assets to coins set
        if base_coins:
            coins.update(base_coins)
        if "individual_assets" in flow_types:
            coins.update(_parse_coins_from_groups(coin_groups))

        if coins:
            symbols.update(_add_symbols_from_ids(coins, session=session))

        for flow_type in flow_types:
            # individual assets have already been treated above along with base_coins
            if flow_type == "individual_assets":
                continue

            elif flow_type == "narratives":
                all_narrative_coins = {}
                for narrative in narratives:
                    url_data = _define_url_narrative(narrative)
                    coin_data = _query_coins(session, url_data=url_data)
                    coin_data_list = _expect_list(coin_data)[
                        :_DEFAULT_N_TOP_NARRATIVE_COINS
                    ]
                    narrative_coins, narrative_symbols = _parse_coins_and_symbols(
                        coin_data_list
                    )
                    coins.update(narrative_coins)
                    symbols.update(narrative_symbols)
                    all_narrative_coins[narrative] = narrative_coins

            elif flow_type == "market_cap_ranges":
                range_coins, range_symbols = _read_mcs_above_limit(
                    min(range_lower_limits), session=session
                )
                coins.update(range_coins)
                symbols.update(range_symbols)

            else:
                raise ValueError(f"Unknown flow type {flow_type}")

        # query CoinGecko for the chart history of each of the coins previously defined
        coin_mcs = dict()
        for coin in coins:
            url_data = _define_url_coin_chart(coin, days=days)
            coin_data = _query_coins(session, url_data=url_data)
            coin_data_dict = _expect_dict(coin_data)
            if not coin_data_dict or not coin_data_dict.get("market_caps"):
                raise ValueError(f"Missing data for {coin}.")

            time_and_mcs = _create_df_from_chart_data(coin_data_dict)
            coin_mcs[coin] = _remove_faulty_data(time_and_mcs)

            # UNCOMMENT THESE LINES TO CREATE RAW DATA FILES FOR DEBUGGING
            # time_and_mcs.to_csv(f"PRIVATE/raw_data/raw_data_{coin}.csv", index=False)

    return coin_mcs, symbols, all_narrative_coins


def _parse_coins_from_groups(coin_groups: dict[str, set[str]]) -> set[str]:
    """Parse portfolio groups into a set of coins.

    Examples:
        >>> _parse_coins_from_groups({"g1": {"btc", "eth"}, "g2": {"eth", "sol"}}) == {"btc", "eth", "sol"}
        True
    """
    return {coin for group in coin_groups.values() for coin in group}


def _add_symbols_from_ids(
    coin_ids: set[str], *, session: requests.Session
) -> dict[str, str]:
    """Take set of ids and create dict with a symbol for each id"""
    url_data = _define_url_symbols()
    coin_data = _query_coins(session, url_data=url_data)
    coin_data_list = _expect_list(coin_data)
    _, all_symbols = _parse_coins_and_symbols(coin_data_list)

    symbols = dict()
    for coin in coin_ids:
        symbols[coin] = all_symbols[coin]

    return symbols


def _define_url_symbols() -> GetValues:
    """
    Define the URL to be queried along with params for finding the
    symbols associated with each coin ID.

    Returns:
        URL to be queried and params dict
    """
    return GetValues(
        f"{COINGECKO_BASE_URL}/list",
        None,
    )


def _query_coins(
    session: requests.Session,
    *,
    url_data: GetValues,
    timeout: int = _DEFAULT_REQUEST_TIMEOUT,
    request_reset: int = _DEFAULT_REQUEST_RESET,
    fail_wait: int = _DEFAULT_NON_200_SLEEP,
) -> CoinList | CoinChart:
    """Query CoinGecko and return a list of coins.

    Loop that retries the query until timeout.  A query should not take more than
    ``timeout`` seconds.  Exceptions during the query are caught and
    logged, but the loop continues after waiting ``fail_wait`` seconds.
    Only a 200 status code will be a valid response.
    If ``2*request_reset`` seconds go by, then an exception is raised.

    Args:
        session: the CoinGecko session
        url_data: URL to be queried with params
        timeout: timeout for query
        fail_wait: time to wait for retrying after non-200 response is received

    Returns:
        either a list of coins, each a dict with id and symbol, or a dict where
            value is a list of 2-element lists (each has the Unix timestamp
            (in milliseconds) and price/market cap/etc)

    Raise:
        TimeoutError if ``2*_DEFAULT_REQUEST_RESET`` goes by
    """
    # initialize response so that finally can check for successful response
    response: requests.Response | None = None

    start_time = time.time()
    while True:
        try:
            logger.info(
                f"Querying CoinGecko URL={url_data.url}, with params={url_data.params}"
            )
            response = session.get(
                url_data.url,
                params=url_data.params,
                timeout=timeout,
            )

            if response.status_code == 429:
                logger.warning(f"Rate limit reached.  Waiting {request_reset} seconds.")
                time.sleep(request_reset)
                continue

            if response.status_code != requests.codes.ok:
                logger.warning(
                    "Non-200 status code returned from CoinGecko.  Retrying."
                )
                time.sleep(fail_wait)
                continue

            data = response.json()
            break

        except requests.exceptions.RequestException:
            logger.warning(
                f"Exception raised when querying CoinGecko.  "
                f"Waiting {fail_wait} seconds then retrying."
            )
            time.sleep(fail_wait)
            continue

        finally:
            end_time = time.time()
            if response is None or (
                response.status_code != requests.codes.ok
                and end_time > start_time + 2 * request_reset
            ):  # extra margin before raising
                raise TimeoutError("CoinGecko query timed out.")

    return data


def _expect_list(coin_data: CoinList | CoinChart) -> CoinList:
    """Change type for coin_data to CoinList."""
    if not isinstance(coin_data, list):
        raise TypeError(
            f"CoinGecko query returned an incorrect type {type(coin_data).__name__} "
            f"while expecting a list"
        )

    return coin_data


def _expect_dict(coin_data: CoinList | CoinChart) -> CoinChart:
    """Change type for coin_data to CoinChart."""
    if not isinstance(coin_data, dict):
        raise TypeError(
            f"CoinGecko query returned an incorrect type {type(coin_data).__name__} "
            f"while expecting a dict"
        )

    return coin_data


def _parse_coins_and_symbols(
    data: CoinList,
) -> tuple[set[str], dict[str, str]]:
    """Parse json data from CoinGecko and create coins set and symbols dict."""
    coins = set()
    symbols = dict()
    for coin in data:
        coin_id = cast(str, coin["id"])
        coin_symbol = cast(str, coin["symbol"])
        coins.add(coin_id)
        symbols[coin_id] = coin_symbol

    return coins, symbols


def _define_url_narrative(narrative: str) -> GetValues:
    """
    Define the URL to be queried along with params for finding the
    coins that belong to the specified narrative.

    Args:
        narrative: narrative to be checked

    Returns:
        URL to be queried and params dict
    """
    return GetValues(
        f"{COINGECKO_BASE_URL}/markets",
        {"vs_currency": "usd", "category": narrative},
    )


def _read_mcs_above_limit(
    lower_limit: float = 1e8, *, session: requests.Session
) -> tuple[set[str], dict[str, str]]:
    """Keep querying CoinGecko until the lowest market cap in the current response
    is less than ``lower_limit``.

    If the lower_limit is never reached, then all the coins and symbols are returned.

    Args:
        lower_limit: the lower limit market cap in the smallest range
        session: the CoinGecko session

    Returns:
        coins set and symbols dict for all coins above lower_limit market cap
    """
    min_mc = lower_limit + 1
    page = 1
    coins = set()
    symbols = dict()
    while min_mc > lower_limit:
        url_data = _define_url_find_coins(page=page)

        coin_data = _query_coins(session, url_data=url_data)
        coin_data_list = _expect_list(coin_data)
        if not coin_data_list:
            logger.warning(
                f"Smallest range, which has a lower limit {lower_limit}, "
                f"is too small.  Searched through Page {page}"
            )
            break

        # save coin_data length for later comparing with the reduced coin_data length
        len_coin_data = len(coin_data_list)

        # only keep those with market cap above lower_limit
        coin_data_list = coin_data_list[
            : _lowest_mc_coin_index(lower_limit=lower_limit, coin_data=coin_data_list)
        ]
        page_coins, page_symbols = _parse_coins_and_symbols(coin_data_list)
        coins.update(page_coins)
        symbols.update(page_symbols)

        # we have already reached the lower limit
        if len_coin_data != len(coin_data_list):
            break

        page += 1
        min_mc = cast(float, coin_data_list[-1]["market_cap"])

    return coins, symbols


def _define_url_find_coins(*, page: int = 1) -> GetValues:
    """
    Define the URL to be queried along with params for finding the
    next page's coins and their market caps.

    Args:
        page: the current page to be queried, each page
            having `_MAX_COINS_PER_PAGE` coins

    Returns:
        URL to be queried and params dict
    """
    url = f"{COINGECKO_BASE_URL}/markets"
    params = dict()
    params["vs_currency"] = "usd"
    params["per_page"] = str(_MAX_COINS_PER_PAGE)
    params["page"] = str(page)

    return GetValues(url, params)


def _lowest_mc_coin_index(*, lower_limit: float, coin_data: CoinList) -> int:
    """Find the index in coin_data for the first coin below ``lower_limit`` market cap.
    If no coin is below the ``lower_limit``, the length of ``coin_data`` is returned.
    If all coins are below ``lower_limit``, 0 is returned.

    Examples:
        >>> data = [{"market_cap": 300.0}, {"market_cap": 200.0}, {"market_cap": 90.0}]
        >>> _lowest_mc_coin_index(lower_limit=100.0, coin_data=data)
        2
        >>> _lowest_mc_coin_index(lower_limit=50.0, coin_data=data)
        3
        >>> _lowest_mc_coin_index(lower_limit=400.0, coin_data=data)
        0
    """
    if (
        _is_number(coin_data[-1]["market_cap"])
        and cast(float, coin_data[-1]["market_cap"]) > lower_limit
    ):
        return len(coin_data)

    # iterate through coins until coin has MC less than lower_limit
    for last_idx in range(len(coin_data)):
        if (
            not _is_number(coin_data[last_idx]["market_cap"])
            or cast(float, coin_data[last_idx]["market_cap"]) < lower_limit
        ):
            return last_idx

    return len(coin_data)  # this shouldn't ever trigger


def _is_number(value: Any) -> bool:
    """Check if the supplied value is a float or int.

    Examples:
        >>> _is_number(1)
        True
        >>> _is_number(1.5)
        True
        >>> _is_number("1")
        False
    """
    return isinstance(value, (float, int))


def _define_url_coin_chart(coin: str, *, days: int = 365) -> GetValues:
    """
    Define the URL to be queried along with params for find the
    historical coin data for the specified coin.

    Args:
        coin: coin ID to be queried (e.g. bitcoin, not BTC), which can be found
            on each coin's CoingGecko page under "API ID"
            (e.g. https://www.coingecko.com/en/coins/bitcoin)
        days: the number of days of historical data to be queried.  Defaults to
            max permissible by CoinGecko

    Returns:
        URL to be queried and params dict

    Notes:
        - Automatic intervals in chart data:
            - 1 day from current time = 5-minutely data
            - 2 - 90 days from current time = hourly data
            - above 90 days from current time = daily data (00:00 UTC)
    """
    url = f"{COINGECKO_BASE_URL}/{coin}/market_chart"
    params = dict()
    params["vs_currency"] = "usd"
    params["days"] = str(days)

    return GetValues(url, params)


def _create_df_from_chart_data(
    coin_data: CoinChart,
) -> pd.DataFrame:
    """Take historical chart data from CoinGecko and convert to a DataFrame with
    ``timestamp`` and ``market_caps`` lists of all the data.  Timestamps are in
     milliseconds.

    Examples:
        >>> d = {"market_caps": [[1.0, 10.0], [2.0, 12.0]]}
        >>> _create_df_from_chart_data(d)
           timestamps  market_caps
        0         1.0         10.0
        1         2.0         12.0
    """
    timestamps_and_market_caps = coin_data["market_caps"]
    timestamps, market_caps = zip(*timestamps_and_market_caps, strict=True)

    return pd.DataFrame(
        {"timestamps": list(timestamps), "market_caps": list(market_caps)}
    )


def _remove_faulty_data(df: pd.DataFrame) -> pd.DataFrame:
    """Take timestamps and market caps and remove any rows that contain NaN or <= 0."""
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.dropna()
    df = df[(df > 0).all(axis=1)]

    return df


def define_frequency_min_and_max_timestamp(
    provider_config: ProviderConfig,
) -> tuple[str, float, float]:
    """Define the frequency, minimum, and maximum timestamp retrieved from CoinGecko.

    Time spans that are lower than 1 day are set to 1 day.  Time spans that are higher
    than 365 days are set to 365 days.  Otherwise:
    - 1 day: 5-minutely data
    - 1 < days <= 90 days: hourly data
    - > 90 days: daily data (00:00 UTC)

    Daily data is published at 00:10 UTC for 00:00 UTC.

    Args:
        provider_config: CoinGecko configuration including ``days``

    Returns:
        the frequency, minimum timestamp, and maximum timestamp
    """
    if provider_config.days < 1:
        logger.warning(
            "CoinGecko data collection time span is too low and is changed " "to 1 day."
        )

    now = datetime.now(UTC)
    if provider_config.days <= 1:
        logger.info(
            "CoinGecko data collection time span is 1 day and the frequency "
            " is set to 5 minutes."
        )
        freq = "5min"
        min_datetime = now - timedelta(days=1)
        min_timestamp = min_datetime.replace(second=0, microsecond=0).timestamp() * 1000
        max_timestamp = now.replace(second=0, microsecond=0).timestamp() * 1000

    elif provider_config.days <= 90:
        logger.info(
            f"CoinGecko data collection time span is {provider_config.days}"
            f" days and the frequency is set to 1 hour."
        )
        freq = "h"
        min_datetime = now - timedelta(days=provider_config.days)
        min_timestamp = (
            min_datetime.replace(minute=0, second=0, microsecond=0).timestamp() * 1000
        )
        max_timestamp = (
            now.replace(minute=0, second=0, microsecond=0).timestamp() * 1000
        )

    elif provider_config.days < 365:
        logger.info(
            f"CoinGecko data collection time span is {provider_config.days}"
            f" days and the frequency is set to 1 day."
        )
        freq = "D"
        min_datetime = now - timedelta(days=provider_config.days)
        min_timestamp = (
            min_datetime.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            * 1000
        )
        max_timestamp = (
            now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000
        )
    else:
        logger.info(
            "CoinGecko data collection time span is 365 "
            "days and the frequency is set to 1 day."
        )
        freq = "D"
        min_datetime = now - timedelta(days=provider_config.days)
        min_timestamp = (
            min_datetime.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
            * 1000
        )
        max_timestamp = (
            now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp() * 1000
        )

    return freq, min_timestamp, max_timestamp
