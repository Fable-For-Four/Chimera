# Chimera

A log investigation tool for HackInnovision 2026, Track C. It reads simulated company logs, finds the one hidden attack that no single alert rule caught, and shows the exact log lines behind every claim.

**All data is simulated.** The demo accounts exist only for this simulated data.

## Approach

To be written (D5).

## Architecture

```
generator -> data/ -> engine -> out/*.json -> FastAPI (api/, :8000, /api only) -> Next.js (web/, :3000)
```

To be written (D5).

## How to run

Needs Python 3.11 or newer and Node.js 20 or newer. On Windows, use Git Bash.

```
cp .env.example .env      # then set JWT_SECRET to 32 characters or more
./run.sh                  # sets up, generates data, runs the engine, seeds users, starts both servers
```

The app is at http://localhost:3000. `./run.sh demo` uses the production UI build.

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

To be written (D5).

## Known limits

To be written (D5), from `PLAN.md` section 14.11.
