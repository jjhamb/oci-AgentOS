#!/usr/bin/env bash
# start.sh — Launch the Mission Control Dashboard backend
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/server.log"
PID_FILE="${SCRIPT_DIR}/server.pid"

# Kill any existing instance
if [[ -f "$PID_FILE" ]]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo "Stopping previous instance (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PID_FILE"
fi

# Also kill anything on port 51763 as a safety net
if command -v fuser &>/dev/null; then
  fuser -k 51763/tcp 2>/dev/null || true
  sleep 0.5
fi

cd "$SCRIPT_DIR"
echo "Starting Mission Control Dashboard..."
echo "  URL:    http://127.0.0.1:51763"
echo "  Log:    $LOG_FILE"
echo "  PID:    $$"
echo ""

# Start server in background, capture PID
python3 server.py >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

sleep 1

# Verify it started
if kill -0 "$NEW_PID" 2>/dev/null; then
  echo "✓ Server running (PID $NEW_PID)"

  # Quick health check
  if curl -sf http://127.0.0.1:51763/api/snapshot >/dev/null 2>&1; then
    echo "✓ Health check passed — /api/snapshot responding"
  else
    echo "⚠ Server started but /api/snapshot not responding yet"
  fi
  echo ""
  echo "Endpoints:"
  echo "  http://127.0.0.1:51763/                    — Dashboard"
  echo "  http://127.0.0.1:51763/api/snapshot        — JSON snapshot"
  echo "  http://127.0.0.1:51763/api/agents          — Agent status (11 agents)"
  echo "  http://127.0.0.1:51763/api/kanban          — Kanban tasks (read-only)"
  echo "  http://127.0.0.1:51763/api/activity/live   — Live activity feed"
  echo "  http://127.0.0.1:51763/events              — SSE stream"
  echo "  http://127.0.0.1:51763/api/board           — Personal task board"
else
  echo "✗ Server failed to start. Check $LOG_FILE"
  cat "$LOG_FILE"
  exit 1
fi
