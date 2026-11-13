# AGENTS.md: rules for any AI coding agent (Codex, Claude, others)

This file mirrors `CLAUDE.md` for tools that read `AGENTS.md`. If the two disagree, `CLAUDE.md` wins.

## Before you start
1. Read `PLAN.md` and `TECH-STACK.md`. `PLAN.md` section 8 is the task board with fixed time slots. Sections 4 (JSON) and 14 (routes, roles) are contracts.
2. Read the **locked parts** list in `CLAUDE.md`. Never change a locked part. Ask first.
3. Touch only the files your task owns in `PLAN.md` section 8.

## Layout
- `generator/`, `data/`, `engine/`: Python engine (Lane A, plus `intake.py` for D and `challenge.py`, `truth.py` for B)
- `api/`: FastAPI, the API only, under `/api` (Lane B)
- `web/`: Next.js, the only frontend (Lanes C and D)
- `tests/`: `pytest`, with fixtures in `tests/fixtures/`
- `out/`, `app.db`, `.env`: never committed

## Subagents
Five Claude Code subagents live in `.claude/agents/`. All run on **Sonnet 5.5 (`claude-sonnet-5-5`) at medium effort**.

| Agent | Job | Edits files |
|---|---|---|
| reviewer | Reviews a diff against contracts, ownership, locked parts, secrets, simplicity | No |
| tester | Turns "Done when" lines into `pytest` tests and runs them | `tests/` only |
| debugger | Finds the root cause and makes the smallest fix, with a test | Yes, not locked parts |
| deployment | `.gitignore`, `.env`, secrets in code and history, cookie and JWT setup, clean-clone run | No |
| uiux | Layout at 1920x1080 and 2560x1440, no hardcoded numbers, readability | No |

Commands: `/feature` uses tester, `/fix` uses debugger, `/deploy` uses deployment and uiux.

## Reviewing a diff (Codex's main job here)
Check, in this order:
1. Does it break a section 4 JSON shape, a section 14 route or a locked part?
2. Does it touch files outside the task's ownership?
3. Is it correct? Edge cases: missing fields, late events, empty chain, "No chain found", 401 and 403.
4. Do the tests pass? Run `pytest`, plus `npm run lint` and `npm run build` in `web/` for UI changes.
5. Security: no secrets, SQL with `?` parameters, no `password_hash` in responses, no `dangerouslySetInnerHTML`, token only in the `httpOnly` cookie.
6. Is it simpler than it could be? Flag needless abstractions and libraries not in `TECH-STACK.md`.

Report each finding as `file:line: problem, suggested fix`. Do not rewrite code unless asked.

## Style
Plain Python 3.11 and TypeScript. Small functions. Short comments only where the *why* is not obvious. Deterministic engine output. Every UI number comes from the API.
