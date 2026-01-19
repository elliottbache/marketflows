import copy

import pytest
import requests

from marketflows.config import ProviderConfig
from marketflows.providers import coingecko


@pytest.fixture
def markets_url():
    return "https://api.coingecko.com/api/v3/coins/markets"


@pytest.fixture
def coins_list_response():
    return [
        {
            "id": "0chain",
            "symbol": "zcn",
            "name": "Zus",
            "platforms": {
                "ethereum": "0xb9ef770b6a5e12e45983c5d80545258aa38f3b78",
                "polygon-pos": "0x8bb30e0e67b11b978a5040144c410e1ccddcba30",
            },
        },
        {"id": "01coin", "symbol": "zoc", "name": "01coin", "platforms": {}},
    ]


@pytest.fixture
def coin_groups():
    return {
        "murad": [
            "bitcoin",
            "spx6900",
            "apu-s-club",
            "gigachad-2",
            "mog-coin",
            "popcat",
        ],
        "cryptocapo": [
            "bitcoin",
            "haha",
            "mstr2100",
            "selfiedogcoin",
            "moo-deng",
            "neiro-3",
        ],
    }


def test_load_coingecko_data(
    api_session, coingecko_api_key, coin_groups, requests_mock, monkeypatch
):
    """note that since we are not actually querying CoinGecko, the time step
    will be 1 day and not the hourly data that would normally be automatically
    imposed by CoinGecko for days=3"""
    days = 3
    flow_types = ["narratives", "market_cap_ranges", "individual_assets"]
    base_coins = ["bitcoin", "ethereum"]
    narratives = ["made-in-usa"]
    range_lower_limits = [1.1e11, 1e12, 1e13]

    # reduce coin_groups
    del coin_groups["cryptocapo"]
    coin_groups["murad"].pop()
    coin_groups["murad"].pop()
    coin_groups["murad"].pop()

    # monkeypatch timeout so that tests don't take more than 2 seconds
    original = coingecko._query_coins

    def fast_query_coins(session, *, url_data):
        return original(
            session, url_data=url_data, timeout=1, request_reset=60, fail_wait=1
        )

    monkeypatch.setattr(coingecko, "_query_coins", fast_query_coins)

    # define expected outputs
    final_list = [
        "bitcoin",
        "ethereum",
        "tether",
        "spx6900",
        "apu-s-club",
        "ripple",
        "solana",
        "usd-coin",
    ]

    # define response from requests.get calls
    # call from _add_symbols_from_ids
    symbol_response = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {"id": "dogecoin", "symbol": "doge", "name": "Dogecoin"},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
        {"id": "spx6900", "symbol": "spx", "name": "SPX6900"},
        {"id": "apu-s-club", "symbol": "apu", "name": "Apu Apustaja"},
    ]
    requests_mock.get(
        "https://api.coingecko.com/api/v3/coins/list",
        status_code=200,
        json=symbol_response,
    )

    # call from _define_url_narrative and _read_mcs_above_limit
    markets_response1 = [
        {"id": "ripple", "symbol": "xrp", "name": "XRP", "market_cap": 1.2e11},
        {"id": "solana", "symbol": "sol", "name": "Solana", "market_cap": 8e10},
        {"id": "usd-coin", "symbol": "usdc", "name": "USDC", "market_cap": 7e10},
    ]
    markets_response2 = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "market_cap": 2e12},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum", "market_cap": 4e11},
        {"id": "tether", "symbol": "usdt", "name": "Tether", "market_cap": 2e11},
        {"id": "binancecoin", "symbol": "bnb", "name": "BNB", "market_cap": 1e11},
        {"id": "ripple", "symbol": "xrp", "name": "XRP", "market_cap": 1e11},
        {"id": "solana", "symbol": "sol", "name": "Solana", "market_cap": 8e10},
    ]
    markets_adapter = requests_mock.get(
        "https://api.coingecko.com/api/v3/coins/markets",
        response_list=[
            {"status_code": 200, "json": markets_response1},
            {"status_code": 200, "json": markets_response2},
        ],
    )

    # call from _define_url_coin_chart
    base_chart_response = {
        "prices": [
            [1711843200000, 1e5],
            [1711929600000, 1.01e5],
            [1711983682000, 1.02e5],
        ],
        "market_caps": [
            [1711843200000, 1],
            [1711929600000, 1.01],
            [1711983682000, 1.02],
        ],
    }
    chart_adapter = dict()
    for icoin, coin in enumerate(final_list):
        chart_response = copy.deepcopy(base_chart_response)
        for idx in range(3):
            chart_response["market_caps"][idx][1] = (
                base_chart_response["market_caps"][idx][1] * icoin
            )
        chart_adapter[coin] = requests_mock.get(
            f"{coingecko.COINGECKO_BASE_URL}/{coin}/market_chart",
            status_code=200,
            json=chart_response,
        )

    # call tested function
    provider_config = ProviderConfig(
        days, flow_types, base_coins, narratives, range_lower_limits, coin_groups
    )
    coin_mcs, symbols, narrative_coins = coingecko.load_coingecko_data(
        api_key=coingecko_api_key, provider_config=provider_config
    )

    # check function outputs
    assert len(coin_mcs) == len(final_list)
    assert len(symbols) == len(final_list)
    for coin in final_list:
        assert coin in coin_mcs
        assert coin in symbols
        assert "timestamps" in coin_mcs[coin]
        assert "market_caps" in coin_mcs[coin]
        assert len(coin_mcs[coin]["market_caps"]) == days
        assert len(coin_mcs[coin]["timestamps"]) == days
    assert len(narrative_coins) == len(narratives)
    assert len(narrative_coins[narratives[0]]) == len(markets_response1)
    for coin in markets_response1:
        assert coin["id"] in narrative_coins[narratives[0]]

    # check params for markets calls
    history = markets_adapter.request_history
    assert len(history) == 2
    assert history[0].qs["vs_currency"] == ["usd"]
    assert history[0].qs["category"] == [narratives[0]]
    assert "per_page" in history[1].qs
    assert history[0].headers[coingecko.COINGECKO_HEADER_KEY_API] == coingecko_api_key

    # check params for charts calls
    for coin in final_list:
        history = chart_adapter[coin].request_history
        assert len(history) == 1
        assert history[0].qs["days"] == [str(days)]
        assert history[0].qs["vs_currency"] == ["usd"]


class TestParseCoinsFromGroups:
    def test_parse_coins_from_groups_success(self, coin_groups):
        coins = coingecko._parse_coins_from_groups(coin_groups)
        assert isinstance(coins, set)
        assert len(coins) == 11
        assert "murad" not in coins

    def test_parse_coins_from_groups_empty_list_success(self, coin_groups):
        # make second coin group empty
        coin_groups["cryptocapo"] = []

        coins = coingecko._parse_coins_from_groups(coin_groups)
        assert isinstance(coins, set)
        assert len(coins) == 6
        assert "murad" not in coins

    def test_parse_coins_from_groups_empty_dict_success(self):
        # make all coin_groups empty
        coin_groups = {}

        coins = coingecko._parse_coins_from_groups(coin_groups)
        assert isinstance(coins, set)
        assert len(coins) == 0


def test_add_symbols_from_ids_success(api_session, coingecko_api_key, requests_mock):
    coin_ids = {"bitcoin", "ethereum", "litecoin"}
    url = "https://api.coingecko.com/api/v3/coins/list"
    coins_list_response = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
        {"id": "litecoin", "symbol": "ltc", "name": "Litecoin"},
        {"id": "dogecoin", "symbol": "doge", "name": "Dogecoin"},
    ]
    # create an adapter variable to later access the last_request
    adapter = requests_mock.get(url, json=coins_list_response, status_code=200)

    # call the tested function
    symbols = coingecko._add_symbols_from_ids(coin_ids, session=api_session)

    assert len(symbols) == 3
    assert symbols["bitcoin"] == "btc"
    assert symbols["ethereum"] == "eth"
    assert symbols["litecoin"] == "ltc"

    assert (
        adapter.last_request.headers[coingecko.COINGECKO_HEADER_KEY_API]
        == coingecko_api_key
    )
    assert not adapter.last_request.qs


def test_define_url_symbols_success(coingecko_api_key):
    url_params = coingecko._define_url_symbols()
    assert url_params.url == f"{coingecko.COINGECKO_BASE_URL}/list"
    assert url_params.params is None


class TestQueryCoins:
    @pytest.mark.parametrize(
        "url, params",
        [
            (
                "https://api.coingecko.com/api/v3/coins/markets",
                {"category": "made-in-usa"},
            ),
            (
                "https://api.coingecko.com/api/v3/coins/markets",
                {"vs_currency": "usd", "per_page": "250", "page": "1"},
            ),
            (
                "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart",
                {
                    "vs_currency": "usd",
                    "days": "365",
                },
            ),
            ("https://api.coingecko.com/api/v3/coins/list", None),
        ],
        ids=["narrative", "ranges", "historical_data", "symbols_list"],
    )
    def test_query_coins_success(
        self,
        url,
        params,
        api_session,
        coingecko_api_key,
        coins_list_response,
        requests_mock,
    ):
        # create the URL, headers and params
        url_data = coingecko.GetValues(url, params)

        # create an adapter variable to later access the last_request
        adapter = requests_mock.get(
            url_data.url, json=coins_list_response, status_code=200
        )

        # call the tested function
        data = coingecko._query_coins(api_session, url_data=url_data)

        # check that the coins_list_response has been returned
        assert len(data) == 2
        assert data[0]["id"] == "0chain"
        assert data[0]["symbol"] == "zcn"
        assert requests_mock.called
        assert requests_mock.call_count == 1

        # check that the headers were correctly sent
        assert (
            adapter.last_request.headers[coingecko.COINGECKO_HEADER_KEY_API]
            == coingecko_api_key
        )

        # check that the params were correctly sent
        if params is not None:
            for key in params:
                assert adapter.last_request.qs[key][0] == params[key]
        else:
            assert not adapter.last_request.qs

    def test_query_coins_timeout_from_201(
        self, api_session, markets_url, coingecko_api_key, requests_mock, caplog
    ):
        # create the URL, headers and params
        url_data = coingecko.GetValues(markets_url, None)

        # return a 201 status code
        requests_mock.get(
            url_data.url, json={"mock_response": "hello"}, status_code=201
        )

        with pytest.raises(TimeoutError, match="CoinGecko query timed out"):
            coingecko._query_coins(
                api_session, url_data=url_data, fail_wait=1, request_reset=2
            )

        assert "Non-200 status code returned from CoinGecko.  Retrying." in caplog.text

    def test_query_coins_timeout_from_get_timeout(
        self, api_session, markets_url, coingecko_api_key, requests_mock, caplog
    ):
        # create the URL, headers and params
        url_data = coingecko.GetValues(markets_url, None)

        # raise a ConnectionTimeout exception
        requests_mock.get(url_data.url, exc=requests.exceptions.ConnectTimeout)

        with pytest.raises(TimeoutError, match="CoinGecko query timed out"):
            coingecko._query_coins(
                api_session, url_data=url_data, fail_wait=1, request_reset=1
            )

        assert "Exception raised when querying CoinGecko." in caplog.text

    def test_query_coins_rate_limit_then_success(
        self,
        api_session,
        markets_url,
        coingecko_api_key,
        coins_list_response,
        requests_mock,
        caplog,
    ):
        # create the URL, headers and params
        url_data = coingecko.GetValues(markets_url, None)

        # return a 429 rate limit status code
        adapter = requests_mock.get(
            url_data.url,
            response_list=[
                {"status_code": 429, "json": []},
                {"status_code": 200, "json": coins_list_response},
            ],
        )

        # call the tested function
        data = coingecko._query_coins(
            api_session, url_data=url_data, fail_wait=1, request_reset=1
        )

        # check that the coins_list_response has been returned
        assert len(data) == 2
        assert data[0]["id"] == "0chain"
        assert data[0]["symbol"] == "zcn"
        assert requests_mock.called
        assert requests_mock.call_count == 2

        # check that the headers were correctly sent
        assert (
            adapter.last_request.headers[coingecko.COINGECKO_HEADER_KEY_API]
            == coingecko_api_key
        )

        # check that the params were correctly sent
        assert not adapter.last_request.qs


def test_parse_coins_and_symbols_success(coins_list_response):
    coins, symbols = coingecko._parse_coins_and_symbols(coins_list_response)
    assert coins == {"0chain", "01coin"}
    assert symbols["0chain"] == "zcn"
    assert symbols["01coin"] == "zoc"


def test_define_url_narrative_success(coingecko_api_key, narrative):
    url_params = coingecko._define_url_narrative(narrative)
    assert url_params.url == f"{coingecko.COINGECKO_BASE_URL}/markets"
    assert url_params.params == {"vs_currency": "usd", "category": narrative}


@pytest.mark.parametrize(
    "lower_limit, last_page, len_coins, last_coin, "
    + "next_coin, last_symbol, next_symbol",
    [
        (9e10, 2, 5, "ripple", "solana", "xrp", "sol"),
        (7e10, 3, 6, "solana", "", "sol", ""),
        (1.5e11, 2, 3, "tether", "binancecoin", "usdt", "bnb"),
        (3e12, 1, 0, "", "", "", ""),
    ],
    ids=[
        "normal",
        "third_page_empty",
        "second_page_all_lower_than_limit",
        "no_coins_higher_than_limit",
    ],
)
def test_read_mcs_above_limit_success(
    api_session,
    coingecko_api_key,
    markets_url,
    lower_limit,
    last_page,
    len_coins,
    last_coin,
    next_coin,
    last_symbol,
    next_symbol,
    requests_mock,
    caplog,
    monkeypatch,
):
    coin_data1 = [
        {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin", "market_cap": 2e12},
        {"id": "ethereum", "symbol": "eth", "name": "Ethereum", "market_cap": 4e11},
        {"id": "tether", "symbol": "usdt", "name": "Tether", "market_cap": 2e11},
    ]
    coin_data2 = [
        {"id": "binancecoin", "symbol": "bnb", "name": "BNB", "market_cap": 1e11},
        {"id": "ripple", "symbol": "xrp", "name": "XRP", "market_cap": 1e11},
        {"id": "solana", "symbol": "sol", "name": "Solana", "market_cap": 8e10},
    ]

    # create the mock requests adapter
    adapter = requests_mock.get(
        markets_url,
        response_list=[
            {"status_code": 200, "json": coin_data1},
            {"status_code": 200, "json": coin_data2},
            {"status_code": 200, "json": []},
        ],
    )

    # monkeypatch timeout so that tests don't take more than 2 seconds
    original = coingecko._query_coins

    def fast_query_coins(session, *, url_data):
        return original(
            session, url_data=url_data, timeout=1, request_reset=60, fail_wait=1
        )

    monkeypatch.setattr(coingecko, "_query_coins", fast_query_coins)

    # call the tested function
    coins, symbols = coingecko._read_mcs_above_limit(lower_limit, session=api_session)

    # check coins and symbols
    assert len(coins) == len_coins
    assert len(symbols) == len_coins
    if last_coin:
        assert last_coin in coins
        assert symbols[last_coin] == last_symbol
    if next_coin:
        assert next_coin not in coins
        assert next_symbol not in symbols

    # check params and headers in last call to requests_mock.get
    assert (
        adapter.last_request.headers[coingecko.COINGECKO_HEADER_KEY_API]
        == coingecko_api_key
    )
    assert adapter.last_request.qs["vs_currency"] == ["usd"]
    assert adapter.last_request.qs["per_page"] == [str(coingecko._MAX_COINS_PER_PAGE)]
    assert adapter.last_request.qs["page"] == [str(last_page)]

    # check that warning is in log if empty page is returned
    # if last_coin is not empty and next_coin is empty,
    # this means last page is empty
    if last_coin and not next_coin:
        assert "Smallest range, which has a lower limit" in caplog.text


def test_define_url_find_coins_success(coingecko_api_key):
    url_params = coingecko._define_url_find_coins(page=1)
    assert url_params.url == f"{coingecko.COINGECKO_BASE_URL}/markets"
    assert url_params.params == {
        "vs_currency": "usd",
        "per_page": str(coingecko._MAX_COINS_PER_PAGE),
        "page": str(1),
    }


@pytest.mark.parametrize(
    "lower_limit, lowest_mc, last_idx",
    [
        (5e11, 1e11, 1),
        (3e12, 1e11, 0),
        (3e10, 1e11, 4),
        (3e10, dict(), 3),
    ],
    ids=["normal", "too_high", "too_low", "invalid_number"],
)
def test_lowest_mc_coin_index_success(lower_limit, lowest_mc, last_idx):
    coin_data = [
        {
            "id": "bitcoin",
            "symbol": "btc",
            "name": "Bitcoin",
            "market_cap": 1913727679902,
        },
        {
            "id": "ethereum",
            "symbol": "eth",
            "name": "Ethereum",
            "market_cap": 397106812843,
        },
        {
            "id": "tether",
            "symbol": "usdt",
            "name": "Tether",
            "market_cap": 186816994937,
        },
        {"id": "leafty", "symbol": "leafty", "name": "Leafty", "market_cap": lowest_mc},
    ]

    # call the tested function
    idx = coingecko._lowest_mc_coin_index(lower_limit=lower_limit, coin_data=coin_data)

    assert idx == last_idx


def test_define_url_coin_chart_success(coingecko_api_key, coin):
    days = 10
    url_params = coingecko._define_url_coin_chart(coin, days=days)
    assert url_params.url == f"{coingecko.COINGECKO_BASE_URL}/{coin}/market_chart"
    assert url_params.params == {"vs_currency": "usd", "days": str(days)}


def test_create_lists_from_chart_data_success():
    coin_data = {
        "prices": [
            [1711843200001, 69702.3087473573],
            [1711929600001, 71246.9514406015],
            [1711983682001, 68887.7495158568],
        ],
        "market_caps": [
            [1711843200000, 1370247487960.09],
            [1711929600000, 1401370211582.37],
            [1711983682000, 1355701979725.16],
        ],
        "total_volumes": [
            [1711843200002, 16408802301.8374],
            [1711929600002, 19723005998.215],
            [1711983682002, 30137418199.6431],
        ],
    }

    # call the tested function
    coin_data_lists = coingecko._create_lists_from_chart_data(coin_data)

    assert coin_data_lists["timestamps"] == [
        1711843200000,
        1711929600000,
        1711983682000,
    ]
    assert coin_data_lists["market_caps"] == [
        1370247487960.09,
        1401370211582.37,
        1355701979725.16,
    ]


def test_remove_faulty_data_success():
    data = {
        "timestamps": [1, 2, "NaN", "false", 5],
        "market_caps": [{}, 200, 300, "four", 500],
    }
    correct_data = coingecko._remove_faulty_data(data)
    assert correct_data == {"timestamps": [2, 5], "market_caps": [200, 500]}
