import pytest

from marketflows.config import ProviderConfig
from marketflows.providers.coingecko import CoingeckoProvider
from marketflows.providers.factory import create_provider


def test_create_provider_returns_coingecko_provider():
    provider_config = ProviderConfig(
        provider="coingecko",
        days=1,
        flow_types=[],
    )

    provider = create_provider(api_key="KEY", provider_config=provider_config)

    assert isinstance(provider, CoingeckoProvider)


def test_create_provider_raises_for_unsupported_provider():
    provider_config = ProviderConfig(
        provider="unsupported",
        days=1,
        flow_types=[],
    )

    with pytest.raises(ValueError, match="Unsupported provider: unsupported"):
        create_provider(api_key="KEY", provider_config=provider_config)
