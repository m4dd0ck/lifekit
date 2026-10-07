"""Event models for Lifekit.

Events are appended to the ``events`` table and applied once to the current-state
tables as they are written. They are a record of what happened, not something the
application replays.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Types of events in the system."""

    # Habit events
    HABIT_CREATED = "habit.created"
    HABIT_LOGGED = "habit.logged"
    HABIT_ARCHIVED = "habit.archived"

    # Journal events
    JOURNAL_ENTRY_CREATED = "journal.entry_created"

    # Goal events
    GOAL_CREATED = "goal.created"
    GOAL_MILESTONE_ADDED = "goal.milestone_added"
    GOAL_PROGRESS_UPDATED = "goal.progress_updated"
    GOAL_COMPLETED = "goal.completed"
    GOAL_ABANDONED = "goal.abandoned"


class Event(BaseModel):
    """Immutable record of one state change, appended to the event log."""

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.now)
    entity_id: str
    data: dict[str, Any]
