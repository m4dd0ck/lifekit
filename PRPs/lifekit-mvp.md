name: "Lifekit MVP - Personal Management System"
description: |

## Purpose
Build a local-first personal management app combining habit tracking, journaling, and goal setting with intelligent interconnections between data types. The system emphasizes psychological health (no debt/punishment mechanics), data-driven insights, and unique features like habit composting and future-self letters.

## Core Principles
1. **Local-first**: All data stored locally in SQLite, privacy by default
2. **Event-sourced**: Every action is an immutable event for time-travel and analytics
3. **No punishment**: Missed habits just disappear - no debt, no guilt mechanics
4. **Interconnected data**: Journal mood predicts habit success, habits link to goals
5. **Research-backed**: Track what science says matters, not vanity metrics

---

## Goal
Build a working CLI + API for Lifekit that allows users to:
1. Track habits with context and mood
2. Write journal entries with mood, gratitude, and prompts
3. Set goals with milestones
4. See analytics: streaks, mood trends, habit-mood correlations, chronotype patterns
5. Receive AI-generated weekly narratives summarizing their data

## Why
- **Portfolio value**: Demonstrates event sourcing, DuckDB analytics, Claude API integration
- **Personal utility**: Actually useful tool for the developer
- **Unique angle**: Interconnected personal data (not just another habit tracker)

## What

### User-Visible Behavior

**CLI Commands:**
```bash
# Habits
lk habit add "Morning run" --why "Energy for the day" --tiny "Put on shoes"
lk habit log "Morning run" --mood 4 --difficulty 2 --context "Before work"
lk habit list
lk habit stats "Morning run"

# Journal
lk journal write                    # Opens editor or prompts
lk journal write --mood 7 --gratitude "Good coffee, sunny day"
lk journal prompt                   # Get a random prompt
lk journal search "anxiety"

# Goals
lk goal add "Run a 5k" --deadline 2026-04-01
lk goal milestone "Run a 5k" "Run 1 mile without stopping"
lk goal progress "Run a 5k" 40

# Analytics
lk stats                            # Overview dashboard
lk stats habits                     # Habit-specific stats
lk stats mood                       # Mood trends
lk stats correlations               # Habit-mood correlations

# AI Features
lk narrative                        # Generate weekly narrative
lk letter "Morning run"             # Read sealed letter for habit
```

### Success Criteria
- [ ] Can CRUD habits, journal entries, goals, milestones
- [ ] All actions stored as events (event sourcing)
- [ ] Streaks calculated correctly (current, longest, completion rate)
- [ ] Mood trends visible (7-day, 30-day)
- [ ] At least one correlation metric (mood vs habit completion)
- [ ] Weekly narrative generation via Claude API
- [ ] All tests pass, no linting errors, types check

---

## All Needed Context

### Documentation & References
```yaml
- url: https://docs.pydantic.dev/latest/
  why: Data models, validation, Field constraints

- url: https://typer.tiangolo.com/
  why: CLI framework - commands, arguments, options

- url: https://rich.readthedocs.io/
  why: Terminal output - tables, panels, progress bars

- url: https://duckdb.org/docs/api/python/overview
  why: Analytics queries, time-series aggregations

- url: https://docs.anthropic.com/en/docs/build-with-claude/text-generation
  why: Claude API for narrative generation

- file: /home/noah/portfolio/metricforge/pyproject.toml
  why: Project structure pattern to follow

- file: /home/noah/portfolio/resolve-ai/src/resolve_ai/models.py
  why: Pydantic model patterns (enums, validators, Field)

- file: /home/noah/portfolio/resolve-ai/src/resolve_ai/storage/database.py
  why: DuckDB database class pattern

- file: /home/noah/portfolio/metricforge/src/metricforge/cli/main.py
  why: Typer CLI pattern with Rich output

- file: /home/noah/portfolio/metricforge/tests/conftest.py
  why: Pytest fixture patterns
```

### Current Codebase tree
```bash
/home/noah/developer/lifekit/
├── BRAINSTORM.md          # Research and ideas (read this!)
└── PRPs/
    └── lifekit-mvp.md     # This file
```

### Desired Codebase tree
```bash
/home/noah/developer/lifekit/
├── BRAINSTORM.md
├── PRPs/
│   └── lifekit-mvp.md
├── pyproject.toml              # uv project config
├── README.md                   # Brief description
├── src/
│   └── lifekit/
│       ├── __init__.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── habit.py        # Habit, HabitLog models
│       │   ├── journal.py      # JournalEntry, Prompt models
│       │   ├── goal.py         # Goal, Milestone models
│       │   └── events.py       # Event sourcing base types
│       ├── storage/
│       │   ├── __init__.py
│       │   ├── database.py     # DuckDB storage layer
│       │   └── events.py       # Event store implementation
│       ├── analytics/
│       │   ├── __init__.py
│       │   ├── streaks.py      # Streak calculations
│       │   ├── trends.py       # Mood/habit trends
│       │   └── correlations.py # Cross-data correlations
│       ├── ai/
│       │   ├── __init__.py
│       │   └── narrative.py    # Claude API for weekly narrative
│       └── cli/
│           ├── __init__.py
│           └── main.py         # Typer CLI app
└── tests/
    ├── __init__.py
    ├── conftest.py             # Shared fixtures
    ├── test_models.py
    ├── test_storage.py
    ├── test_analytics.py
    └── test_cli.py
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: Pydantic v2 syntax (not v1)
from pydantic import BaseModel, Field, field_validator  # NOT validator

# CRITICAL: DuckDB datetime handling
# Use ISO strings or Python datetime, not pandas Timestamp
created_at: datetime = Field(default_factory=datetime.now)

# CRITICAL: Typer callback for app-level options
@app.callback()
def main(db_path: str = typer.Option("~/.lifekit/data.db")):
    ...

# CRITICAL: Rich console for all output (not print)
from rich.console import Console
console = Console()
console.print("[green]Success![/green]")

# CRITICAL: Event sourcing - events are immutable
# Never update events, only append new ones
# Current state = replay all events

# CRITICAL: Claude API
from anthropic import Anthropic
client = Anthropic()  # Uses ANTHROPIC_API_KEY env var
```

---

## Implementation Blueprint

### Data Models

```python
# src/lifekit/models/events.py
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field
import uuid

class EventType(str, Enum):
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
    """Immutable event - source of truth for all state changes."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=datetime.now)
    entity_id: str  # ID of the habit/journal/goal this event affects
    data: dict[str, Any]  # Event-specific payload


# src/lifekit/models/habit.py
from datetime import datetime
from pydantic import BaseModel, Field

class Habit(BaseModel):
    """A habit to track."""
    habit_id: str
    name: str
    description: str | None = None
    why: str | None = None  # Sealed letter to future self
    tiny_version: str | None = None  # BJ Fogg's tiny habit
    created_at: datetime
    archived_at: datetime | None = None

class HabitLog(BaseModel):
    """A single habit completion/attempt."""
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


# src/lifekit/models/journal.py
class JournalEntry(BaseModel):
    """A journal entry."""
    entry_id: str
    created_at: datetime
    content: str
    mood: int | None = Field(default=None, ge=1, le=10)
    energy: int | None = Field(default=None, ge=1, le=5)
    gratitude: str | None = None  # Comma-separated or free text
    prompt_id: str | None = None
    tags: list[str] = Field(default_factory=list)

class Prompt(BaseModel):
    """A journaling prompt."""
    prompt_id: str
    text: str
    category: str  # gratitude, reflection, shadow, goal


# src/lifekit/models/goal.py
from enum import Enum

class GoalStatus(str, Enum):
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"

class Goal(BaseModel):
    """A goal to achieve."""
    goal_id: str
    outcome: str  # SMART format description
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
```

### Task List

```yaml
Task 1 - Project Setup:
  CREATE pyproject.toml:
    - Mirror pattern from /home/noah/portfolio/metricforge/pyproject.toml
    - Dependencies: duckdb, pydantic>=2.0, typer, rich, anthropic, structlog
    - Dev deps: pytest, pytest-cov, ruff, mypy
    - CLI entrypoint: lk = "lifekit.cli.main:app"

Task 2 - Core Models:
  CREATE src/lifekit/models/__init__.py
  CREATE src/lifekit/models/events.py:
    - EventType enum with all event types
    - Event base model with id, type, timestamp, entity_id, data
  CREATE src/lifekit/models/habit.py:
    - Habit model
    - HabitLog model with mood/energy/difficulty fields
  CREATE src/lifekit/models/journal.py:
    - JournalEntry model
    - Prompt model
  CREATE src/lifekit/models/goal.py:
    - Goal model with GoalStatus enum
    - Milestone model

Task 3 - Storage Layer:
  CREATE src/lifekit/storage/__init__.py
  CREATE src/lifekit/storage/database.py:
    - MIRROR pattern from /home/noah/portfolio/resolve-ai/src/resolve_ai/storage/database.py
    - Database class with DuckDB connection
    - Schema: events table (event source), plus view tables for current state
    - Methods: append_event(), get_events(), rebuild_state()
  CREATE src/lifekit/storage/events.py:
    - EventStore class wrapping Database
    - Methods to query events by type, entity, time range
    - State reconstruction from events

Task 4 - Analytics:
  CREATE src/lifekit/analytics/__init__.py
  CREATE src/lifekit/analytics/streaks.py:
    - calculate_streak(habit_id) -> current, longest, completion_rate
    - Uses HabitLog events to compute
  CREATE src/lifekit/analytics/trends.py:
    - mood_trend(days=7) -> list of (date, avg_mood)
    - habit_completion_trend(habit_id, days=30) -> list of (date, completed)
  CREATE src/lifekit/analytics/correlations.py:
    - mood_habit_correlation(habit_id) -> correlation coefficient
    - chronotype_analysis(habit_id) -> best time of day

Task 5 - AI Integration:
  CREATE src/lifekit/ai/__init__.py
  CREATE src/lifekit/ai/narrative.py:
    - generate_weekly_narrative(events, journal_entries) -> str
    - Uses Claude API with structured prompt
    - Summarizes habits completed, mood trends, insights

Task 6 - CLI:
  CREATE src/lifekit/cli/__init__.py
  CREATE src/lifekit/cli/main.py:
    - MIRROR pattern from /home/noah/portfolio/metricforge/src/metricforge/cli/main.py
    - Typer app with subcommands: habit, journal, goal, stats, narrative
    - Rich output for tables and formatting
    - App callback for global --db-path option

Task 7 - Tests:
  CREATE tests/__init__.py
  CREATE tests/conftest.py:
    - MIRROR pattern from /home/noah/portfolio/metricforge/tests/conftest.py
    - Fixtures: tmp_db, sample_events, populated_store
  CREATE tests/test_models.py:
    - Test model validation, enums, field constraints
  CREATE tests/test_storage.py:
    - Test event append, retrieval, state reconstruction
  CREATE tests/test_analytics.py:
    - Test streak calculation, mood trends, correlations
  CREATE tests/test_cli.py:
    - Test CLI commands with CliRunner

Task 8 - Final Polish:
  CREATE README.md:
    - Brief description (2-3 sentences)
    - Installation: uv sync
    - Usage: basic CLI examples
    - No marketing language
  CREATE .github/workflows/ci.yml:
    - MIRROR pattern from portfolio projects
    - uv sync --dev, ruff check, mypy, pytest
  RUN validation gates
```

### Pseudocode for Key Components

```python
# src/lifekit/storage/database.py
SCHEMA_SQL = """
-- Event store (source of truth)
CREATE TABLE IF NOT EXISTS events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    entity_id TEXT NOT NULL,
    data JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_entity ON events(entity_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);

-- Materialized views for current state (rebuilt from events)
CREATE TABLE IF NOT EXISTS habits (
    habit_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    why TEXT,
    tiny_version TEXT,
    created_at TIMESTAMP NOT NULL,
    archived_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS habit_logs (
    log_id TEXT PRIMARY KEY,
    habit_id TEXT NOT NULL,
    completed_at TIMESTAMP NOT NULL,
    completed BOOLEAN DEFAULT TRUE,
    context TEXT,
    mood_after INTEGER,
    energy_before INTEGER,
    difficulty INTEGER,
    quality INTEGER,
    notes TEXT
);

-- Similar tables for journal_entries, goals, milestones
"""

class Database:
    def __init__(self, db_path: Path | str = ":memory:"):
        self.db_path = db_path
        self._conn = None

    @property
    def conn(self):
        if self._conn is None:
            self._conn = duckdb.connect(str(self.db_path))
            self._init_schema()
        return self._conn

    def append_event(self, event: Event) -> None:
        """Append event and update materialized view."""
        # Insert into events table
        self.conn.execute(
            "INSERT INTO events VALUES (?, ?, ?, ?, ?)",
            [event.event_id, event.event_type.value, event.timestamp,
             event.entity_id, json.dumps(event.data)]
        )
        # Update materialized view based on event type
        self._apply_event(event)

    def _apply_event(self, event: Event) -> None:
        """Apply event to materialized views."""
        if event.event_type == EventType.HABIT_CREATED:
            self.conn.execute(
                "INSERT INTO habits VALUES (?, ?, ?, ?, ?, ?, NULL)",
                [event.entity_id, event.data["name"], ...]
            )
        elif event.event_type == EventType.HABIT_LOGGED:
            self.conn.execute(
                "INSERT INTO habit_logs VALUES (...)",
                [...]
            )
        # ... handle other event types


# src/lifekit/analytics/streaks.py
def calculate_streak(db: Database, habit_id: str) -> dict:
    """Calculate streak stats for a habit."""
    result = db.conn.execute("""
        WITH daily_completion AS (
            SELECT
                DATE(completed_at) as day,
                MAX(completed::INT) as completed
            FROM habit_logs
            WHERE habit_id = ?
            GROUP BY DATE(completed_at)
        ),
        streaks AS (
            SELECT
                day,
                completed,
                day - INTERVAL (ROW_NUMBER() OVER (ORDER BY day)) DAY as grp
            FROM daily_completion
            WHERE completed = 1
        )
        SELECT
            COUNT(*) as streak_length,
            MIN(day) as start_date,
            MAX(day) as end_date
        FROM streaks
        GROUP BY grp
        ORDER BY end_date DESC
    """, [habit_id]).fetchall()

    # Calculate current streak, longest streak, completion rate
    ...


# src/lifekit/ai/narrative.py
from anthropic import Anthropic

def generate_weekly_narrative(
    habits: list[dict],
    journal_entries: list[dict],
    mood_trend: list[tuple],
) -> str:
    """Generate AI narrative of the week."""
    client = Anthropic()

    prompt = f"""You are a supportive personal coach reviewing someone's week.

Here's their data:

HABITS COMPLETED:
{format_habits(habits)}

JOURNAL EXCERPTS:
{format_journal(journal_entries)}

MOOD TREND (1-10):
{format_mood(mood_trend)}

Write a 2-3 paragraph narrative summary of their week. Be:
- Warm but not saccharine
- Observational, noting patterns
- Forward-looking with gentle suggestions
- Never judgmental about missed habits

Do NOT use phrases like "great job" or "you're doing amazing". Just observe and reflect."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text
```

### Integration Points

```yaml
DATABASE:
  - Location: ~/.lifekit/data.db (default, configurable)
  - Created on first run
  - Schema applied automatically

CONFIG:
  - ANTHROPIC_API_KEY env var for AI features
  - --db-path CLI option for custom location

CLI:
  - Entrypoint: lk (defined in pyproject.toml)
  - Subcommands: habit, journal, goal, stats, narrative, letter
```

---

## Validation Loop

### Level 1: Syntax & Style
```bash
cd /home/noah/developer/lifekit
uv run ruff check src/ tests/ --fix
uv run ruff format src/ tests/
uv run mypy src/

# Expected: No errors
```

### Level 2: Unit Tests
```bash
uv run pytest tests/ -v

# Expected: All tests pass
```

### Level 3: Integration Test
```bash
# Initialize and test CLI
uv run lk habit add "Test habit" --why "Testing"
uv run lk habit list
uv run lk habit log "Test habit" --mood 4
uv run lk stats

# Expected: Commands work, data persists
```

---

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] CLI commands work: habit add/log/list, journal write, goal add, stats
- [ ] Events stored correctly in database
- [ ] Analytics calculations correct (streaks, trends)
- [ ] AI narrative generates (with valid API key)

---

## Anti-Patterns to Avoid
- ❌ Don't add debt/punishment mechanics - user explicitly rejected this
- ❌ Don't use Pydantic v1 syntax (validator → field_validator)
- ❌ Don't use print() - use Rich console
- ❌ Don't mutate events - append only
- ❌ Don't over-engineer MVP - start simple, validate, enhance
- ❌ Don't add features not in spec (no web UI, no sync, no mobile)

---

## Confidence Score: 8/10

**Why 8:**
- Clear patterns from existing portfolio projects to follow
- Well-defined data models from brainstorm research
- Event sourcing adds complexity but is well-documented
- Claude API integration is straightforward
- DuckDB analytics queries may need iteration

**Risks:**
- Streak calculation SQL may need debugging
- Event replay for state reconstruction needs careful testing
- AI prompt tuning may need iteration
