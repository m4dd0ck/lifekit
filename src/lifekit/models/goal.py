"""Goal tracking models."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field

Progress = Annotated[int, Field(ge=0, le=100)]
"""Percent complete; reaching 100 marks a goal achieved."""


class GoalStatus(str, Enum):
    """Status of a goal."""

    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"


class Goal(BaseModel):
    """A goal to achieve."""

    goal_id: str
    outcome: str = Field(min_length=1)
    deadline: datetime | None = None
    created_at: datetime
    completed_at: datetime | None = None
    status: GoalStatus = GoalStatus.ACTIVE
    progress: Progress = 0


class Milestone(BaseModel):
    """A milestone toward a goal."""

    milestone_id: str
    goal_id: str
    description: str = Field(min_length=1)
    target_date: datetime | None = None
    completed_at: datetime | None = None
    order: int
