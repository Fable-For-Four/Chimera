# RedString: build plan

HackInnovision 2026, Track C (Chimera). Team of 4. Submission at 09:30, presentations from 10:00.

**Pitch in one line:** 5,124 innocent-looking log lines go in, one proven attack story comes out.

**Design reference:** the clickable mock (`redstring-mock.html`). Every screen named below exists in it. All numbers in the mock are placeholders; the engine must produce the real ones.

---

## 1. What we are building

A tool that reads simulated company logs and:

1. finds the one hidden attack that no single alert rule caught,
2. draws it as a graph and a timeline,
3. shows the exact log lines behind every claim,
4. says how sure it is, and stays honest when logs are missing or out of order.

It investigates after the fact. It does not block anything and does not watch a live network.

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
generator.py ──> events.jsonl + truth.json + access.json
                     │
engine (Python) ─────┤  sort → profile → score → link → challenge → report
                     │
                     └──> case.json  (+ stress/00.json … stress/40.json)
                               │
UI (the mock, reading JSON) ───┘
```

- **Engine:** Python 3.11, `networkx` for the graph. No ML training.
- **Output:** plain JSON files. The UI loads them. No database, no login, no cloud deploy.
- **UI:** start from the mock. Replace its hardcoded constants (`LOGS`, `NODES`, `CHAIN`, `HYP`, `STAGES`) with data loaded from `case.json`. This is the fastest path to a product-quality screen.
- **Optional later:** a small FastAPI endpoint `POST /investigate` so the Run button calls the engine live.

The detection logic is plain deterministic code. An LLM, if used at all, only rewrites the report text and must cite log IDs. This keeps the demo repeatable and every step explainable in Q&A.

### Repo layout

```
redstring/
  generator/      scenario + noise
  engine/         sort.py profile.py score.py link.py challenge.py report.py run.py
  data/           events.jsonl truth.json access.json history.json
  out/            case.json stress/*.json
  ui/             index.html (from the mock)
  tests/
  README.md
```

## 4. The contract between the two pairs

Agree on this in the first 30 minutes. Pair B builds against a hand-written sample of `case.json` copied from the mock while Pair A builds the engine.

### One event (`events.jsonl`, one per line)

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

`ts` is the source machine's clock. `received_at` is when the log reached us. A late log has a large gap between the two.

### The result (`case.json`)

```json
{
  "summary": { "events": 5124, "sources": 4, "late_fixed": 212, "alerts_fired": 0 },
  "stages": [ { "name": "Sort", "result": "212 late events moved", "seconds": 0.4 } ],
  "verdict": {
    "label": "Likely attack", "confidence": 87,
    "entry_point": { "account": "priya.s", "event": "L-1881" },
    "blast_radius": { "accounts": ["priya.s", "svc-backup"], "touched": ["WS-PRIYA-014", "DC-01", "FIN-SRV-02"], "reachable": ["HR-SRV-01"] },
    "weakest_step": 3
  },
  "chain": [
    {
      "step": 1, "stage": "Initial access", "technique": "T1078", "time": "03:12",
      "from": "203.0.113.47", "to": "priya.s",
      "what": "VPN sign-in to priya.s from a new country",
      "confidence": 82, "inferred": false,
      "usual": "India, 09:00 to 19:30", "now": "Romania, 03:12",
      "signals": [ { "name": "New country for this user", "weight": 0.34 } ],
      "exhibits": [ { "id": "L-1881", "raw": "…", "late": false, "present": true } ]
    }
  ],
  "graph": { "nodes": [ { "id": "priya.s", "type": "user", "state": "hit" } ], "edges": [ { "from": "priya.s", "to": "MAIL-01", "kind": "normal" } ] },
  "hypotheses": [ { "name": "Outside attacker with a stolen password", "share": 87, "fits": ["…"], "breaks": [] } ],
  "events_sample": [ { "id": "L-1881", "score": 0.82, "step": 1, "late": false } ],
  "truth_score": { "planted": 12, "found": 11, "linked": 12, "missed": ["L-2152"], "false_links": ["L-1902"] },
  "report": [ { "text": "At 03:12 someone signed in as priya.s from Romania.", "cites": ["L-1881"] } ],
  "limits": [ "Whether the payroll files were opened or only copied." ],
  "actions": [ { "kind": "Contain", "text": "Reset the priya.s password and end her sessions" } ]
}
```

Stress runs use the same shape, one file per level: `stress/00.json`, `05.json`, … `40.json`.

## 5. The scenario we plant

A fake company, Acme Corp: 50 users, 20 machines, 4 log sources (VPN gateway, domain controller, file servers, edge firewall). One night, 03:00 to 04:30, about 5,000 normal events.

The attack, 12 events in 5 steps:

| Step | Time | What happens | ATT&CK (verify the IDs) |
|---|---|---|---|
| 1 | 03:12 | Two failed VPN sign-ins, then success as `priya.s` from Romania | T1078 Valid Accounts |
| 2 | 03:41 | That session adds `svc-backup` to Domain Admins | T1098 Account Manipulation |
| 3 | 03:44 | `svc-backup` signs in by hand on DC-01 and asks for a ticket to the finance server | T1021 Remote Services |
| 4 | 03:52 | `svc-backup` reads 1,412 payroll files from FIN-SRV-02 | T1039 Data from Network Shared Drive |
| 5 | 04:07 | FIN-SRV-02 sends 2.1 GB to a never-seen address | T1048 Exfiltration Over Alternative Protocol |

Deliberate mess the engine must survive:

- 212 events arrive out of order. One of them is the step 3 logon, 6 minutes late.
- One planted event (a DNS lookup) is weak enough to be missed.
- One innocent event (the 03:20 backup check by `svc-backup`) looks related.
- Each step stays under the existing alert limits: 2 failed logins against a limit of 5, 2.1 GB against a limit of 5 GB.

The generator also writes:

- `truth.json`: the IDs of the planted events, for scoring ourselves.
- `history.json`: 30 days of summarised normal behaviour per user and machine, for baselines.
- `access.json`: which account can reach which machine, for the blast radius.

Use a fixed random seed so every run gives the same data.

## 6. Engine features (must-have)

Each stage is one small module with one test.

### 6.1 Sort
- Order events by `ts`, not by arrival.
- Mark an event `late` when `received_at - ts` is over 2 minutes.
- **Done when:** the step 3 logon lands before the ticket request, and the count of late events is reported.

### 6.2 Profile
- From `history.json`, build a baseline per user (countries, usual hours, machines used, actions ever done), per service account (logon types, source machines, job times) and per machine (outside connections, daily upload).
- **Done when:** `priya.s` shows India and 09:00 to 19:30, and `svc-backup` shows scheduled jobs from BKP-01 only.

### 6.3 Score
- A list of small rules, each with a name and a weight. Examples: new country, outside usual hours, failures then success, first group change, service account gains admin, service account used by hand, wrong source machine, first outside connection, upload far above normal.
- Combine weights so that several weak signals add up without passing 1: `score = 1 - (1-w1)(1-w2)…`.
- Subtract a small penalty when the event was late, because its time is less certain.
- Keep the fired rule names with each event. They become "why it scored high" in the UI.
- **Done when:** attack events score above 0.45, normal noise stays below 0.15, and each score lists its reasons.

### 6.4 Link
- Take events scoring 0.3 or more. Join two of them when they share a user, machine or address, are in time order, and are within 45 minutes.
- The joined events form a chain. Group them into steps and label each step with its ATT&CK stage.
- Step confidence comes from its events' scores and how many exhibits back it. Chain confidence comes from the step confidences and how many attack stages are covered in order.
- A step with no exhibits left but needed to connect its neighbours is kept and marked `inferred`.
- **Done when:** the engine prints the 5 steps in order in the terminal, with confidences, from `events.jsonl` alone.

### 6.5 Verdict
- **Entry point:** the first step of the chain.
- **Blast radius:** from every compromised account, walk `access.json` to list machines touched and machines reachable.
- **Label:** Likely at 70 or more, Probable at 50 or more, otherwise Possible and sent to an analyst.
- **Weakest step:** the lowest confidence.

### 6.6 Challenge
- Two innocent explanations: "Priya working late while travelling" and "backup job set up wrongly".
- For each, mark which steps it can explain and which it cannot. Its share is the weight of what it explains.
- **Done when:** the three shares add to 100 and each lists what fits and what breaks.

### 6.7 Report
- One sentence per step from a template, each with the ID of its strongest exhibit.
- A "what the logs cannot prove" list, filled from inferred steps and missing sources.
- A check that every cited ID exists in the events. A sentence with a bad citation is dropped.

### 6.8 Score against the truth
- Compare linked events with `truth.json`: how many planted events were found, how many linked events were really the attack, which were missed, which were linked by mistake.
- Show the real numbers, even if they are below 92%.

### 6.9 Stress runs
- For each level 0, 5, … 40: delete that share of events at random (fixed seed), shuffle arrival order, rerun the whole pipeline, save the result.
- Precompute all nine files before the demo so the slider is instant.
- **Done when:** confidence falls as the level rises and at least one step becomes `inferred` at a high level.

## 7. UI features

### Must-have screens

| Screen | What it must do |
|---|---|
| **Start** | Counts of events, sources, late arrivals and alerts. The four alert rules with how far under the limit each stayed. A Run button. |
| **Run** | The six stages tick off with their real results from `case.json`. |
| **Overview** | Verdict label, confidence ring, entry point, blast radius, data at risk, weakest step. The 5-step chain. |
| **Attack graph** | Nodes and edges from `case.json`. Attack path in red, numbered. Click a step to open its evidence. Replay button. Timeline with the steps marked inside the noise. |
| **Evidence drawer** | Step title, ATT&CK tag, confidence, usual against this time, score reasons, exhibits with late and deleted tags. |

### Next, in this order

| Screen | What it adds |
|---|---|
| **Stress test** | Slider loads `stress/NN.json`. Chart of the three explanations. Table of Proven, Thin, Guess per step. Truth score. |
| **Innocent explanations panel** | On Overview. |
| **Evidence log** | Table with unusual score, step chip, filters, search. |
| **Report** | Sentences with citations, limits, actions, copy button. |
| **Approval buttons** | On Overview. The tool recommends, a person approves. |

### Graph layout
Give each scenario node a fixed position in the generator output, and show only nodes within one hop of the chain plus a few normal ones. A force layout costs time and looks different on every run.

## 8. Build order and owners

Pair A owns generator and engine. Pair B owns the UI. In each pair, one person builds with Claude and the other reviews the diff with Codex before merge.

| Time | Pair A (engine) | Pair B (UI) |
|---|---|---|
| 01:30 to 02:00 | Repo, contract (section 4), split | Same, plus copy the mock into `ui/` |
| 02:00 to 04:00 | Generator, Sort, Profile, Score | Mock reads a hand-written `case.json`. Start, Run and Overview from data. |
| 02:30 to 04:00 | Mentor round 1: show the mock and this plan, ask what they would cut | |
| 04:00 to 04:30 | Break | Break |
| 04:30 to 06:00 | Link, Verdict, truth score | Attack graph and evidence drawer from data |
| **06:00** | **Checkpoint: the real `case.json` drives the UI end to end** | |
| 06:00 to 07:30 | Challenge, Report, stress runs | Stress test screen, explanations panel |
| 07:30 to 08:30 | Mentor round 2, then extras from section 9 in order | Evidence log, Report screen, extras |
| **08:30** | **Feature freeze.** README, two demo rehearsals, backup screen recording | |
| 09:30 | Submit | |

Rules that protect the plan:

- By 04:00 the engine prints the right chain in the terminal, or we simplify the scenario.
- At 06:00, if the real JSON does not drive the UI, both pairs stop features and integrate.
- After 08:30, bug fixes only.
- Small PRs, merged often. Nobody pushes straight to `main`.

## 9. Extra features if there is time

Ranked by how much they raise the chance of winning per hour spent. Take them in order and stop at the freeze.

| # | Feature | Why it helps | Time |
|---|---|---|---|
| 1 | **A clean night.** A second dataset with no attack. Verdict: "No chain found". | Proves the tool does not cry wolf. Answers the first question judges ask. | 30 to 45 min |
| 2 | **Earliest moment we could have known.** Replay the events in order and report when confidence first crossed 50%. | A headline line for the pitch: "flagged at 03:41, 26 minutes before any data left". | 45 min |
| 3 | **A second attack.** A different chain, such as an insider copying data with no outside sign-in. | Proves the chain is found, not hardcoded. | 1 h |
| 4 | **Which log would help most.** For the weakest step, name the missing source that would raise confidence. | Shows the tool reasons about its own gaps. | 45 min |
| 5 | **Upload your own log file.** Drop a file, run the engine live. | Strong for the live demo and Q&A. Needs the FastAPI endpoint. | 1 to 1.5 h |
| 6 | **Free-form Ask the case.** An LLM answers from the case JSON only, and every answer must cite log IDs that exist. | Usability and explainability. Risky live, so keep the three canned questions as fallback. | 1 to 1.5 h |
| 7 | **What if we had stopped it at step 2.** Remove a step and show what the attacker could no longer reach. | Reasoning quality. | 1.5 h |
| 8 | **Analyst feedback.** Mark a step as innocent and the verdict recalculates. | Human in the loop. | 1 h |
| 9 | **Export the report** as Markdown. | Small polish. | 20 min |

Items 1 and 2 are worth doing before finishing the Evidence log and Report screens.

## 10. What we will not build

- Training any ML model.
- Real SIEM or cloud integrations.
- User accounts, a database, deployment.
- Live blocking or automatic response. The tool recommends and a person approves.
- A light theme, mobile polish, animations beyond the replay.

## 11. Demo script (8 minutes)

| Minute | Show | Say |
|---|---|---|
| 0:00 | Start screen | "A normal night at Acme. 5,124 events. Four alert rules, none fired." |
| 0:45 | Alert rules panel | "Each step stayed under its own limit. Rules look at one event at a time." |
| 1:15 | Press Run | Name the six stages as they tick. |
| 2:00 | Overview | "Likely attack, 87%. In through one stolen password. Payroll data out in 55 minutes." |
| 3:00 | Attack graph replay | Let the chain draw itself. Stay quiet for a moment. |
| 4:00 | Click step 3 | "Usual against this time. Why it scored. The exact log lines. This one arrived 6 minutes late and we put it back in order." |
| 5:00 | Innocent explanations | "We tried to explain it away. Here is why each explanation breaks." |
| 5:45 | Stress test | Drag to 20%, then 35%. "The chain survives, confidence drops, step 3 becomes a guess and we say so." |
| 6:45 | Truth score | "We planted 12 events. We found 11, and linked one by mistake. Here they are." |
| 7:15 | Report and approvals | "Every sentence cites a log line. Nothing changes until a person approves." |
| 7:45 | Close | "5,124 innocent lines in, one proven story out." |

Questions to prepare for:

- **Is it hardcoded?** Show the clean night or the second attack, or rerun with a different seed.
- **Why no ML?** Baselines and rules are explainable and need no training data. Every score lists its reasons.
- **How does it handle clock skew?** Sorts by source time, flags late logs, lowers confidence for them.
- **What about false positives?** Show the weak signals that were scored but not linked, and the truth score.
- **Where does the LLM fit?** Only in wording the report, with citations checked against the logs.
- **What would you do next?** Real log formats, more attack patterns, learning weights from analyst feedback.

## 12. Risks and fallbacks

| Risk | Fallback |
|---|---|
| Linking does not find the chain by 04:00 | Narrow the time window and the scenario until it does. A correct small chain beats a broken clever one. |
| Engine and UI disagree on the JSON | The 06:00 checkpoint. Keep the hand-written sample in the repo as the reference. |
| Stress runs are slow | Precompute the nine files. Never compute during the demo. |
| LLM is slow or wrong live | Template report is the default. LLM text is optional. |
| Live demo breaks | Backup screen recording made at 08:45. |
| Both AI tools hit usage limits | Use ChatGPT for review and research, Claude for building. Keep prompts small. |

## 13. Submission checklist

- [ ] The real engine output drives every number on screen
- [ ] "Simulated data" is visible in the UI and stated in the README
- [ ] ATT&CK IDs checked on attack.mitre.org
- [ ] README: approach, architecture diagram, how to run, assumptions, known limits
- [ ] One command regenerates data and results
- [ ] Tests pass for Sort, Score and Link
- [ ] Demo rehearsed twice with a timer
- [ ] Backup recording saved
- [ ] Repo link submitted before 09:30
