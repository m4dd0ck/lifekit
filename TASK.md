# Tasks

Single-repo status, kept by hand. Last reviewed **2026-10-28**.

## Needs the owner

Nothing.

## Queue

From the 2026-10-07 inventory. The six code items (event replay, store validation, row
mapping, goal lookup, narrative window, `get_overview_stats` placement) shipped 2026-10-28.

| Item | Note |
|---|---|
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
