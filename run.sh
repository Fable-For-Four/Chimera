#!/usr/bin/env bash
# Sets up and starts Chimera with one command.
# Windows: run from Git Bash (not PowerShell or cmd). Mac and Linux: any terminal.
#   ./run.sh        development servers
#   ./run.sh demo   production build of the UI, steadier for the presentation
set -euo pipefail
cd "$(dirname "$0")"
MODE="${1:-dev}"

# On Windows "python3" is often a Microsoft Store stub that fails, so test it before using it.
if command -v python3 >/dev/null 2>&1 && python3 -c "" >/dev/null 2>&1; then PY=python3; else PY=python; fi
if ! "$PY" -c "import sys; sys.exit(sys.version_info < (3, 11))"; then
  echo "Python 3.11 or newer is needed. Found: $("$PY" --version 2>&1)" >&2
  exit 1
fi

# Fail early if an old run is still holding the ports.
for port in 8000 3000; do
  if (echo > "/dev/tcp/127.0.0.1/$port") 2>/dev/null; then
    echo "Port $port is already in use. Stop the old server first." >&2
    exit 1
  fi
done

if [ ! -f .env ]; then
  echo "Missing .env. Copy .env.example to .env and set JWT_SECRET (32 characters or more)." >&2
  exit 1
fi
# Strip Windows line endings, or every value would end in an invisible \r.
# eval, not source <(...): macOS ships bash 3.2, where sourcing a process substitution reads nothing.
set -a
eval "$(tr -d '\r' < .env)"
set +a
JWT_SECRET="${JWT_SECRET:-}"
if [ "${#JWT_SECRET}" -lt 32 ]; then
  echo "JWT_SECRET in .env must be 32 characters or more." >&2
  exit 1
fi

[ -d .venv ] || "$PY" -m venv .venv
# Windows venvs keep their scripts in Scripts/, Mac and Linux in bin/.
if [ -f .venv/Scripts/activate ]; then source .venv/Scripts/activate; else source .venv/bin/activate; fi
python -m pip install -q -r requirements.txt
[ -d web/node_modules ] || npm --prefix web ci

python -m generator --seed 7
python -m engine.run
python -m api.seed

# Stop both servers when this script ends. On Windows, a plain kill leaves the node and python
# children running, so the whole process tree is killed with taskkill instead.
stop() {
  for pid in $(jobs -p); do
    if [ -f "/proc/$pid/winpid" ]; then
      taskkill //F //T //PID "$(cat "/proc/$pid/winpid")" >/dev/null 2>&1 || true
    else
      pkill -TERM -P "$pid" 2>/dev/null || true
      kill "$pid" 2>/dev/null || true
    fi
  done
}
trap stop EXIT INT TERM

uvicorn api.main:app --host 127.0.0.1 --port 8000 &
if [ "$MODE" = demo ]; then
  npm --prefix web run build
  npm --prefix web start &
else
  npm --prefix web run dev &
fi

echo "Chimera is running at http://localhost:3000. Press Ctrl+C to stop."
wait
