from marketflows.config import ProviderConfig
from marketflows.providers.base import MarketDataProvider
from marketflows.providers.coingecko import CoingeckoProvider


def create_provider(
    *, api_key: str, provider_config: ProviderConfig
) -> MarketDataProvider:
    if provider_config.provider == "coingecko":
        return CoingeckoProvider(api_key=api_key, provider_config=provider_config)

    raise ValueError(f"Unsupported provider: {provider_config.provider}")
