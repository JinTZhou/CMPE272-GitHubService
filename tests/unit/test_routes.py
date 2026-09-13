# Author: Jin Ting Zhou

import httpx
import pytest
from fastapi.testclient import TestClient

from app.github_client import GitHubAPIError
from app.main import app
from app.routes import issues

pytestmark = pytest.mark.unit

client = TestClient(app)

def test_create_issue_route(monkeypatch):

    def fake_create_issue(
        title,
        body=None,
        labels=None,
    ):
        return {
            "number": 10,
            "html_url": "https://github.com/test/10",
            "state": "open",
            "title": title,
            "body": body,
            "labels": [
                {"name": "bug"},
                {"name": "test"},
            ],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }

    monkeypatch.setattr(
        issues.github_client,
        "create_issue",
        fake_create_issue,
    )

    response = client.post(
        "/issues",
        json={
            "title": "Test issue",
            "body": "Test body",
            "labels": ["bug", "test"],
        },
    )

    assert response.status_code == 201
    assert response.headers["Location"] == "/issues/10"

    data = response.json()

    assert data["number"] == 10
    assert data["title"] == "Test issue"
    assert data["labels"] == [
        "bug",
        "test",
    ]

def test_list_issues_route(monkeypatch):

    github_response = httpx.Response(
        200,
        json=[
            {
                "number": 1,
                "html_url": "https://github.com/test/1",
                "state": "open",
                "title": "Issue 1",
                "body": "Body 1",
                "labels": [
                    {"name": "bug"},
                ],
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        ],
        headers={
            "Link": (
                '<https://example.com?page=2>; rel="next"'
            )
        },
    )

    def fake_list_issues(
        state,
        labels,
        page,
        per_page,
    ):
        assert state == "open"
        assert page == 2
        assert per_page == 10
        assert labels == "bug"

        return github_response

    monkeypatch.setattr(
        issues.github_client,
        "list_issues",
        fake_list_issues,
    )

    response = client.get(
        "/issues",
        params={
            "state": "open",
            "labels": "bug",
            "page": 2,
            "per_page": 10,
        },
    )

    assert response.status_code == 200
    assert response.headers["Link"].startswith(
        "<https://example.com?page=2>"
    )

    data = response.json()

    assert data[0]["number"] == 1
    assert data[0]["labels"] == ["bug"]

def test_get_issue_route(monkeypatch):

    def fake_get_issue(number):
        assert number == 7

        return {
            "number": 7,
            "html_url": "https://github.com/test/7",
            "state": "open",
            "title": "Issue 7",
            "body": "Body",
            "labels": [
                {"name": "bug"},
            ],
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }

    monkeypatch.setattr(
        issues.github_client,
        "get_issue",
        fake_get_issue,
    )

    response = client.get("/issues/7")

    assert response.status_code == 200
    assert response.json()["number"] == 7

def test_create_comment_route(monkeypatch):

    def fake_create_comment(
        number,
        body,
    ):
        return {
            "id": 123,
            "body": body,
            "user": {
                "login": "test-user",
            },
            "created_at": "2026-01-01T00:00:00Z",
            "html_url": (
                "https://github.com/test/comment/123"
            ),
        }

    monkeypatch.setattr(
        issues.github_client,
        "create_comment",
        fake_create_comment,
    )

    response = client.post(
        "/issues/7/comments",
        json={
            "body": "Test comment",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] == 123
    assert data["body"] == "Test comment"
    assert data["user"] == "test-user"

def test_list_comments_route(monkeypatch):

    github_response = httpx.Response(
        200,
        json=[
            {
                "id": 1,
                "body": "Comment",
                "user": {
                    "login": "test-user",
                },
                "created_at": "2026-01-01T00:00:00Z",
                "html_url": (
                    "https://github.com/test/comment/1"
                ),
            }
        ],
        headers={
            "Link": (
                '<https://example.com?page=2>; rel="next"'
            )
        },
    )

    def fake_list_comments(
        number,
        page,
        per_page,
    ):
        assert number == 7
        assert page == 1
        assert per_page == 10

        return github_response

    monkeypatch.setattr(
        issues.github_client,
        "list_comments",
        fake_list_comments,
    )

    response = client.get(
        "/issues/7/comments",
        params={
            "page": 1,
            "per_page": 10,
        },
    )

    assert response.status_code == 200
    assert "Link" in response.headers

    data = response.json()

    assert data[0]["id"] == 1

def test_create_issue_route_maps_github_error(
    monkeypatch,
):

    def fake_create_issue(
        title,
        body=None,
        labels=None,
    ):
        raise GitHubAPIError(
            status_code=404,
            message="Not Found",
        )

    monkeypatch.setattr(
        issues.github_client,
        "create_issue",
        fake_create_issue,
    )

    response = client.post(
        "/issues",
        json={
            "title": "Test",
        },
    )

    assert response.status_code == 404

def test_get_issue_route_maps_404(monkeypatch):

    def fake_get_issue(number):
        raise GitHubAPIError(
            status_code=404,
            message="Issue not found",
        )

    monkeypatch.setattr(
        issues.github_client,
        "get_issue",
        fake_get_issue,
    )

    response = client.get("/issues/999")

    assert response.status_code == 404


def test_update_issue_route_maps_error(monkeypatch):

    def fake_update_issue(
        number,
        title=None,
        body=None,
        state=None,
    ):
        raise GitHubAPIError(
            status_code=500,
            message="GitHub failure",
        )

    monkeypatch.setattr(
        issues.github_client,
        "update_issue",
        fake_update_issue,
    )

    response = client.patch(
        "/issues/7",
        json={
            "state": "closed",
        },
    )

    assert response.status_code == 503


def test_create_comment_route_maps_error(
    monkeypatch,
):

    def fake_create_comment(
        number,
        body,
    ):
        raise GitHubAPIError(
            status_code=404,
            message="Issue not found",
        )

    monkeypatch.setattr(
        issues.github_client,
        "create_comment",
        fake_create_comment,
    )

    response = client.post(
        "/issues/7/comments",
        json={
            "body": "Test",
        },
    )

    assert response.status_code == 404