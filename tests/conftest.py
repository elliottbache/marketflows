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
