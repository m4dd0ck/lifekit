"""DuckDB storage layer for Lifekit."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb
import structlog

from lifekit.errors import AmbiguousNameError, NotFoundError
from lifekit.models.events import Event, EventType

log = structlog.get_logger()

SCHEMA_SQL = """
-- Append-only event log; every write lands here first, then in the tables below
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    entity_id TEXT NOT NULL,
    data JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

-- Current-state tables, updated once per event as it is appended (no replay)
CREATE TABLE IF NOT EXISTS habits (
    habit_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    why TEXT,
    tiny_version TEXT,
    created_at TIMESTAMP NOT NULL,
    archived_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS habit_logs (
    log_id TEXT PRIMARY KEY,
    habit_id TEXT NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    completed BOOLEAN DEFAULT TRUE,
    context TEXT,
    mood_after INTEGER,
    energy_before INTEGER,
    difficulty INTEGER,
    quality INTEGER,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS journal_entries (
    entry_id TEXT PRIMARY KEY,
    created_at TIMESTAMP NOT NULL,
    content TEXT NOT NULL,
    mood INTEGER,
    energy INTEGER,
    gratitude TEXT,
    prompt_id TEXT,
    tags JSON
);

CREATE TABLE IF NOT EXISTS goals (
    goal_id TEXT PRIMARY KEY,
    outcome TEXT NOT NULL,
    deadline TIMESTAMP,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status TEXT DEFAULT 'active',
    progress INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS milestones (
    milestone_id TEXT PRIMARY KEY,
    goal_id TEXT NOT NULL,
    description TEXT NOT NULL,
    target_date TIMESTAMP,
    completed_at TIMESTAMP,
    milestone_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS prompts (
    prompt_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    category TEXT NOT NULL
);
"""

DEFAULT_PROMPTS = [
    ("p1", "What am I grateful for today?", "gratitude"),
    ("p2", "What challenged me today and what did I learn?", "reflection"),
    ("p3", "What emotions am I feeling right now?", "reflection"),
    ("p4", "What am I avoiding and why?", "shadow"),
    ("p5", "What would make today great?", "goal"),
    ("p6", "What's one small win I can celebrate?", "gratitude"),
    ("p7", "What patterns do I notice in my behavior this week?", "reflection"),
    ("p8", "If I could change one thing about today, what would it be?", "reflection"),
]


class Database:
    """DuckDB database for Lifekit storage."""

    def __init__(self, db_path: Path | str = ":memory:"):
        self.db_path: Path | str = Path(db_path) if db_path != ":memory:" else db_path
        self._conn: duckdb.DuckDBPyConnection | None = None

    @property
    def conn(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            if isinstance(self.db_path, Path):
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(str(self.db_path))
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        self.conn.execute(SCHEMA_SQL)
        for prompt_id, text, category in DEFAULT_PROMPTS:
            self.conn.execute(
                """
                INSERT INTO prompts (prompt_id, text, category)
                VALUES (?, ?, ?)
                ON CONFLICT (prompt_id) DO NOTHING
                """,
                [prompt_id, text, category],
            )
        log.info("database_initialized", path=str(self.db_path))

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def append_event(self, event: Event) -> None:
        self.conn.execute(
            """INSERT INTO events (event_id, event_type, timestamp, entity_id, data)
            VALUES (?, ?, ?, ?, ?)""",
            [
                event.event_id,
                event.event_type.value,
                event.timestamp,
                event.entity_id,
                json.dumps(event.data),
            ],
        )
        self._apply_event(event)

    def _apply_event(self, event: Event) -> None:
        data = event.data

        if event.event_type == EventType.HABIT_CREATED:
            self.conn.execute(
                """
                INSERT INTO habits (habit_id, name, description, why, tiny_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    event.entity_id,
                    data["name"],
                    data.get("description"),
                    data.get("why"),
                    data.get("tiny_version"),
                    event.timestamp,
                ],
            )

        elif event.event_type == EventType.HABIT_LOGGED:
            self.conn.execute(
                """
                INSERT INTO habit_logs (log_id, habit_id, completed_at, completed, context,
                    mood_after, energy_before, difficulty, quality, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    data["log_id"],
                    event.entity_id,
                    event.timestamp,
                    data.get("completed", True),
                    data.get("context"),
                    data.get("mood_after"),
                    data.get("energy_before"),
                    data.get("difficulty"),
                    data.get("quality"),
                    data.get("notes"),
                ],
            )

        elif event.event_type == EventType.HABIT_ARCHIVED:
            self.conn.execute(
                "UPDATE habits SET archived_at = ? WHERE habit_id = ?",
                [event.timestamp, event.entity_id],
            )

        elif event.event_type == EventType.JOURNAL_ENTRY_CREATED:
            self.conn.execute(
                """
                INSERT INTO journal_entries (entry_id, created_at, content, mood, energy,
                    gratitude, prompt_id, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    event.entity_id,
                    event.timestamp,
                    data["content"],
                    data.get("mood"),
                    data.get("energy"),
                    data.get("gratitude"),
                    data.get("prompt_id"),
                    json.dumps(data.get("tags", [])),
                ],
            )

        elif event.event_type == EventType.GOAL_CREATED:
            self.conn.execute(
                """
                INSERT INTO goals (goal_id, outcome, deadline, created_at, status, progress)
                VALUES (?, ?, ?, ?, 'active', 0)
                """,
                [
                    event.entity_id,
                    data["outcome"],
                    data.get("deadline"),
                    event.timestamp,
                ],
            )

        elif event.event_type == EventType.GOAL_MILESTONE_ADDED:
            self.conn.execute(
                """
                INSERT INTO milestones
                (milestone_id, goal_id, description, target_date, milestone_order)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    data["milestone_id"],
                    event.entity_id,
                    data["description"],
                    data.get("target_date"),
                    data["order"],
                ],
            )

        elif event.event_type == EventType.GOAL_PROGRESS_UPDATED:
            self.conn.execute(
                "UPDATE goals SET progress = ? WHERE goal_id = ?",
                [data["progress"], event.entity_id],
            )

        elif event.event_type == EventType.GOAL_COMPLETED:
            self.conn.execute(
                "UPDATE goals SET status = 'achieved', completed_at = ? WHERE goal_id = ?",
                [event.timestamp, event.entity_id],
            )

        elif event.event_type == EventType.GOAL_ABANDONED:
            self.conn.execute(
                "UPDATE goals SET status = 'abandoned', completed_at = ? WHERE goal_id = ?",
                [event.timestamp, event.entity_id],
            )

    def _fetch_dicts(self, query: str, params: list | None = None) -> list[dict]:
        """Run a query and return one dict per row, keyed by column name."""
        cursor = self.conn.execute(query, params or [])
        columns = [column[0] for column in cursor.description or []]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def _fetch_dict(self, query: str, params: list | None = None) -> dict | None:
        rows = self._fetch_dicts(query, params)
        return rows[0] if rows else None

    def get_events(
        self,
        event_type: EventType | None = None,
        entity_id: str | None = None,
        since: str | None = None,
    ) -> list[Event]:
        query = "SELECT event_id, event_type, timestamp, entity_id, data FROM events WHERE 1=1"
        params: list = []

        if event_type:
            query += " AND event_type = ?"
            params.append(event_type.value)
        if entity_id:
            query += " AND entity_id = ?"
            params.append(entity_id)
        if since:
            query += " AND timestamp >= ?"
            params.append(since)

        query += " ORDER BY timestamp ASC"
        return [
            Event(
                event_id=row["event_id"],
                event_type=EventType(row["event_type"]),
                timestamp=row["timestamp"],
                entity_id=row["entity_id"],
                data=_load_json(row["data"]),
            )
            for row in self._fetch_dicts(query, params)
        ]

    def get_habits(self, include_archived: bool = False) -> list[dict]:
        query = "SELECT * FROM habits"
        if not include_archived:
            query += " WHERE archived_at IS NULL"
        query += " ORDER BY created_at DESC"
        return self._fetch_dicts(query)

    def get_habit_by_name(self, name: str) -> dict:
        """Return the active habit with exactly this name.

        Raises:
            NotFoundError: No active habit has that name.
            AmbiguousNameError: More than one does (possible in a database written before
                duplicate names were refused).
        """
        rows = self._fetch_dicts(
            "SELECT * FROM habits WHERE name = ? AND archived_at IS NULL", [name]
        )
        return _exactly_one(rows, kind="habit", name=name)

    def has_habit(self, name: str) -> bool:
        """Whether an active habit already has exactly this name."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM habits WHERE name = ? AND archived_at IS NULL", [name]
        ).fetchone()
        return bool(row and row[0])

    def get_habit_logs(self, habit_id: str, limit: int = 30) -> list[dict]:
        return self._fetch_dicts(
            """
            SELECT * FROM habit_logs
            WHERE habit_id = ?
            ORDER BY completed_at DESC
            LIMIT ?
            """,
            [habit_id, limit],
        )

    def get_habit_logs_since(self, habit_id: str, since: datetime) -> list[dict]:
        """Every log of a habit at or after ``since``, newest first."""
        return self._fetch_dicts(
            """
            SELECT * FROM habit_logs
            WHERE habit_id = ? AND completed_at >= ?
            ORDER BY completed_at DESC
            """,
            [habit_id, since],
        )

    def get_journal_entries(self, limit: int = 30) -> list[dict]:
        return self._journal_rows(
            """
            SELECT * FROM journal_entries
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [limit],
        )

    def get_journal_entries_since(self, since: datetime) -> list[dict]:
        """Every journal entry written at or after ``since``, newest first."""
        return self._journal_rows(
            """
            SELECT * FROM journal_entries
            WHERE created_at >= ?
            ORDER BY created_at DESC
            """,
            [since],
        )

    def search_journal(self, query: str) -> list[dict]:
        return self._journal_rows(
            """
            SELECT * FROM journal_entries
            WHERE content ILIKE ?
            ORDER BY created_at DESC
            """,
            [f"%{query}%"],
        )

    def _journal_rows(self, query: str, params: list) -> list[dict]:
        rows = self._fetch_dicts(query, params)
        for row in rows:
            row["tags"] = _load_json(row["tags"])
        return rows

    def get_goals(self, status: str | None = None) -> list[dict]:
        query = "SELECT * FROM goals"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        return self._fetch_dicts(query, params)

    def get_goal_by_outcome(self, outcome: str) -> dict:
        """Return the active goal whose outcome matches, ignoring case.

        Raises:
            NotFoundError: No active goal has that outcome.
            AmbiguousNameError: More than one does (possible in a database written before
                duplicate outcomes were refused).
        """
        rows = self._fetch_dicts(
            "SELECT * FROM goals WHERE LOWER(outcome) = LOWER(?) AND status = 'active'",
            [outcome],
        )
        return _exactly_one(rows, kind="goal", name=outcome)

    def has_goal(self, outcome: str) -> bool:
        """Whether an active goal already has this outcome, ignoring case."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM goals WHERE LOWER(outcome) = LOWER(?) AND status = 'active'",
            [outcome],
        ).fetchone()
        return bool(row and row[0])

    def get_milestones(self, goal_id: str) -> list[dict]:
        return self._fetch_dicts(
            """
            SELECT milestone_id, goal_id, description, target_date, completed_at,
                milestone_order AS "order"
            FROM milestones
            WHERE goal_id = ?
            ORDER BY milestone_order ASC
            """,
            [goal_id],
        )

    def get_random_prompt(self, category: str | None = None) -> dict | None:
        query = "SELECT * FROM prompts"
        params: list = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY RANDOM() LIMIT 1"
        return self._fetch_dict(query, params)


def _exactly_one(rows: list[dict], kind: str, name: str) -> dict:
    if not rows:
        raise NotFoundError(f"{kind.capitalize()} not found: {name}")
    if len(rows) > 1:
        raise AmbiguousNameError(
            f"{len(rows)} active {kind}s are named '{name}'; "
            f"finish or archive all but one before using the name"
        )
    return rows[0]


def _load_json(value: Any) -> Any:
    """Decode a JSON column, which DuckDB may hand back already parsed or as text."""
    return json.loads(value) if isinstance(value, str) else value
