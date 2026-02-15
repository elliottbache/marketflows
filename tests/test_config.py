import pytest

from marketflows import config


@pytest.mark.parametrize(
    "base_assets, base_assets_exp",
    [
        (None, ["us-dollar"]),
        ([], ["us-dollar"]),
    ],
    ids=[
        "none_base_assets",
        "empty_base_assets",
    ],
)
def test_initialize_base_assets(base_assets, base_assets_exp):
    base_assets_actual = config.initialize_base_assets(base_assets)
    assert base_assets_actual == base_assets_exp
