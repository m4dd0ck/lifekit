"""Tests for Lifekit storage layer."""

from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pytest

from lifekit.errors import AmbiguousNameError, DuplicateNameError, InvalidValueError, NotFoundError
from lifekit.models import Event, EventType
from lifekit.storage.database import Database
from lifekit.storage.events import EventStore


class TestDatabase:
    def test_database_initialization(self, db: Database) -> None:
        # Verify tables exist
        result = db.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        table_names = [r[0] for r in result]

        assert "events" in table_names
        assert "habits" in table_names
        assert "habit_logs" in table_names
        assert "journal_entries" in table_names
        assert "goals" in table_names
        assert "milestones" in table_names
        assert "prompts" in table_names

    def test_default_prompts_loaded(self, db: Database) -> None:
        result = db.conn.execute("SELECT COUNT(*) FROM prompts").fetchone()
        assert result[0] > 0

    def test_get_random_prompt(self, db: Database) -> None:
        prompt = db.get_random_prompt()
        assert prompt is not None
        assert "text" in prompt
        assert "category" in prompt

    def test_get_random_prompt_by_category(self, db: Database) -> None:
        prompt = db.get_random_prompt(category="gratitude")
        assert prompt is not None
        assert prompt["category"] == "gratitude"

    def test_rows_map_by_column_name_not_position(self, tmp_path: Path) -> None:
        # Reason: a file whose habits table has the same columns in another order must still
        # read back correctly; positional indices would swap name and description.
        db_path = tmp_path / "reordered.db"
        conn = duckdb.connect(str(db_path))
        conn.execute(
            """
            CREATE TABLE habits (
                description TEXT,
                name TEXT NOT NULL,
                habit_id TEXT PRIMARY KEY,
                archived_at TIMESTAMP,
                created_at TIMESTAMP NOT NULL,
                tiny_version TEXT,
                why TEXT
            )
            """
        )
        conn.close()

        database = Database(db_path)
        store = EventStore(database)
        habit_id = store.create_habit(name="Stretch", description="Ten minutes", why="Back")

        habit = database.get_habit_by_name("Stretch")
        assert habit is not None
        assert habit["habit_id"] == habit_id
        assert habit["name"] == "Stretch"
        assert habit["description"] == "Ten minutes"
        assert habit["why"] == "Back"
        assert habit["archived_at"] is None
        assert [h["name"] for h in database.get_habits()] == ["Stretch"]
        database.close()


class TestEventStore:
    def test_create_habit(self, store: EventStore, db: Database) -> None:
        habit_id = store.create_habit(
            name="Test habit",
            description="A test",
            why="Testing",
            tiny_version="Do one thing",
        )

        assert habit_id is not None

        # Verify habit in materialized view
        habit = db.get_habit_by_name("Test habit")
        assert habit is not None
        assert habit["why"] == "Testing"

        # Verify event stored
        events = db.get_events(event_type=EventType.HABIT_CREATED)
        assert len(events) == 1
        assert events[0].entity_id == habit_id

    def test_log_habit(self, store: EventStore, db: Database) -> None:
        habit_id = store.create_habit(name="Log test")

        log_id = store.log_habit(
            habit_id=habit_id,
            mood_after=4,
            energy_before=3,
            difficulty=2,
            context="Morning",
        )

        assert log_id is not None

        # Verify log in materialized view
        logs = db.get_habit_logs(habit_id)
        assert len(logs) == 1
        assert logs[0]["mood_after"] == 4
        assert logs[0]["context"] == "Morning"

    def test_archive_habit(self, store: EventStore, db: Database) -> None:
        habit_id = store.create_habit(name="Archive test")
        store.archive_habit(habit_id)

        # Should not appear in default list
        habits = db.get_habits(include_archived=False)
        assert not any(h["habit_id"] == habit_id for h in habits)

        # Should appear with archived flag
        habits = db.get_habits(include_archived=True)
        assert any(h["habit_id"] == habit_id for h in habits)

    def test_create_journal_entry(self, store: EventStore, db: Database) -> None:
        entry_id = store.create_journal_entry(
            content="Today was great.",
            mood=8,
            energy=4,
            gratitude="Sunshine",
            tags=["happy", "productive"],
        )

        assert entry_id is not None

        entries = db.get_journal_entries()
        assert len(entries) == 1
        assert entries[0]["content"] == "Today was great."
        assert entries[0]["mood"] == 8

    def test_search_journal(self, store: EventStore, db: Database) -> None:
        store.create_journal_entry(content="Went for a morning run")
        store.create_journal_entry(content="Worked on the project")
        store.create_journal_entry(content="Another run in the evening")

        results = db.search_journal("run")
        assert len(results) == 2

    def test_create_goal(self, store: EventStore, db: Database) -> None:
        deadline = datetime.now() + timedelta(days=30)
        goal_id = store.create_goal(
            outcome="Run a 5k",
            deadline=deadline,
        )

        assert goal_id is not None

        goals = db.get_goals()
        assert len(goals) == 1
        assert goals[0]["outcome"] == "Run a 5k"
        assert goals[0]["status"] == "active"

    def test_add_milestone(self, store: EventStore, db: Database) -> None:
        goal_id = store.create_goal(outcome="Test goal")

        milestone_id = store.add_milestone(
            goal_id=goal_id,
            description="First step",
        )

        assert milestone_id is not None

        milestones = db.get_milestones(goal_id)
        assert len(milestones) == 1
        assert milestones[0]["description"] == "First step"
        assert milestones[0]["order"] == 1

    def test_update_progress(self, store: EventStore, db: Database) -> None:
        goal_id = store.create_goal(outcome="Progress test")
        store.update_progress(goal_id, 50)

        goal = db.get_goal_by_outcome("Progress test")
        assert goal["progress"] == 50

    def test_complete_goal(self, store: EventStore, db: Database) -> None:
        goal_id = store.create_goal(outcome="Complete test")
        store.complete_goal(goal_id)

        (goal,) = db.get_goals(status="achieved")
        assert goal["goal_id"] == goal_id

    def test_abandon_goal(self, store: EventStore, db: Database) -> None:
        goal_id = store.create_goal(outcome="Abandon test")
        store.abandon_goal(goal_id)

        (goal,) = db.get_goals(status="abandoned")
        assert goal["goal_id"] == goal_id

    def test_get_events_since(self, store: EventStore) -> None:
        store.create_habit(name="Recent habit")

        events = store.get_events_since(days=1)
        assert len(events) >= 1


class TestStoreValidation:
    """The store is the boundary: bad values are rejected before any event is written."""

    def test_log_habit_rejects_out_of_range_mood(
        self, store: EventStore, db: Database, sample_habit_id: str
    ) -> None:
        with pytest.raises(InvalidValueError, match="mood_after"):
            store.log_habit(sample_habit_id, mood_after=99)

        assert db.get_habit_logs(sample_habit_id) == []
        assert db.get_events(event_type=EventType.HABIT_LOGGED) == []

    def test_journal_entry_rejects_mood_above_ten(self, store: EventStore, db: Database) -> None:
        with pytest.raises(InvalidValueError, match="mood"):
            store.create_journal_entry(content="Too happy", mood=11)

        assert db.get_journal_entries() == []

    def test_update_progress_rejects_values_outside_0_to_100(
        self, store: EventStore, db: Database
    ) -> None:
        goal_id = store.create_goal(outcome="Bounded")

        with pytest.raises(InvalidValueError, match="progress"):
            store.update_progress(goal_id, 150)

        goal = db.get_goal_by_outcome("Bounded")
        assert goal is not None
        assert goal["progress"] == 0

    def test_create_habit_rejects_empty_name(self, store: EventStore, db: Database) -> None:
        with pytest.raises(InvalidValueError, match="name"):
            store.create_habit(name="")

        assert db.get_habits() == []

    def test_error_message_is_one_readable_line(
        self, store: EventStore, sample_habit_id: str
    ) -> None:
        with pytest.raises(InvalidValueError) as excinfo:
            store.log_habit(sample_habit_id, mood_after=0, quality=6)

        message = str(excinfo.value)
        assert "\n" not in message
        assert "mood_after" in message
        assert "quality" in message


class TestLookupByName:
    """Names identify exactly one live habit or goal, or the lookup says why not."""

    def test_goal_lookup_is_exact_not_partial(self, store: EventStore, db: Database) -> None:
        store.create_goal(outcome="Run a 5k without stopping")

        with pytest.raises(NotFoundError, match="Goal not found: Run a 5k"):
            db.get_goal_by_outcome("Run a 5k")

    def test_goal_lookup_ignores_case(self, store: EventStore, db: Database) -> None:
        goal_id = store.create_goal(outcome="Run a 5k")

        assert db.get_goal_by_outcome("run A 5K")["goal_id"] == goal_id

    def test_goal_lookup_rejects_ambiguous_name(self, store: EventStore, db: Database) -> None:
        # Reason: a database written before duplicate names were refused can hold two.
        for _ in range(2):
            db.append_event(
                Event(
                    event_type=EventType.GOAL_CREATED,
                    entity_id=f"goal-{_}",
                    data={"outcome": "Twice", "deadline": None},
                )
            )

        with pytest.raises(AmbiguousNameError, match="2 active goals are named 'Twice'"):
            db.get_goal_by_outcome("Twice")

    def test_goal_lookup_sees_only_active_goals(self, store: EventStore, db: Database) -> None:
        old_id = store.create_goal(outcome="Run a 5k")
        store.complete_goal(old_id)
        new_id = store.create_goal(outcome="Run a 5k")

        assert db.get_goal_by_outcome("Run a 5k")["goal_id"] == new_id

    def test_habit_lookup_raises_when_missing(self, db: Database) -> None:
        with pytest.raises(NotFoundError, match="Habit not found: Nope"):
            db.get_habit_by_name("Nope")

    def test_create_habit_refuses_duplicate_name(self, store: EventStore, db: Database) -> None:
        store.create_habit(name="Read")

        with pytest.raises(DuplicateNameError, match="already"):
            store.create_habit(name="Read")

        assert len(db.get_habits()) == 1

    def test_archived_habit_name_can_be_reused(self, store: EventStore, db: Database) -> None:
        old_id = store.create_habit(name="Read")
        store.archive_habit(old_id)

        new_id = store.create_habit(name="Read")

        assert db.get_habit_by_name("Read")["habit_id"] == new_id

    def test_create_goal_refuses_duplicate_active_outcome(
        self, store: EventStore, db: Database
    ) -> None:
        store.create_goal(outcome="Run a 5k")

        with pytest.raises(DuplicateNameError, match="already"):
            store.create_goal(outcome="run a 5k")

        assert len(db.get_goals()) == 1


def _append_old_event(db: Database, event_type: EventType, entity_id: str, data: dict) -> None:
    db.append_event(
        Event(
            event_type=event_type,
            entity_id=entity_id,
            timestamp=datetime.now() - timedelta(days=30),
            data=data,
        )
    )


class TestDateWindows:
    def test_habit_logs_since_excludes_older_logs(
        self, store: EventStore, db: Database, sample_habit_id: str
    ) -> None:
        _append_old_event(
            db, EventType.HABIT_LOGGED, sample_habit_id, {"log_id": "old", "completed": True}
        )
        recent_id = store.log_habit(sample_habit_id)

        logs = db.get_habit_logs_since(sample_habit_id, datetime.now() - timedelta(days=7))

        assert [log["log_id"] for log in logs] == [recent_id]

    def test_journal_entries_since_excludes_older_entries(
        self, store: EventStore, db: Database
    ) -> None:
        _append_old_event(db, EventType.JOURNAL_ENTRY_CREATED, "old", {"content": "Long ago"})
        store.create_journal_entry(content="This week")

        entries = db.get_journal_entries_since(datetime.now() - timedelta(days=7))

        assert [entry["content"] for entry in entries] == ["This week"]


STATE_TABLES = ("habits", "habit_logs", "journal_entries", "goals", "milestones")


def _snapshot(db: Database) -> dict[str, list[tuple]]:
    return {
        table: db.conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
        for table in STATE_TABLES
    }


class TestRebuild:
    def test_rebuild_restores_deleted_and_corrupted_state(self, populated_db: Database) -> None:
        store = EventStore(populated_db)
        habit = populated_db.get_habit_by_name("Read")
        store.archive_habit(habit["habit_id"])
        before = _snapshot(populated_db)
        assert all(rows for rows in before.values())

        populated_db.conn.execute("DELETE FROM habit_logs")
        populated_db.conn.execute("DELETE FROM milestones")
        populated_db.conn.execute("UPDATE goals SET progress = 0, status = 'abandoned'")
        populated_db.conn.execute("UPDATE habits SET archived_at = NULL, why = 'tampered'")
        populated_db.conn.execute("UPDATE journal_entries SET mood = NULL")
        assert _snapshot(populated_db) != before

        counts = populated_db.rebuild_from_events()

        assert _snapshot(populated_db) == before
        assert counts == {table: len(rows) for table, rows in before.items()}

    def test_rebuild_keeps_prompts_and_events(self, populated_db: Database) -> None:
        prompts_before = populated_db.conn.execute("SELECT COUNT(*) FROM prompts").fetchone()
        events_before = populated_db.get_events()

        populated_db.rebuild_from_events()

        assert (
            populated_db.conn.execute("SELECT COUNT(*) FROM prompts").fetchone() == prompts_before
        )
        assert populated_db.get_events() == events_before

    def test_rebuild_applies_events_in_order_within_the_same_instant(self, db: Database) -> None:
        # Reason: a goal created and updated in one microsecond must still end at 40, not 0.
        instant = datetime(2026, 1, 1, 9, 0, 0)
        db.append_event(
            Event(
                event_type=EventType.GOAL_CREATED,
                entity_id="g1",
                timestamp=instant,
                data={"outcome": "Same instant", "deadline": None},
            )
        )
        db.append_event(
            Event(
                event_type=EventType.GOAL_PROGRESS_UPDATED,
                entity_id="g1",
                timestamp=instant,
                data={"progress": 40},
            )
        )

        db.rebuild_from_events()

        assert db.get_goal_by_outcome("Same instant")["progress"] == 40
