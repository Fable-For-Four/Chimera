# Tech stack

Every tool we use and what it is for. The feature plan is in `PLAN.md`. The exact sign-in and permission rules are in `PLAN.md` section 14.

**For coding agents:** use only the tools listed here. Do not add a dependency, a framework or a build step without the team agreeing first.

## How the parts connect

```
browser
   │  talks only to localhost:3000, cookie carries the JWT
   ▼
Next.js (web/, port 3000) ── pages, and a rewrite that forwards /api/* to FastAPI
   ▼
FastAPI (api/, port 8000) ── the API under /api
   │            │
   │            └── SQLite (app.db): users, email_tokens, approvals
   ▼
out/intake.json, out/case.json, out/stress/*.json  ◄── engine ◄── data/*.json(l) ◄── generator
```

- The engine is a plain command-line program that writes files. It knows nothing about users.
- The browser only ever calls `http://localhost:3000`. Next.js forwards `/api/*` to FastAPI on port 8000. One origin for the browser means the cookie works with no CORS setup.
- All API routes start with `/api`.

## Languages and runtimes

| Tool | Use |
|---|---|
| **Python 3.11+** | Generator, engine and API. Write for 3.11 so every teammate can run it. The main laptop has 3.14. |
| **TypeScript** | The UI code. Types catch a mismatch with the API's JSON before the page runs. |
| **Node.js 20+** | Runs Next.js. The main laptop has Node 24. |
| **CSS** | Styles, copied from the mock into one global file. |
| **SVG** | The attack graph, timeline, confidence ring and stress chart, written in JSX. |
| **Bash** | `run.sh`, the one command that sets up and starts everything. |

## Generator and engine

| Tool | Use |
|---|---|
| **`networkx`** | Joins suspicious events into groups (connected components) in the Link stage. |
| **`json`** (built in) | Reads and writes every data file. |
| **`random`** (built in) | Makes the fake data and the stress runs, always with a fixed seed so results repeat. |
| **`datetime`** (built in) | Parses timestamps, sorts by time, finds late logs. |
| **`ipaddress`** (built in) | Tells an inside address from an outside one. |
| **`argparse`** (built in) | Command-line options such as `--seed`. |
| **`time`** (built in) | Measures how long each stage took. |
| **JSONL files** | Input logs, one event per line. Easy to read, diff and generate. |
| **JSON files** | Engine output that the API serves. |

No pandas, no NumPy, no ML library. The data is 5,000 rows and the logic is rules.

## API

| Tool | Use |
|---|---|
| **`fastapi`** | The API server only: routes under `/api`, request checks, shared sign-in and permission checks. It never serves UI files. The frontend is Next.js only. |
| **`uvicorn`** | Runs the FastAPI app. |
| **`pydantic`** (comes with FastAPI) | Checks request bodies and rejects bad ones with `422`. |
| **`email-validator`** | Lets `pydantic` check that an email address is well formed. |
| **FastAPI `BackgroundTasks`** | Sends the verification email after the response. Our replacement for a message queue. |
| **`logging`** (built in) | Server log. Also where the verification link is printed when no email key is set. |

## Accounts and security

| Tool | Use |
|---|---|
| **`bcrypt`** | Hashes passwords, cost 12. Slow on purpose, so stolen hashes are hard to crack. |
| **`PyJWT`** | Creates and checks the session token, signed with HS256. |
| **`secrets`** (built in) | Makes the random email-verification token. |
| **`hashlib`** (built in) | SHA-256 of the verification token, so only the hash is stored. |
| **`httpOnly` cookie** | Carries the session token. Page scripts cannot read it. |
| **Role-based access control** | Our own small map from role to permissions in `api/permissions.py`. No library. |

## Email

| Tool | Use |
|---|---|
| **Resend** | The email service that delivers the "confirm your email" message. Needs an account and an API key. |
| **`resend`** (Python package) | Calls Resend from `api/email.py`. |

## Storage

| Tool | Use |
|---|---|
| **SQLite** | One file, `app.db`, holding users, email tokens and approvals. No server to run. |
| **`sqlite3`** (built in) | Talks to SQLite with plain SQL. No ORM. Always pass values as parameters, never build SQL from strings. |
| **Files in `data/` and `out/`** | The logs and the engine results. |

## UI

| Tool | Use |
|---|---|
| **Next.js** (App Router) | The frontend framework: one route per screen, the dev server, the production build, and the `/api` rewrite to FastAPI. |
| **React** (comes with Next.js) | Builds each screen from components. All screens are client components. |
| **React context** | Shares the signed-in user, the case, the selected step and the stress level between screens. No state library. |
| **`next/font/google`** | Loads Geist, Geist Mono and Instrument Serif. The fonts are downloaded at build time, so the running app needs no internet for them. |
| **`fetch`** | Calls the API from the browser. |
| **Global CSS** (`app/globals.css`) | The mock's styles. No Tailwind and no component library. |
| **ESLint** (comes with Next.js) | Catches common React mistakes. `npm run lint`. |
| **`npm`** | Installs the frontend packages. Commit `package-lock.json`. |
| **`docs/mock.html`** | The design reference. Keep its look and behaviour. |

Create the app with `npx create-next-app@latest web`, choosing TypeScript, ESLint and the App Router, and declining Tailwind. Use the version it installs and do not upgrade during the hackathon.

No Tailwind, no component library, no state library, no data-fetching library, no chart or graph library.

## Testing and quality

| Tool | Use |
|---|---|
| **`pytest`** | All tests: engine stages, JSON shapes, sign-in, permissions. |
| **`httpx`** | Needed by FastAPI's test client, which calls the API inside tests without a running server. |
| **`ruff`** (optional) | One formatter and linter so four agents write alike. `ruff format` and `ruff check`. |
| **GitHub Actions** (optional) | Runs `pytest` on every pull request. |

## Setup and running

| Tool | Use |
|---|---|
| **`venv`** (built in) | A private Python environment in `.venv/`. |
| **`pip` and `requirements.txt`** | Installs the packages. |
| **`npm` and `web/package.json`** | Installs the frontend packages. |
| **`run.sh`** | Creates the venv, installs both sides, loads `.env`, generates data, runs the engine, seeds users, starts FastAPI and Next.js. On Windows, run it from Git Bash. `./run.sh demo` uses the production UI build. |
| **`.gitattributes`** | Keeps `*.sh` and `.env*` on Unix line endings, so bash works on Windows checkouts. |
| **`.env`** | Local secrets. Never committed. |
| **`.env.example`** | The variable names with empty values, committed. |
| **`.gitignore`** | Keeps `.venv/`, `.env`, `app.db`, `out/`, `__pycache__/`, `web/node_modules/` and `web/.next/` out of the repo. |

`requirements.txt`:

```
networkx
fastapi
uvicorn
bcrypt
PyJWT
resend
email-validator
pytest
httpx
```

Commands:

| Command | Does |
|---|---|
| `./run.sh` | Everything, then serves the app at `http://localhost:3000` |
| `python -m generator --seed 7` | Writes the files in `data/` |
| `python -m engine.run` | Writes the files in `out/` and prints the chain |
| `python -m api.seed` | Creates the three demo accounts |
| `uvicorn api.main:app --reload --port 8000` | Starts the API alone |
| `npm install` (in `web/`) | Installs the frontend packages. Needs internet. |
| `npm run dev` (in `web/`) | Starts the frontend for development on port 3000 |
| `npm run build` then `npm start` (in `web/`) | Builds and serves the frontend for the demo |
| `pytest` | Runs the tests |

## Environment variables

| Name | Needed | Purpose |
|---|---|---|
| `JWT_SECRET` | Always, 32 characters or more | Signs the session token |
| `APP_URL` | Always, default `http://localhost:3000` | Start of the link in the verification email |
| `RESEND_API_KEY` | Optional | Sends real email. If unset, the server prints the verification link to its log instead. |
| `EMAIL_FROM` | Optional, default `onboarding@resend.dev` | Sender address. Set it to an address on a verified domain to reach any inbox. |
| `SEED_PASSWORD` | Optional | Password for the three demo accounts |

## Team tools

| Tool | Use |
|---|---|
| **Git and GitHub** (`Fable-For-Four/Chimera`) | One repo, one branch per task, pull requests into `main`. |
| **Claude Code** | Builds each task from `PLAN.md` section 8. |
| **Codex / ChatGPT** | Reviews each pull request's diff before merge, and handles research. |
| **`PLAN.md` and `TECH-STACK.md`** | The shared instructions every agent reads first. |

## Optional tools, only for extra features

| Tool | Use | Extra feature |
|---|---|---|
| **`python-multipart`** | Lets FastAPI accept file uploads | Upload your own log file |
| **`Authlib`** | Google sign-in through OpenID Connect | Google sign-in |
| **An LLM API** (needs an API key, which chat subscriptions do not include) | Free-form answers that must cite log IDs | Free-form Ask the case |

## Choices in short

| Piece | Choice |
|---|---|
| Sign-in method | Email and password per user |
| New users | Sign-up with email, name and password. New accounts get the Viewer role. |
| Email verification | A link sent through Resend. Random token, stored as a hash, valid 30 minutes, works once. |
| Unverified users | Can sign in, but see only the "check your email" screen |
| Demo users | A seed script creates one Admin, one Analyst and one Viewer, already verified |
| Password storage | `bcrypt` hash, cost 12 |
| Token contents | User ID (`sub`) and expiry (`exp`) only |
| Token lifetime | 1 hour, no refresh token |
| Where the browser keeps it | `httpOnly` cookie, `SameSite=Lax` |
| Signing key | `JWT_SECRET` environment variable |
| Roles | Viewer, Analyst, Admin. Routes check a named permission. The role is read from the database on every request. |
| Status codes | `401` not signed in, `403` signed in but not allowed |

## Left out on purpose

- Refresh tokens, password reset, two-factor, rate limiting.
- A message queue. The data arrives once as a file and the engine finishes in seconds.
- An ORM. Three small tables do not need one.
- Tailwind, a component library, a state library and a data-fetching library.
- Next.js server components that fetch data, server actions and middleware. Every screen fetches in the browser.
- A graph layout library and a chart library.
- pandas, NumPy and any ML library.
- Docker and cloud hosting.

## Open decisions

- **Email sender:** with Resend's test sender, mail may only reach the Resend account owner's address. Check this in the Resend dashboard. To reach any inbox, verify a domain there and set `EMAIL_FROM`.
- **UI base:** the Chimera mock, saved as `docs/mock.html`. **Not in the repo yet.** Whoever has it commits it before 03:00, because Lane C styles and Lane A's `layout.json` both copy from it.
- **Product name:** Chimera (decided).
