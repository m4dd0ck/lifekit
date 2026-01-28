# Lifekit

Local-first personal management CLI combining habit tracking, journaling, and goal setting. Event-sourced storage with DuckDB analytics.

## Install

```bash
uv sync
```

## Usage

```bash
# Habits
lk habit add "Morning run" --why "Energy for the day" --tiny "Put on shoes"
lk habit log "Morning run" --mood 4
lk habit list
lk habit stats "Morning run"

# Journal
lk journal write "Had a productive day" --mood 8 --gratitude "Good weather"
lk journal prompt
lk journal search "productive"

# Goals
lk goal add "Run a 5k" --deadline 2026-04-01
lk goal milestone "Run a 5k" "Run 1 mile without stopping"
lk goal progress "Run a 5k" 40

# Analytics
lk stats
lk stats mood
lk stats habits
lk stats correlations

# AI (requires ANTHROPIC_API_KEY)
lk narrative

# Sealed letters
lk letter "Morning run"
```

Data stored in `~/.lifekit/data.db` by default. Override with `--db-path`.
