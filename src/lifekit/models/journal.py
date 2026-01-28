"""Journal entry models."""

from datetime import datetime

from pydantic import BaseModel, Field


class JournalEntry(BaseModel):
    """A journal entry."""

    entry_id: str
    created_at: datetime
    content: str
    mood: int | None = Field(default=None, ge=1, le=10)
    energy: int | None = Field(default=None, ge=1, le=5)
    gratitude: str | None = None
    prompt_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class Prompt(BaseModel):
    """A journaling prompt."""

    prompt_id: str
    text: str
    category: str
