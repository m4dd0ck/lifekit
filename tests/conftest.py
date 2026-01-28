"""Pytest fixtures for Lifekit tests."""

from collections.abc import Generator
from datetime import datetime, timedelta

import pytest

from lifekit.storage.database import Database
from lifekit.storage.events import EventStore


@pytest.fixture
def db() -> Generator[Database, None, None]:
    """Create an in-memory database."""
    database = Database(":memory:")
    yield database
    database.close()


@pytest.fixture
def store(db: Database) -> EventStore:
    """Create an event store."""
    return EventStore(db)


@pytest.fixture
def populated_db(db: Database) -> Database:
    """Create a database with sample data."""
    store = EventStore(db)

    # Create habits
    habit1_id = store.create_habit(
        name="Morning run",
        description="Run in the morning",
        why="It gives me energy for the day",
        tiny_version="Put on running shoes",
    )
    habit2_id = store.create_habit(
        name="Read",
        description="Read for 30 minutes",
    )

    # Log habits
    for i in range(7):
        store.log_habit(
            habit_id=habit1_id,
            mood_after=4 if i % 2 == 0 else 3,
            energy_before=3,
            difficulty=2,
        )

    for i in range(3):
        store.log_habit(
            habit_id=habit2_id,
            mood_after=5,
        )

    # Create journal entries
    store.create_journal_entry(
        content="Had a productive day today. Finished all my tasks.",
        mood=8,
        energy=4,
        gratitude="Good weather, nice coffee",
    )
    store.create_journal_entry(
        content="Feeling a bit tired but overall okay.",
        mood=6,
        energy=2,
    )
    store.create_journal_entry(
        content="Great workout this morning. Feeling energized.",
        mood=9,
        energy=5,
        gratitude="Health, family",
    )

    # Create goals
    goal_id = store.create_goal(
        outcome="Run a 5k without stopping",
        deadline=datetime.now() + timedelta(days=60),
    )
    store.add_milestone(goal_id, "Run 1 mile without stopping")
    store.add_milestone(goal_id, "Run 2 miles without stopping")
    store.update_progress(goal_id, 30)

    return db


@pytest.fixture
def sample_habit_id(store: EventStore) -> str:
    """Create a sample habit and return its ID."""
    return store.create_habit(
        name="Test habit",
        description="A test habit",
        why="For testing",
    )
