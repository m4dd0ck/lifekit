"""Tests for Lifekit storage layer."""

from datetime import datetime, timedelta

from lifekit.models import EventType
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

        goal = db.get_goal_by_outcome("Complete test")
        assert goal["status"] == "achieved"

    def test_abandon_goal(self, store: EventStore, db: Database) -> None:
        goal_id = store.create_goal(outcome="Abandon test")
        store.abandon_goal(goal_id)

        goal = db.get_goal_by_outcome("Abandon test")
        assert goal["status"] == "abandoned"

    def test_get_events_since(self, store: EventStore) -> None:
        store.create_habit(name="Recent habit")

        events = store.get_events_since(days=1)
        assert len(events) >= 1
