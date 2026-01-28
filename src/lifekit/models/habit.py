"""Habit tracking models."""

from datetime import datetime

from pydantic import BaseModel, Field


class Habit(BaseModel):
    """A habit to track."""

    habit_id: str
    name: str
    description: str | None = None
    why: str | None = None
    tiny_version: str | None = None
    created_at: datetime
    archived_at: datetime | None = None


class HabitLog(BaseModel):
    """A single habit completion record."""

    log_id: str
    habit_id: str
    completed_at: datetime
    completed: bool = True
    context: str | None = None
    mood_after: int | None = Field(default=None, ge=1, le=5)
    energy_before: int | None = Field(default=None, ge=1, le=5)
    difficulty: int | None = Field(default=None, ge=1, le=5)
    quality: int | None = Field(default=None, ge=1, le=5)
    notes: str | None = None
