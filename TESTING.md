# Testing

Every number below comes from a real run on seed 7. The same input always gives the same output, so anyone can repeat these results.

## Run the tests

```
pytest -q                 # 287 tests, about 45 seconds
cd web && npm run lint    # UI lint
```

CI runs the same suite on every pull request: Python 3.11 and 3.14 on Ubuntu, Python 3.11 on Windows, and the web lint and build. See the Actions tab on GitHub.

## Scenario test cases

These are the end-to-end cases. Each one runs the whole engine on a dataset and checks the result.

| # | Input | Expected output | Result |
|---|---|---|---|
| 1 | `data/`: one night, 5,124 events from 4 sources, with a planted attack | Verdict "Likely attack", 81% confidence, a chain of 5 steps from 03:12 to 04:19 | Pass |
| 2 | Same data, 212 events arriving late | The late events are put back in time order before scoring | Pass |
| 3 | Same data, scored against the 12 planted events | 11 of 12 found, 0 false links (92% recall, 100% precision), missed L-3751 | Pass |
| 4 | `data_dos/`: a noisy night with no attack, 6,912 events | "No chain found", no steps | Pass |
| 5 | Stress test: 20% of logs deleted at random | 1,025 events deleted, the chain is still found at 67% | Pass |
| 6 | Stress test: 40% of logs deleted at random | 2,050 events deleted, the chain is still found at 74% | Pass |
| 7 | The same chain against three innocent explanations | The attack explains all 5 steps (81%); the others explain one step each (10% and 9%) | Pass |

Try cases 1 and 4 yourself:

```
python -m generator --seed 7
python -m engine.run                      # case 1: prints the 5-step chain
python -m engine.run data_dos out/dos     # case 4: prints "No chain found"
```

## Sign-in and permission cases

| # | Request | Expected | Result |
|---|---|---|---|
| 8 | `GET /api/case` while signed out | 401 "Sign in first" | Pass |
| 9 | Sign in with a wrong password | 401, with the same message as an unknown email | Pass |
| 10 | Sign in with the right password | 200, an `HttpOnly` session cookie (`Secure` when `COOKIE_SECURE=true`) | Pass |
| 11 | A viewer starts a new run | 403 | Pass |
| 12 | Passwords in the database | bcrypt hashes at cost 12, never the plain password | Pass |
| 13 | The server starts without `JWT_SECRET` | It refuses to start | Pass |

## Unit tests by area

| File | Tests | What it covers |
|---|---|---|
| `test_auth.py` | 44 | Sign-up, sign-in, cookies, roles, password hashing |
| `test_challenge.py` | 40 | Innocent explanations and why each one breaks |
| `test_parse_logs.py` | 38 | Reading key=value, JSON, syslog and CSV lines |
| `test_case_api.py` | 37 | Case routes, re-runs, stress levels, approvals |
| `test_verification.py` | 24 | Email verification links |
| `test_engine_a2.py`, `test_engine_a3.py` | 34 | Baselines, scoring, linking the chain |
| `test_truth.py` | 18 | Scoring against the planted attack |
| `test_scenario.py`, `test_generator.py`, `test_noise.py` | 25 | The simulated data |
| `test_intake.py` | 10 | The Start screen numbers |
| `test_engine_report.py`, `test_engine_run.py`, `test_engine_stress.py` | 12 | Report, full run, stress runs |
| `test_contract.py` | 5 | JSON shapes match the sample files |
| **Total** | **287** | |
