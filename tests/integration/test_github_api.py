# Author: Jin Ting Zhou

import os

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app.main import app

load_dotenv()

pytestmark = pytest.mark.integration


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def github_enabled():
    required = [
        "GITHUB_TOKEN",
        "GITHUB_OWNER",
        "GITHUB_REPO",
    ]

    missing = [
        variable
        for variable in required
        if not os.getenv(variable)
    ]

    if missing:
        pytest.skip(
            f"Missing environment variables: {missing}"
        )

def test_create_and_get_issue(
    client,
    github_enabled,
):
    response = client.post(
        "/issues",
        json={
            "title": (
                "Integration test issue"
            ),
            "body": (
                "Created by automated integration test."
            ),
            "labels": [],
        },
    )

    assert response.status_code == 201

    created = response.json()

    issue_number = created["number"]

    assert created["title"] == (
        "Integration test issue"
    )

    response = client.get(
        f"/issues/{issue_number}"
    )

    assert response.status_code == 200

    issue = response.json()

    assert issue["number"] == issue_number
    assert issue["title"] == (
        "Integration test issue"
    )

def test_update_close_reopen(
    client,
    github_enabled,
):
    response = client.post(
        "/issues",
        json={
            "title": "Update integration test",
            "body": "Original body",
            "labels": [],
        },
    )

    assert response.status_code == 201

    issue_number = response.json()["number"]

    response = client.patch(
        f"/issues/{issue_number}",
        json={
            "title": "Updated integration test",
            "body": "Updated body",
        },
    )

    assert response.status_code == 200

    updated = response.json()

    assert updated["title"] == (
        "Updated integration test"
    )

    assert updated["body"] == (
        "Updated body"
    )

    response = client.patch(
        f"/issues/{issue_number}",
        json={
            "state": "closed",
        },
    )

    assert response.status_code == 200
    assert response.json()["state"] == "closed"

    response = client.patch(
        f"/issues/{issue_number}",
        json={
            "state": "open",
        },
    )

    assert response.status_code == 200
    assert response.json()["state"] == "open"

def test_create_comment(
    client,
    github_enabled,
):
    response = client.post(
        "/issues",
        json={
            "title": "Comment integration test",
            "body": "Testing comments",
            "labels": [],
        },
    )

    assert response.status_code == 201

    issue_number = response.json()["number"]

    response = client.post(
        f"/issues/{issue_number}/comments",
        json={
            "body": (
                "Integration test comment"
            ),
        },
    )

    assert response.status_code == 201

    comment = response.json()

    assert comment["body"] == (
        "Integration test comment"
    )

    response = client.get(
        f"/issues/{issue_number}/comments"
    )

    assert response.status_code == 200

    comments = response.json()

    assert any(
        comment["body"]
        == "Integration test comment"
        for comment in comments
    )