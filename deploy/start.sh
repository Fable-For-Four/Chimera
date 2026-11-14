#!/usr/bin/env bash
set -euo pipefail

JWT_SECRET="${JWT_SECRET:-}"
if [ "${#JWT_SECRET}" -lt 32 ]; then
  echo "JWT_SECRET must be set and 32 characters or more." >&2
  exit 1
fi
if [ -z "${SEED_PASSWORD:-}" ]; then
  echo "SEED_PASSWORD must be set. The demo default is public in the README." >&2
  exit 1
fi

mkdir -p "$(dirname "${DB_PATH:-/app/app.db}")"
python -m api.seed

uvicorn api.main:app --host 127.0.0.1 --port 8000 &
npm --prefix web start -- -H 0.0.0.0 -p "${PORT:-3000}" &

wait -n
exit 1
