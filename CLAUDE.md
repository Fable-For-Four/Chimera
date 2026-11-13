# Chimera: rules for Claude

Read `PLAN.md` and `TECH-STACK.md` before any task. `PLAN.md` section 8 is the task board with fixed time slots. Sections 4 and 14 are contracts.

## What this is
A log investigation tool for HackInnovision 2026, Track C. The Python engine reads simulated logs and writes JSON. A FastAPI server serves that JSON to signed-in users. A Next.js app is the only frontend.

```
generator -> data/ -> engine -> out/*.json -> FastAPI (api/, :8000, /api only) -> Next.js (web/, :3000)
```

## Time comes first
Submit at 09:30. Freeze at 08:30. Every task has a fixed slot in `PLAN.md` section 8. If a task runs over its slot, cut scope inside the task, then use the cut order. Never stretch the clock.

## Who owns what
Each task in `PLAN.md` section 8 names the files it owns. **Touch only those files.** If you need a change in someone else's file, stop and say so.

| Lane | Area |
|---|---|
| A | `generator/`, `data/`, `engine/` (except `intake.py`, `challenge.py`, `truth.py`) |
| B | `run.sh`, `requirements.txt`, `.gitignore`, `.env.example`, `api/`, `engine/challenge.py`, `engine/truth.py` |
| C | `web/` shell and lib (`Shell.tsx`, `lib/`, `globals.css`, `layout.tsx`), Start, Overview, graph, stress |
| D | `tests/fixtures/`, `tests/test_contract.py`, `engine/intake.py`, `web/` login, verify, logs, report, admin, `README.md` |

Shared-file rules: `api/main.py` goes B4, then B5, then B6. `engine/run.py` is Lane A only. `Shell.tsx`, `lib/` and `globals.css` belong to C1.

## FAILSAFE: locked parts
When a team member says a part works, add it here. **Do not edit, refactor, reformat or "improve" anything listed below.** If a task seems to need a change to a locked part, stop and ask first.

<!-- One line per item: path or function, who confirmed, time -->
- (nothing locked yet)

## Contracts
- JSON shapes: `PLAN.md` section 4. The reference is `tests/fixtures/*.sample.json`, checked by `tests/test_contract.py`.
- API routes, roles and status codes: `PLAN.md` section 14.
- Changing either needs the team to agree and the sample files updated first.

## Stack (full list in TECH-STACK.md)
- Python 3.11 syntax (the main laptop runs 3.14). `networkx`, FastAPI, `sqlite3`, `bcrypt`, `PyJWT`, `resend`.
- Next.js App Router with TypeScript. Every screen is a client component and fetches `/api/*` in the browser.
- **Not allowed:** Tailwind, component libraries, state libraries, data-fetching libraries, chart or graph libraries, ORMs, pandas, NumPy, ML. No new dependency without the team agreeing.

## Code style
- Plain and readable. Small functions with clear names.
- Short comments only where the *why* is not obvious. One or two lines, never an essay.
- No abstraction for one use: no base classes, factories, or config for fixed values.
- Engine stages take plain data and return plain data, so each can be tested alone. Same input, same output.
- UI: every number comes from the API. Only labels are typed in.

## Security (from PLAN.md section 14)
- Secrets only in `.env`, which is never committed. `.env.example` has the names with empty values.
- The app refuses to start without `JWT_SECRET` (32 characters or more).
- Passwords are hashed with `bcrypt` at cost 12. Never log a password, hash or token, and never return `password_hash`.
- The session JWT lives only in the `httpOnly` `session` cookie. The UI never reads or stores it.
- SQL always uses `?` parameters, never string building.
- Log text is untrusted. Render it as plain JSX text. Never use `dangerouslySetInnerHTML`.
- The only allowed log of a secret: the verification link is printed when `RESEND_API_KEY` is unset (PLAN 14.12).

## Workflow
- One task per branch, small PRs, never push to `main`.
- A task is done when its "Done when" checks pass and `pytest` is green. UI tasks also pass `npm run lint` and `npm run build`.
- Ask before changing anything outside the task.
- Commands: `/feature` (tests first), `/fix` (debug), `/deploy` (pre-submission checks).
- Subagents in `.claude/agents/` (reviewer, tester, debugger, deployment, uiux) run on Sonnet 5.5 at medium effort.

## Run
```
./run.sh                              # everything, app at http://localhost:3000 (Windows: Git Bash)
./run.sh demo                         # same, with the production UI build for the presentation
python -m generator --seed 7          # writes data/
python -m engine.run                  # writes out/ and prints the chain
python -m api.seed                    # creates the three demo accounts
uvicorn api.main:app --reload --port 8000
pytest
cd web && npm run lint && npm run build
```
