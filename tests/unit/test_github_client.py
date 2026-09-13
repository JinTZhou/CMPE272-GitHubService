# Author: Jin Ting Zhou

import httpx
import pytest

from app.github_client import GitHubAPIError, GitHubClient

pytestmark = pytest.mark.unit

def make_client():
    return GitHubClient(
        token="test-token",
        owner="test-owner",
        repo="test-repo",
    )


def test_create_issue_success(monkeypatch):
    client = make_client()

    def fake_post(url, json):
        assert url == "/repos/test-owner/test-repo/issues"
        assert json == {
            "title": "Test issue",
            "body": "Test body",
            "labels": ["bug"],
        }

        return httpx.Response(
            201,
            json={
                "number": 1,
                "title": "Test issue",
            },
        )

    monkeypatch.setattr(
        client.client,
        "post",
        fake_post,
    )

    result = client.create_issue(
        title="Test issue",
        body="Test body",
        labels=["bug"],
    )

    assert result["number"] == 1
    assert result["title"] == "Test issue"

    client.close()


def test_create_issue_without_optional_fields(monkeypatch):
    client = make_client()

    def fake_post(url, json):
        assert json == {
            "title": "Only title",
        }

        return httpx.Response(
            201,
            json={
                "number": 2,
                "title": "Only title",
            },
        )

    monkeypatch.setattr(
        client.client,
        "post",
        fake_post,
    )

    result = client.create_issue(
        title="Only title"
    )

    assert result["number"] == 2

    client.close()


def test_get_issue(monkeypatch):
    client = make_client()

    def fake_get(url):
        assert url == "/repos/test-owner/test-repo/issues/5"

        return httpx.Response(
            200,
            json={
                "number": 5,
                "title": "Issue 5",
            },
        )

    monkeypatch.setattr(
        client.client,
        "get",
        fake_get,
    )

    result = client.get_issue(5)

    assert result["number"] == 5

    client.close()


def test_update_issue(monkeypatch):
    client = make_client()

    def fake_patch(url, json):
        assert url == "/repos/test-owner/test-repo/issues/5"
        assert json == {
            "title": "Updated",
            "body": "New body",
            "state": "closed",
        }

        return httpx.Response(
            200,
            json={
                "number": 5,
                "title": "Updated",
                "state": "closed",
            },
        )

    monkeypatch.setattr(
        client.client,
        "patch",
        fake_patch,
    )

    result = client.update_issue(
        number=5,
        title="Updated",
        body="New body",
        state="closed",
    )

    assert result["state"] == "closed"

    client.close()


def test_update_issue_only_state(monkeypatch):
    client = make_client()

    def fake_patch(url, json):
        assert json == {
            "state": "closed",
        }

        return httpx.Response(
            200,
            json={
                "number": 5,
                "state": "closed",
            },
        )

    monkeypatch.setattr(
        client.client,
        "patch",
        fake_patch,
    )

    result = client.update_issue(
        number=5,
        state="closed",
    )

    assert result["state"] == "closed"

    client.close()


def test_create_comment(monkeypatch):
    client = make_client()

    def fake_post(url, json):
        assert (
            url
            == "/repos/test-owner/test-repo"
               "/issues/5/comments"
        )

        assert json == {
            "body": "Test comment",
        }

        return httpx.Response(
            201,
            json={
                "id": 100,
                "body": "Test comment",
            },
        )

    monkeypatch.setattr(
        client.client,
        "post",
        fake_post,
    )

    result = client.create_comment(
        number=5,
        body="Test comment",
    )

    assert result["id"] == 100

    client.close()


def test_list_issues_without_labels(monkeypatch):
    client = make_client()

    def fake_get(url, params):
        assert url == "/repos/test-owner/test-repo/issues"
        assert params == {
            "state": "open",
            "page": 2,
            "per_page": 10,
        }

        return httpx.Response(
            200,
            json=[],
        )

    monkeypatch.setattr(
        client.client,
        "get",
        fake_get,
    )

    response = client.list_issues(
        state="open",
        page=2,
        per_page=10,
    )

    assert response.status_code == 200

    client.close()


def test_list_issues_with_labels(monkeypatch):
    client = make_client()

    def fake_get(url, params):
        assert params["labels"] == "bug"
        assert params["page"] == 1
        assert params["per_page"] == 20

        return httpx.Response(
            200,
            json=[],
        )

    monkeypatch.setattr(
        client.client,
        "get",
        fake_get,
    )

    response = client.list_issues(
        labels="bug",
        page=1,
        per_page=20,
    )

    assert response.status_code == 200

    client.close()


def test_list_comments(monkeypatch):
    client = make_client()

    def fake_get(url, params):
        assert (
            url
            == "/repos/test-owner/test-repo"
               "/issues/5/comments"
        )

        assert params == {
            "page": 2,
            "per_page": 10,
        }

        return httpx.Response(
            200,
            json=[],
        )

    monkeypatch.setattr(
        client.client,
        "get",
        fake_get,
    )

    response = client.list_comments(
        number=5,
        page=2,
        per_page=10,
    )

    assert response.status_code == 200

    client.close()

def test_handle_non_json_error_response():
    client = make_client()

    response = httpx.Response(
        500,
        text="Server error",
    )

    try:
        client._handle_response(response)
    except GitHubAPIError as exc:
        assert exc.status_code == 500
        assert exc.message == "GitHub API request failed"
        assert exc.response_body == {}

    client.close()

def test_is_rate_limited_when_remaining_zero():
    client = make_client()

    response = httpx.Response(
        403,
        headers={
            "X-RateLimit-Remaining": "0",
        },
    )

    assert client._is_rate_limited(response) is True

    client.close()


def test_is_rate_limited_when_status_429():
    client = make_client()

    response = httpx.Response(429)

    assert client._is_rate_limited(response) is True

    client.close()


def test_is_not_rate_limited():
    client = make_client()

    response = httpx.Response(
        403,
        headers={
            "X-RateLimit-Remaining": "10",
        },
    )

    assert client._is_rate_limited(response) is False

    client.close()