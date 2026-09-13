# Author: Jin Ting Zhou

import hashlib
import hmac

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app
from app.routes import webhook
from app.routes.webhook import verify_signature
pytestmark = pytest.mark.unit

SECRET = "test-secret"
client = TestClient(app)


@pytest.fixture
def webhook_secret(monkeypatch):
    monkeypatch.setattr(
        "app.routes.webhook.WEBHOOK_SECRET",
        SECRET,
    )


def create_signature(body: bytes) -> str:
    digest = hmac.new(
        SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


def test_valid_signature(webhook_secret):
    body = b'{"action":"opened"}'

    signature = create_signature(body)

    verify_signature(
        body,
        signature,
    )


def test_invalid_signature(webhook_secret):
    body = b'{"action":"opened"}'

    with pytest.raises(
        HTTPException
    ) as exc:
        verify_signature(
            body,
            "sha256=wrong",
        )

    assert exc.value.status_code == 401


def test_tampered_body(webhook_secret):
    original_body = b'{"action":"opened"}'

    signature = create_signature(
        original_body
    )

    tampered_body = (
        b'{"action":"closed"}'
    )

    with pytest.raises(
        HTTPException
    ) as exc:
        verify_signature(
            tampered_body,
            signature,
        )

    assert exc.value.status_code == 401


def test_missing_signature(webhook_secret):
    body = b'{"action":"opened"}'

    with pytest.raises(
        HTTPException
    ) as exc:
        verify_signature(
            body,
            None,
        )

    assert exc.value.status_code == 401


# ---------------------------------------------------------------------------
# Endpoint-level webhook tests
# These exercise the actual /webhook and /events routes in addition to the
# lower-level verify_signature() tests above.
# ---------------------------------------------------------------------------

def make_endpoint_signature(body: bytes) -> str:
    digest = hmac.new(
        SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return f"sha256={digest}"


def test_webhook_success(monkeypatch):
    monkeypatch.setattr(
        webhook,
        "WEBHOOK_SECRET",
        SECRET,
    )

    class FakeStore:
        def __init__(self):
            self.saved = []

        def event_exists(self, delivery_id):
            return False

        def save_event(
            self,
            delivery_id,
            event,
            action,
            issue_number,
            timestamp,
        ):
            self.saved.append(
                {
                    "id": delivery_id,
                    "event": event,
                    "action": action,
                    "issue_number": issue_number,
                    "timestamp": timestamp,
                }
            )

    store = FakeStore()

    monkeypatch.setattr(
        webhook,
        "event_store",
        store,
    )

    body = (
        b'{"action":"opened",'
        b'"issue":{"number":42}}'
    )

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "delivery-123",
            "X-Hub-Signature-256": make_endpoint_signature(body),
        },
    )

    assert response.status_code == 204
    assert len(store.saved) == 1
    assert store.saved[0]["id"] == "delivery-123"
    assert store.saved[0]["event"] == "issues"
    assert store.saved[0]["action"] == "opened"
    assert store.saved[0]["issue_number"] == 42


def test_webhook_duplicate_delivery(monkeypatch):
    monkeypatch.setattr(
        webhook,
        "WEBHOOK_SECRET",
        SECRET,
    )

    class FakeStore:
        def __init__(self):
            self.save_called = False

        def event_exists(self, delivery_id):
            return True

        def save_event(self, *args, **kwargs):
            self.save_called = True

    store = FakeStore()

    monkeypatch.setattr(
        webhook,
        "event_store",
        store,
    )

    body = (
        b'{"action":"opened",'
        b'"issue":{"number":42}}'
    )

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "duplicate-1",
            "X-Hub-Signature-256": make_endpoint_signature(body),
        },
    )

    assert response.status_code == 204
    assert store.save_called is False


def test_webhook_ping(monkeypatch):
    monkeypatch.setattr(
        webhook,
        "WEBHOOK_SECRET",
        SECRET,
    )

    class FakeStore:
        def __init__(self):
            self.saved = None

        def event_exists(self, delivery_id):
            return False

        def save_event(self, **kwargs):
            self.saved = kwargs

    store = FakeStore()

    monkeypatch.setattr(
        webhook,
        "event_store",
        store,
    )

    body = b'{"zen":"Keep it simple"}'

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "ping",
            "X-GitHub-Delivery": "ping-1",
            "X-Hub-Signature-256": make_endpoint_signature(body),
        },
    )

    assert response.status_code == 204
    assert store.saved["event"] == "ping"
    assert store.saved["issue_number"] is None


def test_webhook_issue_comment_without_issue(monkeypatch):
    monkeypatch.setattr(
        webhook,
        "WEBHOOK_SECRET",
        SECRET,
    )

    class FakeStore:
        def __init__(self):
            self.saved = None

        def event_exists(self, delivery_id):
            return False

        def save_event(self, **kwargs):
            self.saved = kwargs

    store = FakeStore()

    monkeypatch.setattr(
        webhook,
        "event_store",
        store,
    )

    body = b'{"action":"created"}'

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issue_comment",
            "X-GitHub-Delivery": "comment-1",
            "X-Hub-Signature-256": make_endpoint_signature(body),
        },
    )

    assert response.status_code == 204
    assert store.saved["event"] == "issue_comment"
    assert store.saved["issue_number"] is None


def test_webhook_missing_delivery_id(monkeypatch):
    monkeypatch.setattr(
        webhook,
        "WEBHOOK_SECRET",
        SECRET,
    )

    body = b'{"action":"opened"}'

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": make_endpoint_signature(body),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Missing X-GitHub-Delivery header"
    )


def test_webhook_unsupported_event(monkeypatch):
    monkeypatch.setattr(
        webhook,
        "WEBHOOK_SECRET",
        SECRET,
    )

    body = b'{"action":"opened"}'

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "push",
            "X-GitHub-Delivery": "push-1",
            "X-Hub-Signature-256": make_endpoint_signature(body),
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Unsupported GitHub event"
    )


def test_webhook_invalid_endpoint_signature(monkeypatch):
    monkeypatch.setattr(
        webhook,
        "WEBHOOK_SECRET",
        SECRET,
    )

    body = b'{"action":"opened"}'

    response = client.post(
        "/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-GitHub-Event": "issues",
            "X-GitHub-Delivery": "bad-signature-1",
            "X-Hub-Signature-256": "sha256=wrong",
        },
    )

    assert response.status_code == 401


def test_events_route(monkeypatch):
    class FakeStore:
        def get_events(self, limit):
            assert limit == 5

            return [
                {
                    "id": "abc",
                    "event": "issues",
                    "action": "opened",
                    "issue_number": 1,
                    "timestamp": "2026-01-01T00:00:00Z",
                }
            ]

    monkeypatch.setattr(
        webhook,
        "event_store",
        FakeStore(),
    )

    response = client.get(
        "/events?limit=5"
    )

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": "abc",
            "event": "issues",
            "action": "opened",
            "issue_number": 1,
            "timestamp": "2026-01-01T00:00:00Z",
        }
    ]


def test_events_limit_validation():
    response = client.get("/events?limit=0")

    assert response.status_code == 422

    response = client.get("/events?limit=101")

    assert response.status_code == 422
