# Author: Jin Ting Zhou

from app.storage.event_store import EventStore


def test_event_store_empty(tmp_path):

    database = tmp_path / "events.db"

    store = EventStore(database)

    assert store.get_events() == []


def test_event_does_not_exist(tmp_path):

    database = tmp_path / "events.db"

    store = EventStore(database)

    assert (
        store.event_exists("missing")
        is False
    )


def test_save_and_find_event(tmp_path):

    database = tmp_path / "events.db"

    store = EventStore(database)

    store.save_event(
        delivery_id="delivery-1",
        event="issues",
        action="opened",
        issue_number=42,
        timestamp="2026-01-01T00:00:00Z",
    )

    assert (
        store.event_exists("delivery-1")
        is True
    )


def test_get_events(tmp_path):

    database = tmp_path / "events.db"

    store = EventStore(database)

    store.save_event(
        delivery_id="delivery-1",
        event="issues",
        action="opened",
        issue_number=42,
        timestamp="2026-01-01T00:00:00Z",
    )

    store.save_event(
        delivery_id="delivery-2",
        event="issue_comment",
        action="created",
        issue_number=42,
        timestamp="2026-01-02T00:00:00Z",
    )

    events = store.get_events(limit=10)

    assert len(events) == 2
    assert events[0]["id"] == "delivery-2"
    assert events[1]["id"] == "delivery-1"


def test_get_events_limit(tmp_path):

    database = tmp_path / "events.db"

    store = EventStore(database)

    for i in range(5):
        store.save_event(
            delivery_id=f"id-{i}",
            event="issues",
            action="opened",
            issue_number=i,
            timestamp=f"2026-01-0{i+1}T00:00:00Z",
        )

    events = store.get_events(limit=2)

    assert len(events) == 2