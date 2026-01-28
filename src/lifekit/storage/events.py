"""Event store wrapper for Lifekit."""

import uuid
from datetime import datetime, timedelta

from lifekit.models.events import Event, EventType
from lifekit.storage.database import Database


class EventStore:
    """High-level event store operations."""

    def __init__(self, db: Database):
        self.db = db

    def create_habit(
        self,
        name: str,
        description: str | None = None,
        why: str | None = None,
        tiny_version: str | None = None,
    ) -> str:
        habit_id = str(uuid.uuid4())
        event = Event(
            event_type=EventType.HABIT_CREATED,
            entity_id=habit_id,
            data={
                "name": name,
                "description": description,
                "why": why,
                "tiny_version": tiny_version,
            },
        )
        self.db.append_event(event)
        return habit_id

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
        log_id = str(uuid.uuid4())
        event = Event(
            event_type=EventType.HABIT_LOGGED,
            entity_id=habit_id,
            data={
                "log_id": log_id,
                "completed": completed,
                "context": context,
                "mood_after": mood_after,
                "energy_before": energy_before,
                "difficulty": difficulty,
                "quality": quality,
                "notes": notes,
            },
        )
        self.db.append_event(event)
        return log_id

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
        entry_id = str(uuid.uuid4())
        event = Event(
            event_type=EventType.JOURNAL_ENTRY_CREATED,
            entity_id=entry_id,
            data={
                "content": content,
                "mood": mood,
                "energy": energy,
                "gratitude": gratitude,
                "prompt_id": prompt_id,
                "tags": tags or [],
            },
        )
        self.db.append_event(event)
        return entry_id

    def create_goal(
        self,
        outcome: str,
        deadline: datetime | None = None,
    ) -> str:
        goal_id = str(uuid.uuid4())
        event = Event(
            event_type=EventType.GOAL_CREATED,
            entity_id=goal_id,
            data={
                "outcome": outcome,
                "deadline": deadline.isoformat() if deadline else None,
            },
        )
        self.db.append_event(event)
        return goal_id

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

        milestone_id = str(uuid.uuid4())
        event = Event(
            event_type=EventType.GOAL_MILESTONE_ADDED,
            entity_id=goal_id,
            data={
                "milestone_id": milestone_id,
                "description": description,
                "target_date": target_date.isoformat() if target_date else None,
                "order": order,
            },
        )
        self.db.append_event(event)
        return milestone_id

    def update_progress(self, goal_id: str, progress: int) -> None:
        event = Event(
            event_type=EventType.GOAL_PROGRESS_UPDATED,
            entity_id=goal_id,
            data={"progress": min(100, max(0, progress))},
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
