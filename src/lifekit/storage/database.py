"""DuckDB storage layer for Lifekit."""

import json
from pathlib import Path

import duckdb
import structlog

from lifekit.models.events import Event, EventType

log = structlog.get_logger()

SCHEMA_SQL = """
-- Event store (source of truth)
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

-- Materialized views for current state
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
        results = self.conn.execute(query, params).fetchall()

        events = []
        for row in results:
            events.append(
                Event(
                    event_id=row[0],
                    event_type=EventType(row[1]),
                    timestamp=row[2],
                    entity_id=row[3],
                    data=json.loads(row[4]) if isinstance(row[4], str) else row[4],
                )
            )
        return events

    def get_habits(self, include_archived: bool = False) -> list[dict]:
        query = "SELECT * FROM habits"
        if not include_archived:
            query += " WHERE archived_at IS NULL"
        query += " ORDER BY created_at DESC"

        results = self.conn.execute(query).fetchall()
        return [
            {
                "habit_id": r[0],
                "name": r[1],
                "description": r[2],
                "why": r[3],
                "tiny_version": r[4],
                "created_at": r[5],
                "archived_at": r[6],
            }
            for r in results
        ]

    def get_habit_by_name(self, name: str) -> dict | None:
        result = self.conn.execute(
            "SELECT * FROM habits WHERE name = ? AND archived_at IS NULL", [name]
        ).fetchone()
        if not result:
            return None
        return {
            "habit_id": result[0],
            "name": result[1],
            "description": result[2],
            "why": result[3],
            "tiny_version": result[4],
            "created_at": result[5],
            "archived_at": result[6],
        }

    def get_habit_logs(self, habit_id: str, limit: int = 30) -> list[dict]:
        results = self.conn.execute(
            """
            SELECT * FROM habit_logs
            WHERE habit_id = ?
            ORDER BY completed_at DESC
            LIMIT ?
            """,
            [habit_id, limit],
        ).fetchall()
        return [
            {
                "log_id": r[0],
                "habit_id": r[1],
                "completed_at": r[2],
                "completed": r[3],
                "context": r[4],
                "mood_after": r[5],
                "energy_before": r[6],
                "difficulty": r[7],
                "quality": r[8],
                "notes": r[9],
            }
            for r in results
        ]

    def get_journal_entries(self, limit: int = 30) -> list[dict]:
        results = self.conn.execute(
            """
            SELECT * FROM journal_entries
            ORDER BY created_at DESC
            LIMIT ?
            """,
            [limit],
        ).fetchall()
        return [
            {
                "entry_id": r[0],
                "created_at": r[1],
                "content": r[2],
                "mood": r[3],
                "energy": r[4],
                "gratitude": r[5],
                "prompt_id": r[6],
                "tags": json.loads(r[7]) if isinstance(r[7], str) else r[7],
            }
            for r in results
        ]

    def search_journal(self, query: str) -> list[dict]:
        results = self.conn.execute(
            """
            SELECT * FROM journal_entries
            WHERE content ILIKE ?
            ORDER BY created_at DESC
            """,
            [f"%{query}%"],
        ).fetchall()
        return [
            {
                "entry_id": r[0],
                "created_at": r[1],
                "content": r[2],
                "mood": r[3],
                "energy": r[4],
                "gratitude": r[5],
                "prompt_id": r[6],
                "tags": json.loads(r[7]) if isinstance(r[7], str) else r[7],
            }
            for r in results
        ]

    def get_goals(self, status: str | None = None) -> list[dict]:
        query = "SELECT * FROM goals"
        params: list = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"

        results = self.conn.execute(query, params).fetchall()
        return [
            {
                "goal_id": r[0],
                "outcome": r[1],
                "deadline": r[2],
                "created_at": r[3],
                "completed_at": r[4],
                "status": r[5],
                "progress": r[6],
            }
            for r in results
        ]

    def get_goal_by_outcome(self, outcome: str) -> dict | None:
        result = self.conn.execute(
            "SELECT * FROM goals WHERE outcome ILIKE ?", [f"%{outcome}%"]
        ).fetchone()
        if not result:
            return None
        return {
            "goal_id": result[0],
            "outcome": result[1],
            "deadline": result[2],
            "created_at": result[3],
            "completed_at": result[4],
            "status": result[5],
            "progress": result[6],
        }

    def get_milestones(self, goal_id: str) -> list[dict]:
        results = self.conn.execute(
            """
            SELECT * FROM milestones
            WHERE goal_id = ?
            ORDER BY milestone_order ASC
            """,
            [goal_id],
        ).fetchall()
        return [
            {
                "milestone_id": r[0],
                "goal_id": r[1],
                "description": r[2],
                "target_date": r[3],
                "completed_at": r[4],
                "order": r[5],
            }
            for r in results
        ]

    def get_random_prompt(self, category: str | None = None) -> dict | None:
        query = "SELECT * FROM prompts"
        params: list = []
        if category:
            query += " WHERE category = ?"
            params.append(category)
        query += " ORDER BY RANDOM() LIMIT 1"

        result = self.conn.execute(query, params).fetchone()
        if not result:
            return None
        return {
            "prompt_id": result[0],
            "text": result[1],
            "category": result[2],
        }
