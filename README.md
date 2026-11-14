# Chimera

A log investigation tool for HackInnovision 2026, Track C. It reads simulated company logs, finds the one hidden attack that no single alert rule caught, and shows the exact log lines behind every claim.

**All data is simulated.** The demo accounts exist only for this simulated data.

## Approach

Chimera reconstructs one attack story from thousands of individually ordinary log events. Its deterministic pipeline:

1. sorts events into source time while preserving arrival-time evidence,
2. profiles activity against the supplied 30-day baselines,
3. scores deviations and records the reason for every score,
4. links related weak signals across accounts, machines, addresses and time,
5. challenges the resulting chain with innocent explanations, and
6. produces a cited report, uncertainty limits and human-approved response actions.

The application is an after-the-fact investigation tool. It does not monitor a live network or automatically block activity. Every conclusion can be traced to the original simulated log line, and the stress test shows which conclusions survive when logs are removed.

## Architecture

```
generator --> data/*.json(l) --> deterministic engine --> out/*.json
                                                        |
browser --> Next.js (:3000) -- /api rewrite --> FastAPI (:8000)
                                                        |
                                      out/*.json + SQLite app.db
```

The generator creates a repeatable company scenario from a fixed seed. The Python engine reads those files and atomically writes the intake, case and nine stress-test results. FastAPI serves the generated investigation to authenticated users and stores accounts and approvals in SQLite. The Next.js interface calls only same-origin `/api/*` routes, so the `httpOnly` session cookie never needs to be read by browser code.

The six engine stages use explicit rules and graph relationships rather than an LLM or a trained model. This keeps the result repeatable and makes every score, link and confidence value explainable.

## How to run

Needs Python 3.11 or newer and Node.js 20 or newer. On Windows, use Git Bash.

```
cp .env.example .env      # then set JWT_SECRET to 32 characters or more
./run.sh                  # sets up, generates data, runs the engine, seeds users, starts both servers
```

The app is at http://localhost:3000. `./run.sh demo` uses the production UI build.

`run.sh` regenerates the simulated dataset, runs the investigation, creates the demo users and then starts both servers. Generated output, the local database, environment secrets and server logs are ignored by Git.

Single steps:

```
pip install -r requirements.txt
python -m generator --seed 7
python -m engine.run
python -m api.seed
uvicorn api.main:app --reload --port 8000
cd web && npm install && npm run dev
pytest
```

## Checks

```
./check.sh setup      # create .venv and install requirements
./check.sh            # lint, format check, tests, validate, web lint and build
./check.sh test       # pytest only (extra args go to pytest, e.g. ./check.sh test -k auth)
./check.sh lint       # ruff lint
./check.sh fix        # ruff lint with safe auto-fixes
./check.sh format     # format all Python files
./check.sh validate   # .env, secrets kept out of git, contract shapes
./check.sh web        # npm lint and build in web/
```

## Demo accounts

| Email | Role |
|---|---|
| `admin@acme.test` | Admin |
| `analyst@acme.test` | Analyst |
| `viewer@acme.test` | Viewer |

The password comes from `SEED_PASSWORD` in `.env`, default `chimera-demo-1`.

## Assumptions

- Input is normalized into the event contract documented in `PLAN.md` section 4.1. Raw source text is retained for evidence.
- `history.json` represents the previous 30 days of normal account, service-account and host behavior.
- Event time and arrival time are both available. Chimera treats late arrival as evidence-quality information rather than silently discarding the event.
- The included scenario and truth labels are simulated and exist to demonstrate and score the investigation pipeline.
- One local API process owns investigation runs. It waits for the engine to finish before serving the new case.
- Containment actions are recommendations only. Approval records the analyst and timestamp but does not make changes to a network.
- Real deployments would need source-specific parsers, durable ingestion, HTTPS, stronger session management and production database operations.

## Known limits

- Sign-in attempts and verification-email resends are not rate limited.
- Password reset and multi-factor authentication are not implemented.
- With Resend's test sender, email may only reach the Resend account owner's address. Verifying a domain removes that limit.
- The local demo uses plain HTTP. A real deployment needs HTTPS and the `Secure` cookie flag.
- Sessions last one hour and have no refresh token. Users sign in again after expiry.
- Server logs remain on the machine running the application. When `RESEND_API_KEY` is unset, those logs contain verification links and must not be shared.
- Chimera currently reads its normalized event format rather than connecting directly to S3, Splunk, Sentinel or another customer log store.
- The supplied baselines are static files. A live deployment would maintain evolving baselines in durable storage.
