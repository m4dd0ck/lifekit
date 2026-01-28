"""Tests for Lifekit models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from lifekit.models import (
    Event,
    EventType,
    Goal,
    GoalStatus,
    Habit,
    HabitLog,
    JournalEntry,
    Milestone,
    Prompt,
)


class TestEventModel:
    def test_event_creation(self) -> None:
        event = Event(
            event_type=EventType.HABIT_CREATED,
            entity_id="test-123",
            data={"name": "Test"},
        )
        assert event.event_id is not None
        assert event.event_type == EventType.HABIT_CREATED
        assert event.entity_id == "test-123"
        assert event.timestamp is not None

    def test_event_type_values(self) -> None:
        assert EventType.HABIT_CREATED.value == "habit.created"
        assert EventType.JOURNAL_ENTRY_CREATED.value == "journal.entry_created"
        assert EventType.GOAL_COMPLETED.value == "goal.completed"


class TestHabitModel:
    def test_habit_creation(self) -> None:
        habit = Habit(
            habit_id="h1",
            name="Morning run",
            description="Run every morning",
            why="Energy for the day",
            tiny_version="Put on shoes",
            created_at=datetime.now(),
        )
        assert habit.name == "Morning run"
        assert habit.archived_at is None

    def test_habit_log_validation(self) -> None:
        log = HabitLog(
            log_id="l1",
            habit_id="h1",
            completed_at=datetime.now(),
            mood_after=4,
            energy_before=3,
        )
        assert log.mood_after == 4
        assert log.completed is True

    def test_habit_log_mood_range(self) -> None:
        with pytest.raises(ValidationError):
            HabitLog(
                log_id="l1",
                habit_id="h1",
                completed_at=datetime.now(),
                mood_after=6,  # Invalid: must be 1-5
            )

    def test_habit_log_energy_range(self) -> None:
        with pytest.raises(ValidationError):
            HabitLog(
                log_id="l1",
                habit_id="h1",
                completed_at=datetime.now(),
                energy_before=0,  # Invalid: must be 1-5
            )


class TestJournalModel:
    def test_journal_entry_creation(self) -> None:
        entry = JournalEntry(
            entry_id="j1",
            created_at=datetime.now(),
            content="Today was a good day.",
            mood=8,
            energy=4,
            gratitude="Sunshine, coffee",
        )
        assert entry.content == "Today was a good day."
        assert entry.mood == 8

    def test_journal_mood_range(self) -> None:
        with pytest.raises(ValidationError):
            JournalEntry(
                entry_id="j1",
                created_at=datetime.now(),
                content="Test",
                mood=11,  # Invalid: must be 1-10
            )

    def test_prompt_creation(self) -> None:
        prompt = Prompt(
            prompt_id="p1",
            text="What are you grateful for?",
            category="gratitude",
        )
        assert prompt.category == "gratitude"


class TestGoalModel:
    def test_goal_creation(self) -> None:
        goal = Goal(
            goal_id="g1",
            outcome="Run a 5k",
            created_at=datetime.now(),
        )
        assert goal.status == GoalStatus.ACTIVE
        assert goal.progress == 0

    def test_goal_status_enum(self) -> None:
        assert GoalStatus.ACTIVE.value == "active"
        assert GoalStatus.ACHIEVED.value == "achieved"
        assert GoalStatus.ABANDONED.value == "abandoned"

    def test_goal_progress_range(self) -> None:
        with pytest.raises(ValidationError):
            Goal(
                goal_id="g1",
                outcome="Test",
                created_at=datetime.now(),
                progress=101,  # Invalid: must be 0-100
            )

    def test_milestone_creation(self) -> None:
        milestone = Milestone(
            milestone_id="m1",
            goal_id="g1",
            description="Run 1 mile",
            order=1,
        )
        assert milestone.completed_at is None
