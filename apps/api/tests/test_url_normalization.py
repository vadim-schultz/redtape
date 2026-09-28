from __future__ import annotations

import pytest
from app.url_normalization import normalize_url


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        ("HTTP://Example.COM/path#fragment", "http://example.com/path"),
        ("https://example.com/path?utm_source=newsletter&b=2", "https://example.com/path?b=2"),
        ("https://example.com/path?fbclid=123", "https://example.com/path"),
        ("https://example.com/path?gclid=abc", "https://example.com/path"),
    ],
)
def test_normalize_url_lowercases_host_and_drops_fragment_and_tracking_parameters(url: str, expected: str) -> None:
    assert normalize_url(url) == expected


def test_normalize_url_treats_trailing_slash_and_parameter_order_as_equal() -> None:
    assert normalize_url("https://example.com/path/?b=2&a=1") == normalize_url("https://example.com/path?a=1&b=2")


def test_normalize_url_keeps_path_case_and_meaningful_query_parameters() -> None:
    url = "https://example.com/Path/CaseSensitive?ref=news&id=42"
    assert normalize_url(url) == "https://example.com/Path/CaseSensitive?id=42&ref=news"
