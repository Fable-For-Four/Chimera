# Chimera: plan per person

This is `PLAN.md` section 8, split by person. The specs live in `PLAN.md` and `TECH-STACK.md`. If this file and `PLAN.md` disagree, `PLAN.md` wins.

**Clock:** build 03:00 to 08:30, break 04:00 to 04:30, freeze 08:30, submit 09:30. Slots are fixed. If you run over, cut scope inside your task. Don't move the clock.

**Everyone:**
- Start each task with `/feature <task ID>`, which writes the tests first. Use `/fix` for bugs. Run `/deploy` at 08:00.
- One branch per task, a small PR, and a review by the reviewer agent or Codex before merging. Never push to `main`.
- Touch only the files your task owns. Need a change in someone else's file? Message them.
- When something works, add it to the locked list in `CLAUDE.md`. Nobody touches it after that.
- First 10 minutes: clone, run `git pull`, copy `.env.example` to `.env`, and set a `JWT_SECRET` of 32 or more characters.

| Person | Lane | Area |
|---|---|---|
| 1 | A | Data generator and detection engine (Python) |
| 2 | B | Backend: scaffold, FastAPI, SQLite database, sign-in, email, two engine stages |
| 3 | C | Frontend core: Next.js app, shell, Start, Overview, graph, stress |
| 4 | D | Contract files, intake, frontend sign-in and secondary screens, README |

---

## Person 1: data and engine (Lane A)

Owns: `generator/`, `data/`, `engine/` except `intake.py`, `challenge.py` and `truth.py`. Lane A only edits `engine/run.py`.

| Slot | Task | Build | Done when |
|---|---|---|---|
| 03:00 to 04:00 | **A1** Generator | `python -m generator --seed 7` writes `events.jsonl`, `truth.json`, `access.json`, `history.json`, `layout.json`. Normal noise, 25 lone oddities, the 12 planted attack events with every field from PLAN §5, and 212 late logs (only the step 3 `LOGON` from the attack). Node positions come from `docs/mock.html`. | Same seed gives identical files. 5,100 to 5,200 events. 12 IDs in truth. The `LOGON` sits after the `TICKET_REQ` in the file. No attack entity is in more than 5% of events. |
| 04:30 to 05:20 | **A2** Sort, Profile, Score | `sort.py`, `profile.py`, `score.py`: the 12 rules and weights from §6.4, `1-(1-w)…` combining, ×0.9 for late events. | Every planted event except the `DNS_QUERY` scores 0.30 or more. All noise stays under 0.15. Each score lists its reasons. |
| 05:20 to 06:35 | **A3** Link and Verdict | `link.py` (networkx components, hubs, 45-minute window, stages, inferred steps, confidence), `verdict.py` (label, entry point, blast radius, graph, actions). | 5 steps in order, 11 events, no `DNS_QUERY` and no oddities. Removing the attack gives no chain. **Checkpoint 06:45.** |
| 06:35 to 06:55 | **A5** Run | `run.py`: intake, pipeline and stage timings, writes `out/case.json`, prints the chain. Stages not merged yet stay empty. | `python -m engine.run` passes `tests/test_contract.py`. Tell Person 2, who switches the API to real files. |
| 06:55 to 07:25 | **A4** Report | `report.py`: one sentence per step with citations, limits, three questions, and a check that drops any bad citation. Wire in Person 2's `challenge.py` and `truth.py` when they merge. | Every cited ID exists. |
| 07:25 to 08:05 | **A6** Stress | `stress.py`: levels 0 to 40, `random.Random(seed + level)`, writes `out/stress/NN.json`. | Level 0 equals `case.json`. Confidence at 40 is lower than at 0. The whole run takes under 20 seconds. |
| 08:05 to 08:30 | Fixes | Integration bugs only. | |

If Link fails at 06:45, simplify the scenario until it works. Nothing else matters more.

---

## Person 2: backend, API and database (Lane B)

Owns: `run.sh`, `requirements.txt`, `.gitignore`, `.gitattributes`, `.env.example`, `api/`, `engine/challenge.py`, `engine/truth.py`, `tests/test_auth.py`, `tests/test_case_api.py`. `api/main.py` is yours alone, built in the order B4, B5, B6.

**Database** (SQLite file `app.db` in the repo root, plain `sqlite3`, `?` parameters only, never committed):

| Table | Columns |
|---|---|
| `users` | `id`, `email` (unique, lowercased), `name`, `password_hash`, `role` (default `viewer`), `email_verified_at`, `created_at` |
| `email_tokens` | `id`, `user_id`, `token_hash` (unique, SHA-256), `expires_at`, `used_at` |
| `approvals` | `id`, `action_id` (unique), `user_id`, `approved_at` |

| Slot | Task | Build | Done when |
|---|---|---|---|
| 03:00 to 03:20 | **B1** Scaffold | `run.sh`, `requirements.txt`, `.gitignore`, `.gitattributes` and `.env.example` already exist. Check them, add a `README.md` skeleton, merge. | Teammates can clone and run `pip install -r requirements.txt`. |
| 03:20 to 04:00, 04:30 to 05:05 | **B4** Accounts | `db.py` (the three tables), `auth.py` (bcrypt cost 12, JWT HS256 with only `sub` and `exp`, the `session` cookie, current user from the database), `permissions.py` (the role map and `require()`), `seed.py` (3 demo accounts), `main.py` (signup, login, logout, me). The app refuses to start without a 32-character `JWT_SECRET`. | PLAN §14.10 tests 1 to 11 pass. Seeded analyst can sign in. **Checkpoint 05:30.** |
| 05:05 to 05:50 | **B5** Case routes | `GET /api/intake`, `/api/case`, `/api/case/stress/{level}`, `POST /api/case/run`, approve, `GET /api/approvals`, users, role change. Serve the sample files until Person 1's A5 merges. | Tests 19 and 20 pass. Viewer gets 403 on run and approve. |
| 05:50 to 06:50 | **B6** Email verification | `email.py` with `send_verification_email()` via Resend in `BackgroundTasks`. Without a key, print the link to the log. Token: `secrets.token_urlsafe(32)`, store only the hash, valid 30 minutes, works once. | Tests 12 to 18 pass. No test sends real email. |
| 06:50 to 07:30 | **B7** Challenge and truth | `challenge.py` (two innocent explanations whose shares add to 100) and `truth.py` (found, missed, false links, recall, precision). Build against `case.sample.json`. Person 1 wires them into `run.py`. | Shares add to 100. Truth numbers are real, not tuned. |
| 07:30 to 08:30 | End to end | Run button → engine → API → UI. Fix what breaks. | A signed-in analyst presses Run and every screen updates. |

Cut first if behind: B6 (treat everyone as verified), then sign-up (seeded users only).

---

## Person 3: frontend core (Lane C)

Owns: `web/package.json`, `next.config.ts`, `app/layout.tsx`, `app/globals.css`, `components/Shell.tsx`, `lib/` (`api.ts`, `types.ts`, `state.tsx`), `app/page.tsx`, `components/Start.tsx`, `components/Overview.tsx`, `app/graph/`, `components/EvidenceDrawer.tsx`, `app/stress/`. Others ask you before changing `Shell`, `lib/` or `globals.css`.

Rules: every screen is a client component. Use `fetch` to `/api/*` only. No Tailwind, no UI, chart or state libraries. All graphics are SVG in JSX. Log text is plain text, never `dangerouslySetInnerHTML`. Every number comes from the API.

| Slot | Task | Build | Done when |
|---|---|---|---|
| 03:00 to 03:10 | Install | `npx create-next-app@latest web` (TypeScript, ESLint, App Router, no Tailwind), then `npm install`, **while the Wi-Fi works**. Commit `package-lock.json`. | `npm run dev` serves a page. |
| 03:10 to 04:00, 04:30 to 05:00 | **C1** App and shell | The mock's CSS goes into `globals.css`. Fonts with `next/font/google`. A `/api` rewrite to port 8000. `lib/api.ts` (401 goes to `/login`, 403 shows its message, sample files from `web/public/samples/` until the API is ready), `lib/types.ts` (PLAN §4.3 and 4.4), `lib/state.tsx` (user, case, step, stress level). `Shell.tsx` handles the sidebar, top bar, and sign-in / check-your-email / app switch. | `npm run build` is clean. The shell renders with sample data. Person 4 can start. |
| 05:00 to 06:00 | **C2** Start, Run, Overview | Start: counts, volume bars, 4 alert rules, first 8 log lines, Run button (disabled for viewers). Run: the six stages tick off. Overview: verdict, ring, headline, entry point, blast radius, data at risk, weakest step, chain, explanations, two empty slots for Person 4's panels. | It renders from samples through the API. "No chain found" works. **Checkpoint 06:00.** |
| 06:00 to 07:15 | **C3** Graph and evidence | SVG `viewBox="0 0 860 480"`, nodes at their given positions, red numbered path, inferred steps dashed, a Replay button, a timeline in the volume bars. The evidence drawer has exhibits A, B, C with late and deleted tags, plus Previous and Next. | Clicking a step opens its evidence. **Checkpoint 07:15:** real engine data drives Start, Overview and the graph. |
| 07:15 to 08:00 | **C4** Stress | A slider from 0 to 40 in steps of 5, a chart of the three shares, a Proven/Thin/Guess table, and the truth score. The chosen level applies to every screen. | All 9 levels load. |
| 08:00 to 08:30 | Layout | Run `/deploy`, which uses the uiux agent at 1920x1080 and 2560x1440. Fix what it finds. | Overview and the graph fit one screen with no horizontal scroll. |

---

## Person 4: contract, intake, frontend screens, docs (Lane D)

Owns: `tests/fixtures/*.sample.json`, `tests/test_contract.py`, `engine/intake.py`, `app/login/`, `app/verify/`, `app/logs/`, `app/report/`, `components/ApprovalsPanel.tsx`, `components/QuestionsPanel.tsx`, `app/admin/`, `README.md` (after B1). `docs/mock.html` must be committed by whoever has it, **before 03:00**.

| Slot | Task | Build | Done when |
|---|---|---|---|
| 03:00 to 03:30 | **B2** Sample files and shape check | Write `case.sample.json` and `intake.sample.json` by hand from the mock's numbers, plus `test_contract.py`, which checks any case or stress file against the shape. | Merged by 03:30. Persons 2 and 3 build against these files. |
| 03:30 to 04:00 | Review | Review Person 2's B1 and Person 3's C1 PRs. Check the ATT&CK IDs on attack.mitre.org. | |
| 04:30 to 05:00 | **B3** Intake | `engine/intake.py`: summary, volume per 5 minutes, the 4 old alert rules with ratios, the first 8 events. | All 4 rules have `fired` false and `alerts_fired` is 0. |
| 05:00 to 06:00 | **D1** Sign-in screens | `/login` (sign-in and sign-up forms, errors in plain words), `/verify` (reads the token, sends it with a POST, shows the result), the "check your email" screen with Send again and Sign out. | Seeded users can sign in. A new user sees "check your email". |
| 06:00 to 06:40 | **D2** Evidence log | A table of ID, time, source, event, score and step. Filters: all, in chain, weak signals, late. A search box. Tags for missed and wrongly linked events. | |
| 06:40 to 07:40 | **D3** Report, approvals, Ask the case | `/report` with sentences whose citations jump to their step, a sequence table, limits, actions with their approval state, and Copy as text. `ApprovalsPanel` and `QuestionsPanel` fill Overview's two slots. | An analyst approves an action and sees the name and time. A viewer can't approve. |
| 07:40 to 08:25 | **D4** Admin (first to cut) | `/admin`: users with a role picker, and the approval history. Only admins see it. | |
| 08:30 to 09:00 | **D5** README and demo | Approach, architecture diagram, how to run, the 3 demo accounts, "Simulated data", assumptions, known limits (PLAN §14.11). Lead two timed rehearsals. | The PLAN §13 checklist is all ticked. |

---

## After the freeze (everyone)

| Time | What |
|---|---|
| 08:30 | Freeze. Bug fixes only. Run `/deploy` once more. |
| 08:30 to 09:00 | Person 4 finishes the README. Everyone else does bug fixes. |
| 09:00 to 09:15 | Two demo rehearsals (PLAN §11), with `./run.sh demo`. Record the backup video. |
| 09:30 | Submit the repo link. |
