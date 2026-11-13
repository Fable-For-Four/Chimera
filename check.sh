#!/usr/bin/env bash
# Developer checks, like npm scripts. Windows: run from Git Bash.
#   ./check.sh setup      create .venv and install requirements
#   ./check.sh test       run pytest (extra args go to pytest, e.g. ./check.sh test -k auth)
#   ./check.sh lint       ruff lint, no changes
#   ./check.sh fix        ruff lint with safe auto-fixes
#   ./check.sh format     format all Python files (changes files)
#   ./check.sh validate   .env, secrets kept out of git, contract shapes
#   ./check.sh web        npm lint and build in web/
#   ./check.sh            everything above that does not change files
set -euo pipefail
cd "$(dirname "$0")"

if command -v python3 >/dev/null 2>&1 && python3 -c "" >/dev/null 2>&1; then PY=python3; else PY=python; fi

use_venv() {
  if [ ! -d .venv ]; then
    echo "No .venv yet. Run ./check.sh setup first." >&2
    exit 1
  fi
  set +u
  if [ -f .venv/Scripts/activate ]; then source .venv/Scripts/activate; else source .venv/bin/activate; fi
  set -u
}

step() { printf '\n== %s ==\n' "$1"; }

setup() {
  if ! "$PY" -c "import sys; sys.exit(sys.version_info < (3, 11))"; then
    echo "Python 3.11 or newer is needed. Found: $("$PY" --version 2>&1)" >&2
    exit 1
  fi
  [ -d .venv ] || "$PY" -m venv .venv
  use_venv
  python -m pip install -q -r requirements.txt
  echo "Ready. Python: $(python --version)"
}

run_tests() { step "pytest"; python -m pytest -q "$@"; }
lint() { step "ruff lint"; ruff check .; }
format_check() { step "ruff format (check only)"; ruff format --check .; }

validate() {
  step "validate"
  local failed=0
  if [ -f .env ]; then
    local secret
    # Read it the way run.sh does, so quotes and "export" are handled the same.
    secret="$(set -a; eval "$(tr -d '\r' < .env)" >/dev/null 2>&1; printf '%s' "${JWT_SECRET:-}")"
    if [ "${#secret}" -lt 32 ]; then echo "FAIL .env: JWT_SECRET must be 32 characters or more"; failed=1
    else echo "ok   .env has a long enough JWT_SECRET"; fi
  else
    echo "FAIL .env missing: copy .env.example to .env and set JWT_SECRET"; failed=1
  fi
  local tracked
  tracked="$(git ls-files .env app.db out | grep -v '^\.env\.example$' || true)"
  if [ -n "$tracked" ]; then echo "FAIL tracked by git, must not be: $tracked"; failed=1
  else echo "ok   .env, app.db and out/ are not tracked by git"; fi
  if [ ! -f .env.example ]; then
    echo "FAIL .env.example is missing"; failed=1
  else
    local filled
    filled="$(grep -E '^[A-Z_]+=.+' .env.example | grep -vE '^(APP_URL|EMAIL_FROM)=' | cut -d= -f1 || true)"
    if [ -n "$filled" ]; then
      echo "FAIL .env.example must have empty values for: $filled"; failed=1
    else echo "ok   .env.example has names only"; fi
  fi
  if [ -f tests/test_contract.py ]; then
    python -m pytest -q tests/test_contract.py || failed=1
  else
    echo "skip tests/test_contract.py not merged yet"
  fi
  return "$failed"
}

web() {
  step "web lint and build"
  if [ ! -f web/package.json ]; then echo "skip web/ not created yet"; return 0; fi
  [ -d web/node_modules ] || npm --prefix web ci
  npm --prefix web run lint
  npm --prefix web run build
}

all() {
  use_venv
  local failed=()
  lint || failed+=(lint)
  format_check || echo "(format is advisory: run ./check.sh format to fix)"
  run_tests || failed+=(test)
  validate || failed+=(validate)
  web || failed+=(web)
  echo
  if [ ${#failed[@]} -eq 0 ]; then echo "All checks passed."
  else echo "Failed: ${failed[*]}"; exit 1; fi
}

cmd="${1:-all}"
[ $# -gt 0 ] && shift
case "$cmd" in
  setup) setup ;;
  test) use_venv; run_tests "$@" ;;
  lint) use_venv; lint ;;
  fix) use_venv; step "ruff lint with fixes"; ruff check --fix . ;;
  format) use_venv; step "ruff format"; ruff format . ;;
  validate) use_venv; validate ;;
  web) web ;;
  all) all ;;
  *) echo "Unknown command: $cmd. Use setup, test, lint, fix, format, validate, web or all." >&2; exit 1 ;;
esac
