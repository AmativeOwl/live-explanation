#!/usr/bin/env bash
set -e

echo "Building extension..."
(cd frontend && npm run build:extension)

echo "Starting backend (Ctrl+C to stop)..."
cd backend && uv run uvicorn main:app --reload --port 8000
