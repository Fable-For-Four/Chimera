# Chimera: build plan

HackInnovision 2026, Track C (Chimera). Team of 4, each driving one coding agent. Submission at 09:30, presentations from 10:00.

**Pitch in one line:** 5,124 innocent-looking log lines go in, one proven attack story comes out.

**Design:** Lane C designs a dark, desktop-first look in `app/globals.css`, following the screens in section 7. All numbers in this plan's examples are placeholders. The engine must produce the real ones.

**How to use this file:** section 8 is the task board. Each task names the files it owns and the sections that specify it. Sections 4, 5, 6, 7 and 14 are the specifications.

---

## 0. Rules for coding agents

Read this file and `TECH-STACK.md` before writing code.

- Build only your task from section 8. Touch only the files that task owns.
- If something is unclear or missing, ask instead of inventing it.
- Use only the libraries in `TECH-STACK.md`.
- The JSON shapes in section 4 and the routes in section 14 are contracts. Do not change them without the team agreeing.
- A task is finished when its "Done when" checks pass and `pytest` is green.
- One task per branch, small pull requests, never push to `main`.
- Never commit secrets, `.env`, `app.db`, or anything in `out/`.
- Short comments only where the *why* is not obvious from the code. One or two lines, never an essay. Code should read clearly without them.
- Every number shown in the UI comes from the API. Nothing is hardcoded in the UI except labels.

## 1. What we are building

A tool that reads simulated company logs and:

1. finds the one hidden attack that no single alert rule caught,
2. draws it as a graph and a timeline,
3. shows the exact log lines behind every claim,
4. says how sure it is, and stays honest when logs are missing or out of order.

It investigates after the fact. It does not block anything and does not watch a live network.

### The end-to-end flow

1. A person signs up, confirms their email, and signs in. Demo accounts are seeded.
2. The Start screen shows what came in and the old alert rules, none of which fired.
3. An analyst presses Run. The engine works through six stages.
4. Overview shows the verdict, the chain, innocent explanations and recommended actions.
5. The attack graph replays the chain. Each step opens its evidence.
6. The stress test deletes and shuffles logs and shows what survives.
7. The report states what happened, with a log line cited for every sentence.
8. An analyst approves actions. Each approval records who and when.
9. An admin changes roles. A viewer can read but not run or approve.

## 2. How the judging criteria map to features

| Criterion | Feature that earns it |
|---|---|
| Technical depth | Six-stage pipeline: Sort, Profile, Score, Link, Challenge, Report |
| Investigation and reasoning | Attack chain, innocent explanations tested and ranked |
| Uncertainty and robustness | Stress test, late-log handling, confidence on every step, "what the logs cannot prove" |
| Execution and explainability | Exhibits (log lines) behind every step, citations in the report, human approval for actions |
| Innovation and usability | Attack replay, product-quality UI, score against the planted attack |

## 3. Architecture

```
generator ──> data/events.jsonl + truth.json + access.json + history.json + layout.json
                     │
engine (Python) ─────┤  sort → profile → score → link → verdict → challenge → report
                     │
                     └──> out/intake.json, out/case.json, out/stress/00.json … 40.json
                               │
API (FastAPI) ─────────────────┤  sign-in, permission check on every route
   └── SQLite: users, approvals │
                               │
UI (Next.js, calling the API)   ┘
```

- **Engine:** a command-line program that writes JSON files. It knows nothing about users. No ML training.
- **API:** FastAPI on `http://localhost:8000`. Serves the engine's JSON to signed-in users and records approvals.
- **App data:** SQLite, three tables (users, email tokens, approvals).
- **UI:** a Next.js app on `http://localhost:3000`, built to section 7, one route per screen, reading everything from the API.
- **One address for the browser:** Next.js forwards every `/api/*` request to FastAPI. The browser only ever talks to `localhost:3000`, so the cookie works and no CORS setup is needed.
- **One command:** `./run.sh` creates the venv, installs both sides, generates data, runs the engine, seeds users and starts both servers.

The detection logic is plain deterministic code. No LLM is needed for any must-have feature.

### Repo layout

```
generator/      __main__.py scenario.py noise.py
engine/         sort.py profile.py score.py link.py verdict.py challenge.py report.py
                intake.py stress.py truth.py run.py
data/           events.jsonl truth.json access.json history.json layout.json   (generated, committed)
out/            intake.json case.json stress/*.json                            (generated, not committed)
api/            main.py auth.py permissions.py db.py email.py seed.py
web/            the Next.js app
  app/          layout.tsx globals.css page.tsx
                login/ verify/ graph/ logs/ stress/ report/ admin/   (one page.tsx each)
  components/   Shell.tsx Start.tsx Overview.tsx EvidenceDrawer.tsx ApprovalsPanel.tsx QuestionsPanel.tsx
  lib/          api.ts types.ts state.tsx
  next.config.ts package.json
tests/          fixtures/case.sample.json fixtures/intake.sample.json test_*.py
run.sh  requirements.txt  .env.example  .gitignore  README.md  PLAN.md  TECH-STACK.md
```

## 4. The data contracts

### 4.1 One event (`data/events.jsonl`, one JSON object per line, in arrival order)

```json
{
  "id": "L-1881",
  "ts": "2026-11-14T03:12:17Z",
  "received_at": "2026-11-14T03:12:19Z",
  "source": "vpn-gw",
  "action": "AUTH_OK",
  "user": "priya.s",
  "host": null,
  "src": "203.0.113.47",
  "dst": null,
  "attrs": { "geo": "RO" },
  "raw": "03:12:17 vpn-gw AUTH_OK user=priya.s src=203.0.113.47 geo=RO"
}
```

- `ts` is the source machine's clock. `received_at` is when the log reached us.
- `attrs` keys in use: `geo`, `type`, `actor`, `member`, `group`, `cmd`, `service`, `path`, `files`, `bytes_out`, `job`.
- Actions in use: `AUTH_OK`, `AUTH_FAIL`, `PROC_START`, `GROUP_ADD`, `LOGON`, `TICKET_REQ`, `SMB_SESSION`, `FILE_READ`, `CONN_OPEN`, `CONN_CLOSE`, `DNS_QUERY`, `MAIL_RECV`, `MAIL_SEND`, `JOB_START`, `JOB_END`, `CRON`, `HEALTH_OK`.

### 4.2 Supporting files

`history.json`, the 30-day baselines:

```json
{
  "users": { "priya.s": { "countries": ["IN"], "hours": [9, 19], "hosts": ["WS-PRIYA-014", "MAIL-01"], "actions": ["AUTH_OK", "MAIL_RECV", "MAIL_SEND"] } },
  "service_accounts": { "svc-backup": { "logon_types": ["batch"], "sources": ["BKP-01"], "job_hours": [1], "admin": false } },
  "hosts": { "FIN-SRV-02": { "outside_peers": [], "daily_upload_mb": 50 } }
}
```

`hours` is `[first, last]` in whole UTC hours, inclusive. A night worker has `[22, 6]`, which wraps past midnight.

`access.json`: `{ "priya.s": ["WS-PRIYA-014", "MAIL-01"], "svc-backup": ["BKP-01", "FIN-SRV-02", "HR-SRV-01", "DC-01"] }`

`truth.json`: `{ "planted": ["L-1873", "…"] }`

`layout.json`: `{ "priya.s": [225, 250], "…": [x, y] }`, positions inside an 860 by 480 canvas for the scenario's nodes.

### 4.3 Before the run (`out/intake.json`)

```json
{
  "summary": { "events": 5124, "sources": 4, "late": 212, "alerts_fired": 0 },
  "alert_rules": [ { "name": "5 failed sign-ins in a minute", "seen": "saw 2 of 5", "ratio": 0.4, "fired": false } ],
  "volume": [ { "start": "03:00", "count": 268 } ],
  "latest": [ { "id": "L-0001", "time": "03:00:02", "source": "MAIL-01", "raw": "…" } ]
}
```

`volume` has one entry per 5 minutes. `latest` is the first 8 events in arrival order.

### 4.4 After the run (`out/case.json`)

```json
{
  "level": 0,
  "deleted": 0,
  "summary": { "events": 5124, "sources": 4, "late": 212, "alerts_fired": 0 },
  "stages": [ { "name": "Sort", "does": "Put every event in true time order", "result": "212 late events moved", "seconds": 0.4 } ],
  "verdict": {
    "label": "Likely attack", "confidence": 87, "found": true,
    "headline": "A stolen password became a domain admin in 29 minutes. Payroll data started leaving 55 minutes after the first sign-in.",
    "entry_point": { "account": "priya.s", "event": "L-1881", "text": "priya.s over VPN, from a country she has never signed in from" },
    "blast_radius": { "accounts": ["priya.s", "svc-backup"], "touched": ["WS-PRIYA-014", "DC-01", "FIN-SRV-02"], "reachable": ["HR-SRV-01"] },
    "data_at_risk": { "files": 1412, "bytes_out": 2254857830 },
    "weakest_step": 3
  },
  "chain": [
    {
      "step": 1, "stage": "Initial access", "technique": "T1078 Valid Accounts", "time": "03:12", "minute": 12,
      "from": "203.0.113.47", "to": "priya.s",
      "what": "VPN sign-in to priya.s from a new country",
      "confidence": 82, "inferred": false,
      "usual": "India, 09:00 to 19:00", "now": "Romania, 03:12",
      "signals": [ { "name": "New country for this user", "weight": 0.34 } ],
      "exhibits": [ { "id": "L-1881", "raw": "…", "late": false, "present": true } ]
    }
  ],
  "graph": {
    "nodes": [ { "id": "priya.s", "type": "user", "state": "hit", "x": 225, "y": 250, "step": 1 } ],
    "edges": [ { "from": "priya.s", "to": "MAIL-01" } ]
  },
  "volume": [ { "start": "03:00", "count": 268 } ],
  "hypotheses": [ { "name": "Outside attacker with a stolen password", "share": 87, "fits": ["All five steps, in order"], "breaks": [] } ],
  "events": [ { "id": "L-1881", "time": "03:12:17", "source": "vpn-gw", "raw": "…", "score": 0.62, "reasons": ["New country for this user"], "step": 1, "late": false, "truth": "found" } ],
  "truth_score": { "planted": 12, "found": 11, "linked": 11, "recall": 92, "precision": 100, "missed": ["L-2152"], "false_links": [] },
  "report": [ { "text": "At 03:12 someone signed in as priya.s from Romania after 2 failed tries.", "cites": ["L-1881"], "step": 1 } ],
  "limits": [ "Whether the payroll files were opened or only copied." ],
  "actions": [ { "id": "reset-priya.s", "kind": "Contain", "text": "Reset the priya.s password and end her sessions" } ],
  "questions": [ { "q": "Why is svc-backup flagged?", "a": "It was made a domain admin at 03:41 and then signed in by hand on DC-01.", "cites": [ { "id": "L-2051", "step": 2 } ] } ]
}
```

- Node `type`: `user`, `machine` or `outside`. Node `state`: `hit`, `reach` or `normal`. `step` is the first step that reaches the node, and is absent for normal nodes.
- `events` holds every event scoring 0.30 or more, plus 40 normal events picked with the fixed seed, in arrival order. `step` is null when the event is not in the chain. `truth` is `found`, `missed`, `false_link` or null.
- When no chain is found: `verdict.found` is false, `label` is "No chain found", `confidence` is 0, and `chain`, `report`, `actions` and `questions` are empty lists. The UI must show this state without errors.
- A stress file has the same shape, with `level` set to the percentage and `deleted` to the number of events removed.

`tests/fixtures/case.sample.json` and `intake.sample.json` are hand-written examples of these shapes, using the example values in this section. The UI is built against them until the engine is ready.

## 5. The scenario and the generator

`python -m generator --seed 7` writes the five files in `data/`. The same seed always gives the same files.

### The company

- Window: 2026-11-14, 03:00 to 04:30 UTC.
- 50 users. Named ones: `priya.s`, `arjun.m`, `neha.k`. The other 47 get generated names. 12 of the 50 are night workers with hours `[22, 6]`. Everyone else has `[9, 19]`.
- One service account: `svc-backup`.
- 20 machines: `MAIL-01`, `DC-01`, `FIN-SRV-02`, `HR-SRV-01`, `BKP-01`, `PRINT-02`, and 14 workstations named `WS-NAME-NNN`, including `WS-PRIYA-014` and `WS-NEHA-022`.
- 4 log sources: `vpn-gw`, `dc`, `files`, `fw-edge`. Each event's `source` is one of these or the machine name.

### Normal noise, about 5,100 events

- Comes only from the 12 night workers and from machine jobs (mail, health checks, cron, print cleanup, and a backup verify job at 03:20).
- The 03:20 backup verify is only `JOB_START` and `JOB_END` events by `svc-backup` from `BKP-01`. Those two actions are exempt from the "Wrong time" rule, so the job scores 0 even though `svc-backup`'s `job_hours` is `[1]`.
- Every normal event stays inside its user's or machine's baseline, so it scores under 0.15.
- Roughly even over time, about 285 events every 5 minutes.

### Lone oddities, 25 events

- Each breaks exactly one rule for an unrelated user or machine, for example one night worker signing in from a new device.
- They score between 0.25 and 0.45 and share no entity at all with the attack: no user, machine (servers included) or address. They become the weak signals that are scored but not linked.

### The attack, 12 planted events

| Step | Time | Events | ATT&CK (verify the IDs) |
|---|---|---|---|
| 1 | 03:09 to 03:12 | Two `AUTH_FAIL` then `AUTH_OK` for `user=priya.s` from `src=203.0.113.47`, `geo=RO` | T1078 Valid Accounts |
| 2 | 03:38, 03:41 | `PROC_START` with `user=priya.s`, `host=WS-PRIYA-014`, `cmd=net-group`. `GROUP_ADD` with `user=priya.s`, `host=DC-01`, `actor=priya.s`, `member=svc-backup`, `group=Domain-Admins` | T1098.007 Additional Local or Domain Groups |
| 3 | 03:44, 03:45 | `LOGON type=interactive` with `user=svc-backup`, `host=DC-01`, `src=WS-PRIYA-014`. `TICKET_REQ` with `user=svc-backup`, `host=DC-01`, `src=WS-PRIYA-014`, `service=cifs/FIN-SRV-02` | T1021 Remote Services |
| 4 | 03:52, 03:53 | `SMB_SESSION` then `FILE_READ` of `path=/finance/payroll/2026`, `files=1412`, with `user=svc-backup`, `host=FIN-SRV-02`, `src=WS-PRIYA-014` | T1039 Data from Network Shared Drive |
| 5 | 04:05 to 04:19 | `DNS_QUERY` with `src=FIN-SRV-02`. `CONN_OPEN` and `CONN_CLOSE` with `src=FIN-SRV-02`, `dst=198.51.100.23:443`, `CONN_CLOSE` with `bytes_out` of about 2.1 GB | T1048.002 Exfiltration Over Asymmetric Encrypted Non-C2 Protocol |

Every field listed above must be set. Each one is needed for the event to reach 0.30 and to link to its neighbours. The step 2 `PROC_START` (`net-group`) is really discovery (T1069), but it is shown inside the privilege step because it leads straight to the group change.

### Deliberate mess

- 212 events get a `received_at` 3 to 12 minutes after `ts`, and the file is written in `received_at` order. The step 3 `LOGON` is one of them, 6 minutes late, so it appears after the `TICKET_REQ`. The other 211 are picked from normal noise only, never from planted events or lone oddities, because the late penalty (×0.9) could push a 0.30 event under the link threshold.
- The `DNS_QUERY` matches no scoring rule. It is the planted event the engine is expected to miss.
- Each attack step stays under the old alert limits (section 6.1).
- No attack entity (`priya.s`, `svc-backup`, `WS-PRIYA-014`, `DC-01`, `FIN-SRV-02`, `203.0.113.47`, `198.51.100.23`) may appear in more than 5% of all events, or Link treats it as a hub and the chain breaks. Spread the `dc` and `files` noise across other machines to keep `DC-01` and `FIN-SRV-02` under the limit.

### IDs and layout

- IDs are `L-0001` upward in arrival order.
- `layout.json` gives positions for the attack's nodes and the six named normal nodes, on the 860 by 480 canvas. The attack path reads left to right:

| Node | Position | Node | Position |
|---|---|---|---|
| `203.0.113.47` | [70, 240] | `198.51.100.23` | [760, 240] |
| `priya.s` | [190, 240] | `HR-SRV-01` | [570, 400] |
| `WS-PRIYA-014` | [310, 240] | `MAIL-01` | [190, 80] |
| `DC-01` | [430, 160] | `arjun.m` | [330, 80] |
| `svc-backup` | [430, 320] | `PRINT-02` | [690, 80] |
| `FIN-SRV-02` | [570, 240] | `BKP-01` | [310, 400] |
| `neha.k` | [800, 400] | `WS-NEHA-022` | [690, 400] |

**Done when:** two runs with the same seed give identical files. The file has 5,100 to 5,200 events. `truth.json` lists 12 IDs. The step 3 `LOGON` appears after the `TICKET_REQ` in the file but has the earlier `ts`. No attack entity is in more than 5% of events. No planted event other than the `LOGON` is late.

## 6. The engine

`python -m engine.run` reads `data/`, writes `out/intake.json`, `out/case.json` and the nine stress files, and prints the chain to the terminal. Each stage is a function that takes plain data and returns plain data. Each has a test.

### 6.1 Intake (`intake.py`)

Runs without the rest of the pipeline. Produces section 4.3.

- `summary`: event count, number of distinct `source` values among the 4 log sources, late count (`received_at - ts` over 2 minutes), alerts fired.
- `volume`: counts per 5 minutes by `ts`.
- `alert_rules`, the old single-event rules:

| Rule | How it is measured | Limit |
|---|---|---|
| 5 failed sign-ins in a minute | Most `AUTH_FAIL` for one user inside any 60 seconds | 5 |
| Outbound transfer over 5 GB | Largest `bytes_out` on one `CONN_CLOSE` | 5 GB |
| Sign-in from a blocked country | Any `AUTH_OK` with `geo` in `["KP", "IR"]` | any |
| Admin group changed by an unknown account | Any `GROUP_ADD` whose `actor` is not in `history.users` | any |

`ratio` is seen divided by limit, capped at 1, and 0 for the last two when nothing matched.

**Done when:** on the generated data, all four rules have `fired` false and `alerts_fired` is 0.

### 6.2 Sort (`sort.py`)

- Order events by `ts`, ties by `id`.
- Mark `late` when `received_at - ts` is over 2 minutes.
- Result line: "N late events moved".

**Done when:** the step 3 `LOGON` comes before the `TICKET_REQ` after sorting.

### 6.3 Profile (`profile.py`)

- Load `history.json` and answer: is this account a user or a service account, what are its countries, hours, hosts, actions, logon types, sources, job hours, and for a machine its outside peers and daily upload.
- An address is outside when it is not in the `10.0.0.0/8` range and is not a known machine name.
- Result line: "N baselines from 30 days".

### 6.4 Score (`score.py`)

Each rule checks one event against its baseline. A rule that matches adds its name and weight.

| Rule name (shown in the UI) | Matches when | Weight |
|---|---|---|
| New country for this user | `AUTH_OK` or `AUTH_FAIL` with `geo` not in the user's countries | 0.34 |
| Outside the usual hours | A user's event at an hour outside their `hours` | 0.28 |
| Failed tries, then success | `AUTH_OK` with 2 or more `AUTH_FAIL` for the same user in the 5 minutes before | 0.20 |
| First group change by this user | `GROUP_ADD` whose `actor` has no `GROUP_ADD` in their `actions` | 0.36 |
| Service account gains admin rights | `GROUP_ADD` whose `member` is a service account and whose `group` is `Domain-Admins` | 0.38 |
| Lookup command for groups | `PROC_START` with `cmd` in `["net-group", "whoami", "nltest"]` | 0.25 |
| Service account used by a person | `LOGON` with `type=interactive` by a service account without `interactive` in `logon_types` | 0.33 |
| Wrong machine for this service account | Any event by a service account whose `src` is not in its `sources` | 0.30 |
| Wrong time for this service account | Any event by a service account at an hour not in `job_hours`, except `JOB_START` and `JOB_END` | 0.27 |
| Large read of files | `FILE_READ` with `files` of 500 or more | 0.30 |
| First outside connection | `CONN_OPEN` or `CONN_CLOSE` from a machine to an outside address not in its `outside_peers` | 0.33 |
| Upload far above normal | `CONN_CLOSE` with `bytes_out` at least 20 times the machine's `daily_upload_mb` | 0.30 |

- Combine: `score = 1 - (1-w1)(1-w2)…`. Several weak signals add up and never pass 1.
- A late event's score is multiplied by 0.9, and it gets an extra reason "Log arrived late, time less certain" with weight -0.10 for display.
- Round scores to 2 decimals.
- Result line: "N weak signals", counting events at 0.30 or more.

**Done when:** every planted event except the `DNS_QUERY` scores 0.30 or more. No normal noise event scores 0.15 or more. Each score lists its reasons.

### 6.5 Link (`link.py`)

1. **Candidates:** events scoring 0.30 or more.
2. **Entities of an event:** the non-empty values of `user`, `host`, `src`, `dst`, `attrs.actor` and `attrs.member`.
3. **Hubs:** an entity that appears in more than 5% of all events is a hub and cannot link events.
4. **Join:** two candidates are joined when they share a non-hub entity and their `ts` values are within 45 minutes. Build the groups with `networkx` connected components.
5. **Pick the chain:** the group with the highest total score that has at least 3 events and at least 2 different stages. If there is none, there is no chain.
6. **Stages:** each chain event belongs to a stage by its action.

| Stage | Actions | Technique | `from` | `to` |
|---|---|---|---|---|
| Initial access | `AUTH_FAIL`, `AUTH_OK` | T1078 Valid Accounts | `src` | `user` |
| Privilege escalation | `PROC_START`, `GROUP_ADD` | T1098.007 Additional Domain Groups | `attrs.actor` | `attrs.member` |
| Lateral movement | `LOGON`, `TICKET_REQ` | T1021 Remote Services | `user` | `host` |
| Collection | `SMB_SESSION`, `FILE_READ` | T1039 Network Shared Drive | `user` | `host` |
| Exfiltration | `CONN_OPEN`, `CONN_CLOSE`, `DNS_QUERY` | T1048.002 Encrypted Non-C2 Protocol | `src` | `dst` |

7. **Steps:** one step per stage that has events, in the stage order above. `from` and `to` come from the step's highest-scoring event. `time` is that event's `ts`. `minute` is minutes after the window start. Exhibits are the step's events in time order. Signals are the reasons of its events, each once, highest weight first.
8. **Step confidence:** `1 - (1-s1)(1-s2)…` over the step's event scores, capped at 0.97, as a whole percentage.
9. **Inferred steps:** if a stage between the first and last present stages has no events, add a step with `inferred` true, no exhibits, confidence at half the lower of its two neighbours, `from` set to the previous step's `to`, and `to` set to the next step's `from`.
10. **Chain confidence:** the mean of all step confidences, times `0.6 + 0.08 × (number of stages with real events)`, rounded.
11. **What, usual, now:** one template per stage. Examples: "VPN sign-in to {user} from a new country", usual "{countries}, {hours}", now "{geo}, {time}". Keep each template to one short line.

Result line: "1 chain, N steps, M events" or "No chain found".

**Done when:** the generated data gives 5 steps in order with 11 events. The `DNS_QUERY` is not in the chain. None of the 25 lone oddities is in the chain. A file with the attack events removed gives no chain.

### 6.6 Verdict (`verdict.py`)

- **Label:** 70 or more is "Likely attack". 50 to 69 is "Probable attack". Under 50 is "Possible attack". No chain is "No chain found".
- **Entry point:** the first step. `account` is its `to`. `event` is its highest-scoring exhibit.
- **Blast radius:** accounts are every user or service account that is a `from` or `to` in the chain. Touched machines are every machine in a chain event. Reachable machines are everything in `access.json` for those accounts, minus the touched ones.
- **Data at risk:** `files` summed over the chain's `FILE_READ` events, and `bytes_out` summed over its `CONN_CLOSE` events.
- **Weakest step:** the step with the lowest confidence.
- **Headline:** minutes from step 1 to the privilege step, and minutes from step 1 to the start of exfiltration, in one or two sentences.
- **Graph:** nodes are every chain entity (`hit`), every reachable machine (`reach`), and up to 6 normal nodes that share an event with a chain node. Positions come from `layout.json`. A node missing from the layout is placed along the bottom edge, spaced evenly. Edges are the user and machine pairs that share a normal event among the shown nodes.
- **Actions:** one per rule that applies.

| When | Kind | Text | `id` |
|---|---|---|---|
| A user account is compromised | Contain | Reset the {user} password and end their sessions | `reset-{user}` |
| A service account gained admin rights | Contain | Remove {account} from Domain Admins | `demote-{account}` |
| Data went to an outside address | Contain | Block {dst} and isolate {host} | `block-{dst}` |
| A machine is reachable but not touched | Check | Review {host}, which the account could reach | `review-{host}` |

### 6.7 Challenge (`challenge.py`)

Two innocent explanations, each able to explain only certain stages.

| Explanation | Explains | Cannot explain |
|---|---|---|
| The account owner working late while travelling | Initial access | Every other stage present |
| A backup job set up wrongly | Collection, when the account is a service account | Every other stage present |

- The attack's share is the chain confidence.
- The rest, `100 - confidence`, is split between the two explanations in proportion to the summed confidence of the steps each explains. If neither explains anything, split evenly.
- Round so the three shares add to exactly 100.
- `fits` and `breaks` are plain phrases built from the stage names.

Result line: "2 tested, both weaker", or which one is not weaker.

**Done when:** shares add to 100, and each explanation lists what fits and what breaks.

### 6.8 Report (`report.py`)

- One sentence per step from a template for its stage, citing the step's highest-scoring exhibit. An inferred step gets "The logs do not show {stage}, but the steps before and after need it." with no citation.
- `limits`: one line per inferred step, "Whether {machine} was touched" for each reachable machine, "Whether the files were opened or only copied" when Collection is present, and "How the password was obtained" when Initial access is present.
- `questions`, three ready answers built from the chain: why the service account is flagged, whether it could be the account owner, and what the logs cannot prove. Each lists the log IDs it relies on.
- Check every cited ID exists in the events. Drop any sentence that fails.

Result line: "N claims, N citations".

### 6.9 Score against the truth (`truth.py`)

- `found`: planted events that are in the chain. `missed`: planted events that are not. `false_links`: chain events that are not planted.
- `recall` is found over planted. `precision` is found over all chain events. Both as whole percentages.
- Mark each entry in `events` with `truth`.
- Show the real numbers. Do not tune the data to hit a target.

### 6.10 Stress runs (`stress.py`)

For each level 0, 5, 10 … 40:

1. Delete that percentage of events at random with `random.Random(seed + level)`.
2. Give 20% of the rest a new `received_at`, 0 to 10 minutes after `ts`, and reorder the file.
3. Run the whole pipeline.
4. For each step that also exists at level 0, add the level-0 exhibits that were deleted, with `present` false.
5. Write `out/stress/NN.json`.

All nine files are written by `engine.run`. Nothing is computed during the demo.

**Done when:** level 0 equals `case.json`. Chain confidence at level 40 is lower than at level 0. Every file passes the shape check.

### 6.11 Run (`run.py`)

- `run(data_dir, out_dir)` runs intake, then the pipeline, then truth, then stress, timing each of the six named stages for `stages`.
- It is built early (task A5) so integration can start. A stage that is not merged yet leaves its fields as empty lists or `null`, which the contract allows. Lane A adds each call as Challenge, Report, truth and stress merge.
- The six stages reported are Sort, Profile, Score, Link, Challenge, Report. Verdict counts inside Link's time.
- Prints the chain: one line per step with time, stage, confidence and exhibit IDs.

**Done when:** `python -m engine.run` finishes in under 20 seconds and `out/case.json` passes the shape check in `tests/test_contract.py`.

## 7. The UI

A Next.js app in `web/`, built to the screens below. Every value comes from the API.

### Structure

- **Next.js with the App Router and TypeScript.** Created with `create-next-app`, without Tailwind.
- **Every screen is a client component** (`"use client"` at the top). Data is fetched in the browser with `fetch`. No server components fetch data, so the cookie never has to be forwarded by hand.
- `app/globals.css` holds all styles in one file: a dark theme, desktop first, plain class names. No CSS framework.
- `app/layout.tsx` loads the fonts with `next/font/google` (Geist, Geist Mono, Instrument Serif) and wraps every page in the state provider and `Shell`.
- `components/Shell.tsx` draws the sidebar and top bar, and decides between sign-in, "check your email" and the app (section 14.9).
- `lib/api.ts` wraps `fetch`: JSON in and out, a `401` sends the user to `/login`, a `403` shows its message.
- `lib/types.ts` holds TypeScript types for the shapes in sections 4.3 and 4.4. Every screen uses them.
- `lib/state.tsx` is a React context holding the signed-in user, the current case, the selected step and the stress level.
- `next.config.ts` has one rewrite: `/api/:path*` goes to `http://localhost:8000/api/:path*`.
- Routes: `/` (Start, then Overview once a case exists), `/graph`, `/logs`, `/stress`, `/report`, `/admin`, `/login`, `/verify`.
- The graph, timeline, confidence ring and stress chart are SVG written in JSX. No chart or graph library.

### Screens

| Screen | File in `web/` | What it must do | Data |
|---|---|---|---|
| **Sign-in and sign-up** | `app/login/page.tsx`, `app/verify/page.tsx` | Two forms. After sign-up, a "check your email" screen with Send again and Sign out. Errors in plain words under the form. | Section 14 |
| **Top bar** | `components/Shell.tsx` | Case title, severity pill, the user's name and role, Sign out. | `/api/auth/me`, `verdict` |
| **Start** | `components/Start.tsx` | Four counts, the volume bars, the four alert rules with how far under the limit each stayed, the first 8 log lines, a Run button. The Run button is disabled for a Viewer. | `/api/intake` |
| **Run** | `components/Start.tsx` | The six stages tick off one after another with their real results, then Overview opens. | `stages` |
| **Overview** | `app/page.tsx`, `components/Overview.tsx` | Verdict label, confidence ring, headline, entry point, blast radius, data at risk, weakest step. The chain as five linked steps. Innocent explanations. How the case was worked. Actions waiting for approval. Ask the case with the three ready questions. | `verdict`, `chain`, `hypotheses`, `stages`, `actions`, `questions`, `/api/approvals` |
| **Attack graph** | `app/graph/page.tsx` | Nodes and edges at their given positions. Attack path in red, numbered. Replay draws the steps one by one. The timeline shows the steps inside the volume bars. Clicking a step opens its evidence. An inferred step is drawn dashed. | `graph`, `chain`, `volume` |
| **Evidence drawer** | `components/EvidenceDrawer.tsx` | Step title, technique, confidence, usual against this time, score reasons, exhibits lettered A, B, C with late and deleted tags, Previous and Next. | `chain` |
| **Stress test** | `app/stress/page.tsx` | A slider from 0 to 40 in steps of 5 loads that level. Chart of the three shares across all levels. Table of each step as Proven, Thin or Guess. The truth score. The chosen level then applies to every screen. | `/api/case/stress/{level}` |
| **Evidence log** | `app/logs/page.tsx` | Table of ID, time, source, event, unusual score, step. Filters: all, in the chain, weak signals, arrived late. Search box. Tags for missed and wrongly linked events. | `events` |
| **Report** | `app/report/page.tsx` | Title, confidence, sentences with citations that jump to the step, sequence table, what the logs cannot prove, actions with their approval state, Copy as text. | `report`, `chain`, `limits`, `actions` |
| **Admin** | `app/admin/page.tsx` | List of users with a role picker, and the approval history. Shown only to an Admin. | `/api/users`, `/api/approvals` |

### States every screen must handle

- **Loading:** a short "Loading" line, never a blank page.
- **No case yet:** `/api/case` returns `404`. Show the Start screen.
- **No chain found:** Overview says "No chain found" with the counts. The graph, stress and report screens say there is nothing to show.
- **Not allowed:** disabled controls for the role, and a plain message on a `403`.
- **Step states:** Proven means every exhibit is present. Thin means some are deleted. Guess means the step is inferred.

### What stays out of the UI

- No number is typed into the UI. If a screen shows a number, it comes from the API.
- Log text is rendered as plain text in JSX, because it is untrusted input. Never use `dangerouslySetInnerHTML`.

## 8. Task board

Four lanes, one person and one agent each. Tasks in a lane run in order, lanes run side by side.

**Re-planned at 02:40 for the time actually left.** The slots below are fixed. If a task runs over its slot, cut scope inside that task first, then use the cut order. The clock does not move.

**Clock:** build 03:00 to 08:30, break 04:00 to 04:30, feature freeze 08:30, submit 09:30. That gives each person 300 minutes of build time.

Task IDs are kept from the earlier board so references elsewhere still work. B2 and B3 moved to Lane D, and Challenge and truth moved to Lane B (as B7), to even out the load.

### Lane A: data and engine core

| Slot | Task | Owns | Spec | Needs |
|---|---|---|---|---|
| 03:00 to 04:00 | **A1** Generator | `generator/`, `data/` | Section 5, 4.1, 4.2 | none |
| 04:30 to 05:20 | **A2** Sort, Profile, Score | `engine/sort.py`, `profile.py`, `score.py`, their tests | 6.2 to 6.4 | A1 |
| 05:20 to 06:35 | **A3** Link and Verdict | `engine/link.py`, `verdict.py`, their tests | 6.5, 6.6 | A2 |
| 06:35 to 06:55 | **A5** Run | `engine/run.py`, its test | 6.11 | A3 |
| 06:55 to 07:25 | **A4** Report | `engine/report.py`, its test | 6.8 | A3 |
| 07:25 to 08:05 | **A6** Stress | `engine/stress.py`, its test | 6.10 | A5 |
| 08:05 to 08:30 | Fixes from integration | | | |

### Lane B: scaffold, API, two engine stages

| Slot | Task | Owns | Spec | Needs |
|---|---|---|---|---|
| 03:00 to 03:20 | **B1** Scaffold | `run.sh`, `requirements.txt`, `.gitignore`, `.gitattributes`, `.env.example` (all already written: check and merge them), `README.md` skeleton | `TECH-STACK.md` | none |
| 03:20 to 04:00, 04:30 to 05:05 | **B4** Accounts | `api/db.py`, `auth.py`, `permissions.py`, `seed.py`, `main.py`, `tests/test_auth.py` | 14.1 to 14.8, tests 1 to 11 | B1 |
| 05:05 to 05:50 | **B5** Case routes | `api/main.py` routes, `tests/test_case_api.py` | 14.6, 14.7 | B2, B4 |
| 05:50 to 06:50 | **B6** Email verification | `api/email.py`, changes in `auth.py`, tests 12 to 18 | 14.12 | B4 |
| 06:50 to 07:30 | **B7** Challenge and truth | `engine/challenge.py`, `truth.py`, their tests | 6.7, 6.9 | A3 (build against `case.sample.json` until A3 merges) |
| 07:30 to 08:30 | Run button end to end, fixes | | | |

Until A5 is merged, B5 serves the sample files.

### Lane C: UI shell and main screens

| Slot | Task | Owns | Spec | Needs |
|---|---|---|---|---|
| 03:00 to 04:00, 04:30 to 05:00 | **C1** Next.js app and shell | `web/package.json`, `next.config.ts`, `app/layout.tsx`, `app/globals.css`, `components/Shell.tsx`, `lib/api.ts`, `lib/types.ts`, `lib/state.tsx` | Section 7, Structure | B2 from 03:30 |
| 05:00 to 06:00 | **C2** Start, Run, Overview | `app/page.tsx`, `components/Start.tsx`, `components/Overview.tsx` | Section 7 | C1 |
| 06:00 to 07:15 | **C3** Attack graph and evidence | `app/graph/page.tsx`, `components/EvidenceDrawer.tsx` | Section 7 | C1 |
| 07:15 to 08:00 | **C4** Stress test | `app/stress/page.tsx` | Section 7 | C3 |
| 08:00 to 08:30 | Layout check at 1080p and 1440p (`/deploy`), fixes | | | |

C1 runs `npm install` in its first 10 minutes, while the venue Wi-Fi works.

Until B5 is merged, `lib/api.ts` returns the sample files, copied into `web/public/samples/`.

### Lane D: contract, intake, sign-in screens, other screens, docs

| Slot | Task | Owns | Spec | Needs |
|---|---|---|---|---|
| 03:00 to 03:30 | **B2** Sample files and shape check | `tests/fixtures/*.sample.json`, `tests/test_contract.py` | 4.3, 4.4 | none |
| 03:30 to 04:00 | Review B1 and C1 diffs. Check the ATT&CK IDs on attack.mitre.org. | | 13 | |
| 04:30 to 05:00 | **B3** Intake | `engine/intake.py`, its test | 6.1 | A1 |
| 05:00 to 06:00 | **D1** Sign-in, sign-up, check your email | `app/login/page.tsx`, `app/verify/page.tsx` | 14.9, 14.12 | C1 |
| 06:00 to 06:40 | **D2** Evidence log | `app/logs/page.tsx` | Section 7 | C1 |
| 06:40 to 07:40 | **D3** Report, approvals, Ask the case | `app/report/page.tsx`, `components/ApprovalsPanel.tsx`, `components/QuestionsPanel.tsx` | Section 7 | C2 |
| 07:40 to 08:25 | **D4** Admin screen (first to cut) | `app/admin/page.tsx` | Section 7 | B5 |
| 08:30 to 09:00 | **D5** README and demo run-through | `README.md` | Sections 11, 13 | everything |

### Checkpoints

| Time | Check | If it fails |
|---|---|---|
| **04:00** | Generator passes its Done-when checks (A1). Scaffold and sample files merged (B1, B2). `npm install` done (C1). | Drop the lone oddities from the generator and add them back after A3. |
| **05:30** | Seeded analyst can sign in (B4). Scores on the real data match 6.4 (A2). Intake merged (B3). | Lane B: cut sign-up (cut order 5). Lane A: fix scoring before anything else. |
| **06:00** | Start and Overview render from the sample files through the API (B5, C2). | Lane C keeps building on the samples. Integration waits for 07:15. |
| **06:45** | Link on the real data gives the 5 steps with 11 events (A3 tests pass). | Simplify the scenario until Link works. Nothing else matters more. |
| **07:15** | A signed-in analyst presses Run and the real engine output drives Start, Overview and the graph. | Everyone stops new work and integrates. |
| **08:00** | Stress, evidence log, report, approvals and email verification work end to end. | Apply the cut order below. |
| **08:30** | **Feature freeze.** Bug fixes only. | |
| **08:30 to 09:15** | README, two demo rehearsals, backup recording by 09:15. | |
| **09:30** | Submit. | |

### Cut order, if behind

Cut from the top. Never cut the engine, the graph, the evidence drawer or the sign-in check.

1. Admin screen (D4)
2. Email verification (B6). Seeded and new users are treated as verified.
3. Ask the case panel
4. Evidence log (D2)
5. Sign-up. Only seeded users can sign in.
6. Stress test screen (C4). Keep the engine's stress files and state the result in the report.

### How two agents avoid collisions

- A task touches only the files it owns. `api/main.py` is shared by B4, B5 and B6, which run in order in one lane.
- `engine/run.py` belongs to Lane A. B3 and B7 do not edit it. Lane A adds their calls when they merge.
- `ApprovalsPanel.tsx` and `QuestionsPanel.tsx` belong to D3. C2 leaves two empty slots for them in `Overview.tsx`.
- `Shell.tsx`, `lib/` and `globals.css` belong to C1. Another task that needs a change there asks the Lane C person.
- A change to a contract needs a message to the team and an update to the sample files first.

## 9. Extra features if there is time

Ranked by how much they raise the chance of winning per hour spent. With the re-planned clock there is no slot for these. Start one only if your lane's tasks are all merged and the 08:00 checkpoint has passed. Realistically only #9 (20 min) fits. Stop at the freeze.

| # | Feature | Why it helps | Time |
|---|---|---|---|
| 1 | **A clean night.** `python -m generator --no-attack` and a second dataset. Verdict: "No chain found". | Proves the tool does not cry wolf. Answers the first question judges ask. | 30 to 45 min |
| 2 | **Earliest moment we could have known.** Run the pipeline on events up to each minute and report when confidence first passed 50%. | A headline for the pitch: "flagged at 03:41, 26 minutes before any data left". | 45 min |
| 3 | **A second attack.** A different chain, such as an insider copying data with no outside sign-in. | Proves the chain is found, not hardcoded. | 1 h |
| 4 | **Which log would help most.** For the weakest step, name the missing source that would raise confidence. | Shows the tool reasons about its own gaps. | 45 min |
| 5 | **Upload your own log file.** Drop a JSONL file, run the engine on it. Needs `python-multipart`. Guarded by `case:run`. | Strong for the live demo and Q&A. | 1 to 1.5 h |
| 6 | **Free-form Ask the case.** An LLM answers from the case JSON only, and every answer must cite log IDs that exist. | Usability. Risky live, so the three ready questions stay as fallback. | 1 to 1.5 h |
| 7 | **What if we had stopped it at step 2.** Remove a step and show what the attacker could no longer reach. | Reasoning quality. | 1.5 h |
| 8 | **Analyst feedback.** Mark a step as innocent and the verdict recalculates. | Human in the loop. | 1 h |
| 9 | **Export the report** as Markdown. | Small polish. | 20 min |
| 10 | **Google sign-in (OAuth).** A second way in, ending in the same JWT session. | Makes the product feel complete. Needs internet at the venue. | 1 to 1.5 h |

## 10. What we will not build

- Training any ML model.
- Real SIEM or cloud integrations.
- Deployment.
- Refresh tokens, password reset, two-factor, rate limiting.
- A message queue. Slow work uses FastAPI background tasks.
- Several cases. There is one case, built from the files in `data/`.
- Live blocking or automatic response. The tool recommends and a person approves.
- A light theme, mobile polish, animations beyond the replay.

## 11. Demo script (8 minutes)

Start already signed in as the analyst.

| Minute | Show | Say |
|---|---|---|
| 0:00 | Start screen | "A normal night at Acme. About 5,000 events. Four alert rules, none fired." |
| 0:45 | Alert rules panel | "Each step stayed under its own limit. Rules look at one event at a time." |
| 1:15 | Press Run | Name the six stages as they tick. |
| 2:00 | Overview | Read the verdict, the entry point and the headline from the screen. |
| 3:00 | Attack graph replay | Let the chain draw itself. Stay quiet for a moment. |
| 4:00 | Click step 3 | "Usual against this time. Why it scored. The exact log lines. This one arrived 6 minutes late and we put it back in order." |
| 5:00 | Innocent explanations | "We tried to explain it away. Here is why each explanation breaks." |
| 5:45 | Stress test | Drag to 20%, then 35%. Read what happens to confidence and to the weakest step. |
| 6:45 | Truth score | "We planted 12 events. Here is how many we found and which one we missed." |
| 7:15 | Report and approvals | "Every sentence cites a log line. Nothing changes until a person approves, and only an analyst can." Approve one action and show the name and time. |
| 7:45 | Close | "5,000 innocent lines in, one proven story out." |

Use the real numbers from the screen. The numbers in this script are placeholders.

Questions to prepare for:

- **Is it hardcoded?** Rerun with a different seed, or show the clean night.
- **Why no ML?** Baselines and rules are explainable and need no training data. Every score lists its reasons.
- **How does it handle clock skew?** Sorts by source time, flags late logs, lowers their score.
- **What about false positives?** Show the weak signals that were scored but not linked, and the truth score.
- **Where does an LLM fit?** Nowhere in detection. Optionally in wording, with citations checked against the logs.
- **How would it scale?** Stream logs through a queue into the same stages, and keep baselines in a database.
- **What would you do next?** Real log formats, more attack patterns, learning weights from analyst feedback.

## 12. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Linking does not find the chain by 06:45 | Narrow the time window and the scenario until it does. A correct small chain beats a broken clever one. |
| Engine and UI disagree on the JSON | The sample files and `tests/test_contract.py` are the reference. The 06:00 checkpoint catches the rest. |
| Two agents edit the same file | File ownership in section 8. |
| Stress runs are slow | They are written by `engine.run` ahead of time. Nothing is computed during the demo. |
| Sign-in fails during the demo | Start the demo already signed in. Run the seed script again if `app.db` is lost. |
| Accounts eat the engine's time | Apply the cut order in section 8. |
| No internet or Resend is down at the venue | Unset `RESEND_API_KEY`. The server prints the verification link to its log. Demo with the seeded accounts. |
| `npm install` fails on venue Wi-Fi | Install in the first 15 minutes. Use a phone hotspot if needed. Commit `package-lock.json`. |
| Two servers to keep running | `run.sh` starts both. For the demo use `npm run build` then `npm start`, which is steadier than dev mode. |
| Live demo breaks | Backup screen recording made at 08:45. |
| The AI tools hit usage limits | Use ChatGPT for review and research, Claude for building. Keep tasks small. |

## 13. Submission checklist

- [ ] `./run.sh` on a clean clone sets up, generates, runs the engine, seeds and starts both servers
- [ ] `npm run build` in `web/` finishes with no type errors
- [ ] The real engine output drives every number on screen
- [ ] "Simulated data" is visible in the UI and stated in the README
- [ ] ATT&CK IDs checked on attack.mitre.org
- [ ] README: approach, architecture diagram, how to run, the three demo accounts, assumptions, known limits
- [ ] `pytest` is green: engine stages, contract shapes, sign-in, permissions
- [ ] `.env`, `JWT_SECRET`, `RESEND_API_KEY`, `app.db` and `out/` are not in the repo
- [ ] `.env.example` lists every variable name
- [ ] Demo rehearsed twice with a timer
- [ ] Backup recording saved
- [ ] Repo link submitted before 09:30

## 14. Sign-in and permissions

Stack choices are in `TECH-STACK.md`. This section is the exact behaviour to build.

### 14.1 Setup

- FastAPI runs on `http://localhost:8000` and serves only the API, under `/api`.
- The Next.js app runs on `http://localhost:3000` and forwards `/api/*` to FastAPI with a rewrite. The browser sees one origin, so the cookie works and FastAPI needs no CORS setup.
- `APP_URL` is `http://localhost:3000`.
- SQLite file `app.db` in the repo root, created on first start. It is in `.gitignore`.
- `JWT_SECRET` comes from the environment. The app refuses to start if it is missing or shorter than 32 characters.
- Other variables (`APP_URL`, `RESEND_API_KEY`, `EMAIL_FROM`, `SEED_PASSWORD`) are listed in `TECH-STACK.md`.

### 14.2 Tables

| Table | Columns |
|---|---|
| `users` | `id` integer primary key, `email` text unique, `name` text, `password_hash` text, `role` text default `viewer`, `email_verified_at` text or null, `created_at` text |
| `email_tokens` | `id` integer primary key, `user_id` integer, `token_hash` text unique, `expires_at` text, `used_at` text or null |
| `approvals` | `id` integer primary key, `action_id` text unique, `user_id` integer, `approved_at` text |

Emails are trimmed and lowercased before saving and before lookup. Times are UTC in ISO 8601.

### 14.3 Passwords

- Hash with `bcrypt`, cost 12. Store only the hash.
- A password must be 8 to 72 bytes long. `bcrypt` ignores everything after 72 bytes, so longer ones are rejected, not cut.
- Never log a password or a hash, and never return `password_hash` from any route.

### 14.4 Token and cookie

- JWT signed with HS256. Claims: `sub` (the user ID as a string) and `exp` (1 hour from issue). Nothing else.
- Sent as a cookie named `session`: `HttpOnly`, `SameSite=Lax`, `Path=/`, `Max-Age=3600`. No `Secure` flag on localhost.
- The UI never reads or stores the token. It calls `/api/auth/me` to learn who is signed in.
- Every route that changes something is `POST` or `PATCH`. No `GET` route changes data.

### 14.5 Finding the current user

One shared function, used by every protected route:

1. Read the `session` cookie. Missing: `401`.
2. Check the signature and expiry. Bad or expired: `401`.
3. Load the user by `sub` from the database. Not found: `401`.
4. Return the user with the role from the database.

The role is never taken from the token, so a role change takes effect on the next request.

### 14.6 Routes

A user in a response is always `{ "id", "email", "name", "role", "verified" }`, where `verified` is true or false. Errors are `{ "detail": "…" }`.

| Route | Body | Success | Failures |
|---|---|---|---|
| `POST /api/auth/signup` | `email`, `name`, `password` | `201` with the user, sets the cookie. Role is `viewer`, `verified` is false. Sends the verification email after the response. | `422` bad email, empty name or password outside 8 to 72 bytes. `409` "An account with this email already exists". |
| `POST /api/auth/verify` | `token` | `200` with the user, now verified | `400` "This link is invalid or has expired" |
| `POST /api/auth/resend-verification` | none | `204`, sends a new email | `401`. `409` if already verified. |
| `POST /api/auth/login` | `email`, `password` | `200` with the user, sets the cookie | `401` "Email or password is incorrect", the same for an unknown email and a wrong password |
| `POST /api/auth/logout` | none | `204`, clears the cookie | none |
| `GET /api/auth/me` | none | `200` with the user | `401` |
| `GET /api/intake` | none | `200` with `out/intake.json` | `401`, `403` |
| `GET /api/case` | none | `200` with `out/case.json` | `401`, `403`, `404` "Run the investigation first" |
| `GET /api/case/stress/{level}` | none | `200` with that stress file | `401`, `403`, `404` unknown level or no case yet |
| `POST /api/case/run` | none | `200` with the fresh case. Runs `engine.run` and waits for it. | `401`, `403`, `500` "The investigation failed" with the reason in the server log |
| `POST /api/actions/{id}/approve` | none | `201` with `action_id`, `approved_by` (name), `approved_at` | `401`, `403`, `404` action not in the current case, `409` already approved |
| `GET /api/approvals` | none | `200` with a list of `action_id`, `approved_by`, `approved_at` | `401`, `403` |
| `GET /api/users` | none | `200` with all users | `401`, `403` |
| `PATCH /api/users/{id}/role` | `role` | `200` with the user | `401`, `403`, `404`, `422` unknown role, `409` when an Admin tries to change their own role |

- On login with an unknown email, still run one `bcrypt` check against a fixed dummy hash, so both failures take the same time.
- `POST /api/case/run` deletes all approvals, because the actions belong to the previous run.
- `intake.json` is written when the server starts, so the Start screen works before any run.

### 14.7 Roles and permissions

| Permission | Viewer | Analyst | Admin |
|---|---|---|---|
| `case:read` View intake, case, evidence, report, approvals | yes | yes | yes |
| `case:run` Run investigation | no | yes | yes |
| `action:approve` Approve containment actions | no | yes | yes |
| `user:manage` List users, change roles | no | no | yes |

| Route | Permission |
|---|---|
| `GET /api/intake`, `GET /api/case`, `GET /api/case/stress/{level}`, `GET /api/approvals` | `case:read` |
| `POST /api/case/run` | `case:run` |
| `POST /api/actions/{id}/approve` | `action:approve` |
| `GET /api/users`, `PATCH /api/users/{id}/role` | `user:manage` |

Rules:

- One map from role to permissions, in `api/permissions.py`. Nothing else in the code names a role.
- One shared check, `require(permission)`, used on every protected route. It answers in this order: not signed in, `401`. Email not verified, `403` "Confirm your email first". Missing the permission, `403` "Your role cannot do this".
- The `/api/auth/*` routes do not need a verified email.
- The UI disables what the user cannot do, using the role from `/api/auth/me`. That is for convenience only. The server check is the real one.

### 14.8 Seed users

`python -m api.seed` creates three accounts if they do not exist, already verified. These are demo accounts for simulated data only.

| Email | Role | Password |
|---|---|---|
| `admin@acme.test` | Admin | from `SEED_PASSWORD`, default `chimera-demo-1` (a known demo-only default, expected by the deployment check) |
| `analyst@acme.test` | Analyst | same |
| `viewer@acme.test` | Viewer | same |

### 14.9 UI behaviour

- The `/verify` page reads `token` from the address, sends it to `/api/auth/verify`, shows "Email confirmed" or the error, then links to the app.
- On every other page, `Shell` calls `/api/auth/me` on load. `401` sends the user to `/login`. `200` with `verified` false shows the "check your email" screen, with Send again and Sign out. `200` with `verified` true shows the app.
- Any `401` from another call returns the user to the sign-in screen.
- A `403` shows its message and changes nothing.
- Send JSON with `fetch` to paths starting with `/api`, never to `localhost:8000` directly. Same origin, so the cookie goes along by default.

### 14.10 Done when

All of these pass as `pytest` tests against the API:

1. Sign-up with a new email returns `201`, role `viewer`, and a `session` cookie.
2. Sign-up with the same email in different capitals returns `409`.
3. Sign-up with a 7-byte or a 73-byte password returns `422`.
4. Login with a wrong password and login with an unknown email return the same `401` body.
5. `/api/auth/me` returns `401` without a cookie, with a tampered token and with an expired token.
6. No response anywhere contains `password_hash`.
7. A Viewer gets `200` on `GET /api/case` and `403` on `POST /api/actions/{id}/approve`.
8. An Analyst can approve. A second approval of the same action returns `409`.
9. An Analyst gets `403` on `GET /api/users`. An Admin gets `200`.
10. After an Admin changes an Analyst to Viewer, that user's existing cookie gets `403` on approve.
11. The app does not start without `JWT_SECRET`.
12. Sign-up calls the email sender once, with a link that starts with `APP_URL`.
13. A new user gets `403` "Confirm your email first" on `GET /api/case`, and `200` after verifying.
14. A verification token works once. The second use returns `400`.
15. An expired token and a made-up token both return `400` with the same body.
16. Sending again makes the earlier token stop working.
17. With `RESEND_API_KEY` unset, sign-up still returns `201` and the link is printed to the log.
18. No test sends a real email. Tests replace the sender with a fake that records calls.
19. `GET /api/case` returns `404` before any run and `200` after `POST /api/case/run`.
20. A Viewer gets `403` on `POST /api/case/run`.

### 14.11 Known limits, to state in the README

- Sign-in attempts and "send again" are not rate limited.
- No password reset.
- With Resend's test sender, mail may only reach the Resend account owner's address. A verified domain removes that limit.
- Plain HTTP on localhost. A real deployment needs HTTPS and the `Secure` cookie flag.
- One 1-hour session with no refresh. The user signs in again after it expires.

### 14.12 Email verification

**Token**
- Made with `secrets.token_urlsafe(32)`.
- Only its SHA-256 hash is saved, in `email_tokens`. The plain token exists only in the email link.
- Valid for 30 minutes and works once. Using it sets `used_at`.
- Making a new token for a user marks that user's older unused tokens as used.

**Link**
- `{APP_URL}/verify?token={token}`. It opens the `/verify` page, which sends the token with `POST /api/auth/verify`.
- Verification is a `POST`, never a `GET`. Mail scanners open links in advance, and a `GET` would use up the token before the person clicks.

**Verify route**
- Hash the token from the body and look it up. Not found, expired or already used: `400` with the same message for all three.
- Otherwise set `users.email_verified_at`, set the token's `used_at`, and return the user.

**Sending**
- One function, `send_verification_email(to, name, link)`, in `api/email.py`. Nothing else in the code talks to Resend.
- It runs after the response, through FastAPI `BackgroundTasks`. A slow or failed send never fails sign-up.
- With `RESEND_API_KEY` set, send through the `resend` package from `EMAIL_FROM`.
- With `RESEND_API_KEY` unset, print the link to the server log and send nothing.
- If Resend returns an error, log the error without the token. The user can press Send again.
- The token and the link are never logged when a key is set.

**The email**
- Subject: "Confirm your email".
- Body, in plain text and simple HTML: a greeting with the name, one sentence, the link, and "This link works for 30 minutes."

**Send again**
- `POST /api/auth/resend-verification` makes a new token and sends a new email.
