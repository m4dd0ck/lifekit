"""Goal tracking models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class GoalStatus(str, Enum):
    """Status of a goal."""

    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"


class Goal(BaseModel):
    """A goal to achieve."""

    goal_id: str
    outcome: str
    deadline: datetime | None = None
    created_at: datetime
    completed_at: datetime | None = None
    status: GoalStatus = GoalStatus.ACTIVE
    progress: int = Field(default=0, ge=0, le=100)


class Milestone(BaseModel):
    """A milestone toward a goal."""

    milestone_id: str
    goal_id: str
    description: str
    target_date: datetime | None = None
    completed_at: datetime | None = None
    order: int
