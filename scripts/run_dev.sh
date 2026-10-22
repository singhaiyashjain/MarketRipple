#!/usr/bin/env bash
# Run backend + frontend together (Linux/macOS/Git-Bash). Windows: run the two commands in README separately.
set -e
(cd backend && uvicorn app.main:app --reload --port 8000) &
(cd frontend && npm run dev) &
wait
