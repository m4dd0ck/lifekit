# Tasks

Single-repo status, kept by hand. Last reviewed **2026-10-20**.

## Needs the owner

Nothing.

## Queue

From the 2026-10-07 inventory; none started.

| Item | Note |
|---|---|
| Event replay | The event log is append-only but nothing rebuilds the current-state tables from it; the README says so. A `rebuild` would make the event-sourcing claim real |
| Validate at the store boundary | The Pydantic models are used only by tests; `EventStore` accepts any value (`log_habit(mood_after=99)` passes). Build the models in the store, or drop them |
| `Database` row mapping | About 480 lines of `SELECT *` with positional indices; reordering a column breaks the mapping. Name columns or map by cursor description |
| Goal lookup is a partial match | `get_goal_by_outcome` uses `ILIKE '%x%'` and takes the first row, so an ambiguous name picks an arbitrary goal; `get_habit_by_name` is exact and allows duplicate names |
| Narrative input window | The CLI fetches `days * 2` logs and `days * 3` entries instead of filtering by date, so "this week" can include older data |
| `get_overview_stats` placement | Lives in `correlations.py` and is not exported from `analytics`; the CLI imports it directly |
| PRP file references | `PRPs/lifekit-mvp.md` names sibling-repo paths from the machine it was written on; it is the historical build spec, leave or annotate |

## Parked: future features

From the original TODO list (2026-02-03); ideas, not commitments. The design behind them is in
`BRAINSTORM.md`.

- [ ] Habit rot and compost: habits decay after N days without logs, decayed habits suggest new
      ones from old patterns, a visual indicator of habit health
- [ ] Predictive breaks: detect declining completion plus mood before burnout, suggest rest days,
      "you usually skip Thursdays" insights
- [ ] External factors: weather, calendar density, sleep data, correlated with habit success
- [ ] Keystone habit mapping: which habits unlock others, a dependency graph
- [ ] Time-capsule letters: locked until a date, notification when they unlock, unreadable and
      uneditable before then
- [ ] Social: habit dueling, opt-in shared accountability, anonymous streak comparison
- [ ] Web UI (FastAPI plus SolidJS or React)
- [ ] Data export (JSON, CSV)
- [ ] Sync across devices (optional)
- [ ] Richer AI coaching prompts
