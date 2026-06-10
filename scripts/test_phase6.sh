#!/bin/bash
# Phase 6 smoke test: starts the backend + frontend dev servers (if not
# already running), runs the eval suite, and prints where to find the UI.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BACKEND_LOG="/tmp/codesheriff_uvicorn.log"
FRONTEND_LOG="/tmp/codesheriff_vite.log"

# 1. Backend
if curl -s -o /dev/null http://localhost:8000/health; then
  echo "Backend already running on http://localhost:8000"
else
  echo "Starting backend (uvicorn) -- logs: $BACKEND_LOG"
  nohup .venv/bin/uvicorn backend.main:app --port 8000 > "$BACKEND_LOG" 2>&1 &
  disown
  for i in $(seq 1 30); do
    if curl -s -o /dev/null http://localhost:8000/health; then
      break
    fi
    sleep 1
  done
fi

# 2. Frontend
if curl -s -o /dev/null http://localhost:5173; then
  echo "Frontend already running on http://localhost:5173"
else
  echo "Starting frontend (vite) -- logs: $FRONTEND_LOG"
  (cd frontend && nohup npm run dev > "$FRONTEND_LOG" 2>&1 &)
  disown
  sleep 3
fi

# 3. Run evals
echo
echo "Running eval suite..."
.venv/bin/python evals/eval_runner.py

echo
echo "Frontend running at http://localhost:5173"
