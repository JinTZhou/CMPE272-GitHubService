# Author: Jin Ting Zhou

import pytest

from app.pagination import parse_link_header

pytestmark = pytest.mark.unit

def test_parse_next_and_last():
    header = (
        '<https://api.github.com/repos/test/issues?page=2>; rel="next", '
        '<https://api.github.com/repos/test/issues?page=5>; rel="last"'
    )

    result = parse_link_header(header)

    assert result["next"].endswith(
        "page=2"
    )

    assert result["last"].endswith(
        "page=5"
    )


def test_parse_empty_header():
    result = parse_link_header(None)

    assert result == {}


def test_parse_single_link():
    header = (
        '<https://example.com?page=3>; rel="next"'
    )

    result = parse_link_header(header)

    assert result == {
        "next": "https://example.com?page=3"
    }