import pytest

from marketflows import logging_utils


@pytest.mark.parametrize(
    "node,expected",
    [
        ("CoinGecko", "CoinGecko"),
        ("TD Ameritrade", "TD_Ameritrade"),
        ("../../oops", "oops"),
        ("a/b\\c", "a_b_c"),
    ],
)
def test_sanitize_node(node, expected):
    out = logging_utils._sanitize_node(node)
    assert out == expected
