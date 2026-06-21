# Prompt 18 — Build the Backend Server

**Phase:** 6 (Dashboard Backend)
**Send to:** Coder

---

Build the full backend for the read-only mission control dashboard.

Create server.py with a ThreadingHTTPServer on 127.0.0.1:51763.

- Serve index.html on GET /
- Return live JSON snapshot on /api/snapshot
- Push SSE updates on /events every 5 seconds
- Wrap every data function in try/except so one failure never crashes the server

Wire up five data functions into the snapshot:

gateway_data() — reads gateway_state.json, returns gateway state, platform statuses, active agent count, uptime.

activity_data() — queries agent-logs.db for last 50 entries, per-agent stats (total, completed, failed, last task, last seen, model), overall totals, 7-day daily breakdown. Sort by created_at DESC, id DESC.

sessions_data() — queries state.db for session count, message count, token totals (input, output, cache), 25 most recent sessions. Timestamps in state.db are Unix float seconds — pass them through as-is.

vps_health() — CPU from two /proc/stat samples, RAM from /proc/meminfo, disk from os.statvfs. No subprocess calls.

cron_jobs() — reads /var/spool/cron/crontabs/root, /etc/crontab, /etc/cron.d/. Strip the extra username field in system files. Label each job "hermes" or "system" and convert schedule to plain English.

Add a personal operator task board backed by board.db — SQLite in the project folder (not Hermes's kanban.db which stays read-only). Python stdlib sqlite3 with read-write access. Schema:

  CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    priority TEXT DEFAULT 'medium',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT
  )

Pre-seed with 8 realistic personal tasks spread across all three statuses on first run.

Endpoints: GET /api/board (list all), POST /api/board (create), POST /api/board/update?id= (update fields), POST /api/board/delete?id= (delete by id).

Create start.sh launcher and confirm the server responds.

---

## What to Watch For
- server.py is the backbone of the entire dashboard — verify it runs without errors
- Test: `curl http://127.0.0.1:51763/api/snapshot` should return JSON
- All 5 data functions must be wrapped in try/except
- board.db is the ONLY writeable database — everything else is read-only
- Pre-seeded tasks should appear in the board
- start.sh should launch the server cleanly
