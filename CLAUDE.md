# lifekit: agent rules

Instructions for coding agents working in this repo; a human reader wants `README.md`. Read
`README.md` for how it works, `RUNBOOK.md` for procedures, `TASK.md` for what is open. The
owner's global agent rules apply on top of these.

- Public repo: no personal data. Examples and tests use invented habits and journal text, never
  the owner's; no API keys anywhere.
- Real-time commits only, never backdated; no AI attribution lines.
- Release steps: `RUNBOOK.md` §Release.
- Traps: `-d` belongs to `--db-path` alone; giving another option that short flag makes Click
  warn and one of them silently win. The narrative's token budget must leave room for a thinking
  block. Tests write to a temporary DuckDB file, never to `~/.lifekit`.
