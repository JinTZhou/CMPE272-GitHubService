# Author: Jin Ting Zhou
# Persistent storage for processed GitHub webhook deliveries.

import sqlite3
from pathlib import Path
from typing import Optional


DATABASE_PATH = Path("events.db")


class EventStore:
    def __init__(self, database_path: Path = DATABASE_PATH):
        self.database_path = database_path
        self._initialize_database()

    def _connect(self):
        return sqlite3.connect(self.database_path)

    def _initialize_database(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS webhook_events (
                    id TEXT PRIMARY KEY,
                    event TEXT NOT NULL,
                    action TEXT,
                    issue_number INTEGER,
                    timestamp TEXT NOT NULL
                )
                """
            )

    def event_exists(self, delivery_id: str) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT 1
                FROM webhook_events
                WHERE id = ?
                """,
                (delivery_id,),
            )

            return cursor.fetchone() is not None

    def save_event(
        self,
        delivery_id: str,
        event: str,
        action: Optional[str],
        issue_number: Optional[int],
        timestamp: str,
    ):
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO webhook_events (
                    id,
                    event,
                    action,
                    issue_number,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    delivery_id,
                    event,
                    action,
                    issue_number,
                    timestamp,
                ),
            )

    def get_events(self, limit: int = 20):
        with self._connect() as connection:
            cursor = connection.execute(
                """
                SELECT
                    id,
                    event,
                    action,
                    issue_number,
                    timestamp
                FROM webhook_events
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )

            rows = cursor.fetchall()

        return [
            {
                "id": row[0],
                "event": row[1],
                "action": row[2],
                "issue_number": row[3],
                "timestamp": row[4],
            }
            for row in rows
        ]


event_store = EventStore()