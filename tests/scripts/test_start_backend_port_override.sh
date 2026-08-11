#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PORT=18001
LOG="$(mktemp)"

API_PORT="$PORT" "$ROOT/scripts/start-backend.sh" >"$LOG" 2>&1 &
PID=$!
trap 'kill "$PID" 2>/dev/null || true; rm -f "$LOG"' EXIT

for _ in {1..50}; do
    if curl -fsS "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then
        exit 0
    fi
    if ! kill -0 "$PID" 2>/dev/null; then
        cat "$LOG" >&2
        exit 1
    fi
    sleep 0.1
done

cat "$LOG" >&2
exit 1
