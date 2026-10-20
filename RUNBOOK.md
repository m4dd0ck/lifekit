# Runbook

Procedures for lifekit. `README.md` describes what each command does; this file says what to
run and in what order.

## On open

```bash
git status --short
git log -3 --oneline
```

## On close

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -q
```

## Run

`uv sync` once, then `uv run lk ...` (`README.md` §Commands). The database is created on first
use. For `lk narrative`, export `ANTHROPIC_API_KEY` first.

## Release

Follows `~/developer/hq/CONVENTIONS.md` §Versioning (portfolio repos):

1. On close checks green.
2. Bump `version` in `pyproject.toml` and `__version__` in `src/lifekit/__init__.py`, then
   `uv lock`, in one `chore: Release vX.Y.Z` commit.
3. Annotated tag `vX.Y.Z`, push with `--tags`, GitHub release with handwritten notes.
4. Commits in real time; never backdated.

## Restore on a new machine

1. Clone the repo and `uv sync`.
2. Copy the old `~/.lifekit/data.db` across if the data is wanted; nothing else backs it up.
3. Export `ANTHROPIC_API_KEY` if the narrative is used.

## Validate

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run pytest -q
python3 ~/.claude/scripts/doc-check.py --repo .
```
