# Author: Jin Ting Zhou

import httpx
import pytest

from app.github_client import GitHubAPIError
from app.routes.issues import map_github_error

pytestmark = pytest.mark.unit

def test_maps_401():
    error = GitHubAPIError(
        status_code=401,
        message="Bad credentials",
    )

    result = map_github_error(error)

    assert result.status_code == 401


def test_maps_403():
    error = GitHubAPIError(
        status_code=403,
        message="Forbidden",
        headers=httpx.Headers({
            "X-RateLimit-Remaining": "10"
        }),
    )

    result = map_github_error(error)

    assert result.status_code == 403


def test_maps_403_rate_limit():
    error = GitHubAPIError(
        status_code=403,
        message="API rate limit exceeded",
        headers=httpx.Headers({
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1790000000",
        }),
    )

    result = map_github_error(error)

    assert result.status_code == 429


def test_maps_404():
    error = GitHubAPIError(
        status_code=404,
        message="Not Found",
    )

    result = map_github_error(error)

    assert result.status_code == 404


def test_maps_500_to_503():
    error = GitHubAPIError(
        status_code=500,
        message="Internal Server Error",
    )

    result = map_github_error(error)

    assert result.status_code == 503


def test_maps_429():
    error = GitHubAPIError(
        status_code=429,
        message="Too many requests",
        headers=httpx.Headers({
            "Retry-After": "60"
        }),
    )

    result = map_github_error(error)

    assert result.status_code == 429
    assert result.headers["Retry-After"] == "60"