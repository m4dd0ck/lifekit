# Lifekit

Local-first personal management CLI: habit tracking, journaling, goals. Python, Typer, DuckDB.

Every change is written to an append-only `events` table and then applied to plain
current-state tables (`habits`, `journal_entries`, `goals`, ...) in the same DuckDB file.
The event log is the record of what happened; the tables are what the CLI reads. There is
no replay or rebuild step.

## Install

```bash
uv sync
```

## Usage

Every command accepts `--db-path` / `-d` (default `~/.lifekit/data.db`).

```bash
# Habits
lk habit add "Morning run" --why "Energy for the day" --tiny "Put on shoes" --desc "3k loop"
lk habit log "Morning run" --mood 4 --energy 3 --difficulty 2 --quality 4 --context "Rainy"
lk habit list              # --archived / -a to include archived habits
lk habit stats "Morning run"
lk habit archive "Morning run"

# Journal
lk journal write "Had a productive day" --mood 8 --energy 4 --gratitude "Good weather"
lk journal list            # --limit / -n, default 10
lk journal prompt          # --category / -c (gratitude, reflection, shadow, goal)
lk journal search "productive"

# Goals
lk goal add "Run a 5k" --deadline 2026-04-01
lk goal milestone "Run a 5k" "Run 1 mile without stopping"
lk goal progress "Run a 5k" 40
lk goal list               # --status / -s (active, achieved, abandoned)

# Analytics
lk stats                   # overview
lk stats mood --days 14    # default 7
lk stats habits
lk stats correlations

# AI (requires ANTHROPIC_API_KEY; uses claude-sonnet-5-5)
lk narrative --days 7

# Sealed letters
lk letter "Morning run"
```

Habit `--mood`, `--energy`, `--difficulty` and `--quality` take 1-5. Journal `--mood` takes
1-10 and `--energy` 1-5. Goal progress is 0-100; reaching 100 marks the goal achieved.
