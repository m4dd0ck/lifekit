"""Event store wrapper for Lifekit.

One method per command. Each builds the Pydantic model for what it writes, so a bad value
is rejected here with an ``InvalidValueError`` before any event reaches the log.
"""

import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta

from pydantic import TypeAdapter, ValidationError

from lifekit.errors import DuplicateNameError, InvalidValueError
from lifekit.models.events import Event, EventType
from lifekit.models.goal import Goal, Milestone, Progress
from lifekit.models.habit import Habit, HabitLog
from lifekit.models.journal import JournalEntry
from lifekit.storage.database import Database


@contextmanager
def _rejecting_invalid_values(field: str = "value") -> Iterator[None]:
    """Turn a Pydantic validation report into one readable ``InvalidValueError`` line.

    Args:
        field: Name used when the report carries no location (a bare ``TypeAdapter`` check).
    """
    try:
        yield
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in error['loc']) or field}: {error['msg']}"
            for error in exc.errors()
        )
        raise InvalidValueError(problems) from None


def _validated[T](build: Callable[[], T]) -> T:
    with _rejecting_invalid_values():
        return build()


class EventStore:
    """High-level event store operations; validates every write before appending it."""

    def __init__(self, db: Database):
        self.db = db

    def create_habit(
        self,
        name: str,
        description: str | None = None,
        why: str | None = None,
        tiny_version: str | None = None,
    ) -> str:
        if self.db.has_habit(name):
            raise DuplicateNameError(f"A habit named '{name}' already exists")
        habit = _validated(
            lambda: Habit(
                habit_id=str(uuid.uuid4()),
                name=name,
                description=description,
                why=why,
                tiny_version=tiny_version,
                created_at=datetime.now(),
            )
        )
        event = Event(
            event_type=EventType.HABIT_CREATED,
            entity_id=habit.habit_id,
            timestamp=habit.created_at,
            data={
                "name": habit.name,
                "description": habit.description,
                "why": habit.why,
                "tiny_version": habit.tiny_version,
            },
        )
        self.db.append_event(event)
        return habit.habit_id

    def log_habit(
        self,
        habit_id: str,
        completed: bool = True,
        context: str | None = None,
        mood_after: int | None = None,
        energy_before: int | None = None,
        difficulty: int | None = None,
        quality: int | None = None,
        notes: str | None = None,
    ) -> str:
        habit_log = _validated(
            lambda: HabitLog(
                log_id=str(uuid.uuid4()),
                habit_id=habit_id,
                completed_at=datetime.now(),
                completed=completed,
                context=context,
                mood_after=mood_after,
                energy_before=energy_before,
                difficulty=difficulty,
                quality=quality,
                notes=notes,
            )
        )
        event = Event(
            event_type=EventType.HABIT_LOGGED,
            entity_id=habit_id,
            timestamp=habit_log.completed_at,
            data=habit_log.model_dump(exclude={"habit_id", "completed_at"}),
        )
        self.db.append_event(event)
        return habit_log.log_id

    def archive_habit(self, habit_id: str) -> None:
        event = Event(
            event_type=EventType.HABIT_ARCHIVED,
            entity_id=habit_id,
            data={},
        )
        self.db.append_event(event)

    def create_journal_entry(
        self,
        content: str,
        mood: int | None = None,
        energy: int | None = None,
        gratitude: str | None = None,
        prompt_id: str | None = None,
        tags: list[str] | None = None,
    ) -> str:
        entry = _validated(
            lambda: JournalEntry(
                entry_id=str(uuid.uuid4()),
                created_at=datetime.now(),
                content=content,
                mood=mood,
                energy=energy,
                gratitude=gratitude,
                prompt_id=prompt_id,
                tags=tags or [],
            )
        )
        event = Event(
            event_type=EventType.JOURNAL_ENTRY_CREATED,
            entity_id=entry.entry_id,
            timestamp=entry.created_at,
            data=entry.model_dump(exclude={"entry_id", "created_at"}),
        )
        self.db.append_event(event)
        return entry.entry_id

    def create_goal(
        self,
        outcome: str,
        deadline: datetime | None = None,
    ) -> str:
        if self.db.has_goal(outcome):
            raise DuplicateNameError(f"An active goal '{outcome}' already exists")
        goal = _validated(
            lambda: Goal(
                goal_id=str(uuid.uuid4()),
                outcome=outcome,
                deadline=deadline,
                created_at=datetime.now(),
            )
        )
        event = Event(
            event_type=EventType.GOAL_CREATED,
            entity_id=goal.goal_id,
            timestamp=goal.created_at,
            data={
                "outcome": goal.outcome,
                "deadline": goal.deadline.isoformat() if goal.deadline else None,
            },
        )
        self.db.append_event(event)
        return goal.goal_id

    def add_milestone(
        self,
        goal_id: str,
        description: str,
        target_date: datetime | None = None,
        order: int | None = None,
    ) -> str:
        if order is None:
            existing = self.db.get_milestones(goal_id)
            order = len(existing) + 1

        milestone = _validated(
            lambda: Milestone(
                milestone_id=str(uuid.uuid4()),
                goal_id=goal_id,
                description=description,
                target_date=target_date,
                order=order,
            )
        )
        event = Event(
            event_type=EventType.GOAL_MILESTONE_ADDED,
            entity_id=goal_id,
            data={
                "milestone_id": milestone.milestone_id,
                "description": milestone.description,
                "target_date": milestone.target_date.isoformat() if milestone.target_date else None,
                "order": milestone.order,
            },
        )
        self.db.append_event(event)
        return milestone.milestone_id

    def update_progress(self, goal_id: str, progress: int) -> None:
        with _rejecting_invalid_values(field="progress"):
            progress = TypeAdapter(Progress).validate_python(progress)
        event = Event(
            event_type=EventType.GOAL_PROGRESS_UPDATED,
            entity_id=goal_id,
            data={"progress": progress},
        )
        self.db.append_event(event)

    def complete_goal(self, goal_id: str) -> None:
        event = Event(
            event_type=EventType.GOAL_COMPLETED,
            entity_id=goal_id,
            data={},
        )
        self.db.append_event(event)

    def abandon_goal(self, goal_id: str) -> None:
        event = Event(
            event_type=EventType.GOAL_ABANDONED,
            entity_id=goal_id,
            data={},
        )
        self.db.append_event(event)

    def get_events_since(self, days: int = 7) -> list[Event]:
        since = (datetime.now() - timedelta(days=days)).isoformat()
        return self.db.get_events(since=since)
