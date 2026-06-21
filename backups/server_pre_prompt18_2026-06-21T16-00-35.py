#!/usr/bin/env python3
"""
Hermes AgentOS — Mission Control Dashboard Backend
Read-only monitoring server on 127.0.0.1:51763
"""

import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = 51763

GATEWAY_STATE_PATH = os.path.expanduser("~/.hermes/gateway_state.json")
AGENT_LOGS_DB     = os.path.expanduser("~/.hermes/agent-logs.db")
STATE_DB          = os.path.expanduser("~/.hermes/state.db")
BOARD_DB          = os.path.join(os.path.dirname(os.path.abspath(__file__)), "board.db")

SSE_INTERVAL      = 5   # seconds between SSE pushes

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def now_iso():
    return datetime.now(timezone.utc).isoformat()


def read_file(path):
    try:
        with open(path, "r") as f:
            return f.read()
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Data functions — each wrapped in try/except so one failure never crashes
# ---------------------------------------------------------------------------
def gateway_data():
    """Read gateway_state.json and return parsed state."""
    try:
        raw = read_file(GATEWAY_STATE_PATH)
        if not raw:
            return {"error": "gateway_state.json not found or empty"}
        data = json.loads(raw)
        # Normalise uptime
        start = data.get("start_time", 0)
        uptime_seconds = 0
        if start and isinstance(start, (int, float)):
            # start_time in gateway_state.json may be a monotonic counter
            # or a Unix timestamp. Only compute delta if it looks like one.
            now_unix = time.time()
            if 1e9 < start < now_unix:
                uptime_seconds = int(now_unix - start)
            else:
                uptime_seconds = int(start)  # treat as raw seconds counter
        platforms = data.get("platforms", {})
        platform_statuses = {}
        for name, info in platforms.items():
            platform_statuses[name] = {
                "state": info.get("state", "unknown"),
                "error_code": info.get("error_code"),
                "error_message": info.get("error_message"),
                "updated_at": info.get("updated_at"),
            }
        return {
            "gateway_state": data.get("gateway_state", "unknown"),
            "pid": data.get("pid"),
            "active_agents": data.get("active_agents", 0),
            "uptime_seconds": uptime_seconds,
            "platforms": platform_statuses,
            "updated_at": data.get("updated_at"),
        }
    except Exception as e:
        return {"error": str(e)}


def activity_data():
    """Query agent-logs.db for recent activity and per-agent stats."""
    try:
        conn = sqlite3.connect(AGENT_LOGS_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Last 50 entries, newest first
        cur.execute("""
            SELECT id, agent_name, task_description, model_used, status, created_at
            FROM agent_logs
            ORDER BY created_at DESC, id DESC
            LIMIT 50
        """)
        recent = [dict(r) for r in cur.fetchall()]

        # Per-agent stats
        cur.execute("""
            SELECT
                agent_name,
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                MAX(created_at) AS last_seen
            FROM agent_logs
            GROUP BY agent_name
        """)
        agent_rows = [dict(r) for r in cur.fetchall()]

        # Last task per agent
        last_tasks = {}
        for agent in agent_rows:
            cur.execute("""
                SELECT task_description, model_used
                FROM agent_logs
                WHERE agent_name = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            """, (agent["agent_name"],))
            row = cur.fetchone()
            if row:
                last_tasks[agent["agent_name"]] = {"task": row[0], "model": row[1]}

        agents = {}
        for a in agent_rows:
            lt = last_tasks.get(a["agent_name"], {})
            agents[a["agent_name"]] = {
                "total": a["total"],
                "completed": a["completed"],
                "failed": a["failed"],
                "last_task": lt.get("task", ""),
                "last_seen": a["last_seen"],
                "model": lt.get("model", ""),
            }

        # Overall totals
        cur.execute("SELECT COUNT(*) FROM agent_logs")
        total_logs = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM agent_logs WHERE status = 'completed'")
        total_completed = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM agent_logs WHERE status = 'failed'")
        total_failed = cur.fetchone()[0]

        # 7-day daily breakdown
        cur.execute("""
            SELECT
                DATE(created_at) AS day,
                COUNT(*) AS count,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
            FROM agent_logs
            WHERE created_at >= DATETIME('now', '-7 days')
            GROUP BY day
            ORDER BY day ASC
        """)
        daily = [dict(r) for r in cur.fetchall()]

        conn.close()
        return {
            "recent": recent,
            "agents": agents,
            "totals": {
                "total": total_logs,
                "completed": total_completed,
                "failed": total_failed,
            },
            "daily": daily,
        }
    except Exception as e:
        return {"error": str(e)}


def sessions_data():
    """Query state.db for session/message/token stats."""
    try:
        conn = sqlite3.connect(STATE_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Counts
        cur.execute("SELECT COUNT(*) FROM sessions")
        session_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM messages")
        message_count = cur.fetchone()[0]

        # Token totals
        cur.execute("""
            SELECT
                COALESCE(SUM(input_tokens), 0)     AS input_tokens,
                COALESCE(SUM(output_tokens), 0)    AS output_tokens,
                COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens,
                COALESCE(SUM(cache_write_tokens), 0) AS cache_write_tokens
            FROM sessions
        """)
        row = cur.fetchone()
        tokens = {
            "input": row[0],
            "output": row[1],
            "cache_read": row[2],
            "cache_write": row[3],
        }

        # 25 most recent sessions (by started_at DESC)
        cur.execute("""
            SELECT id, source, model, started_at, ended_at, message_count,
                   input_tokens, output_tokens, cache_read_tokens,
                   title, archived
            FROM sessions
            ORDER BY started_at DESC
            LIMIT 25
        """)
        recent_sessions = [dict(r) for r in cur.fetchall()]

        conn.close()
        return {
            "session_count": session_count,
            "message_count": message_count,
            "tokens": tokens,
            "recent_sessions": recent_sessions,
        }
    except Exception as e:
        return {"error": str(e)}


def vps_health():
    """CPU, RAM, disk — no subprocess calls."""
    result = {}

    # --- CPU via /proc/stat ---
    try:
        def read_cpu():
            with open("/proc/stat") as f:
                line = f.readline()  # "cpu  ..."
            fields = line.split()[1:]
            return [int(x) for x in fields]

        t1 = read_cpu()
        time.sleep(0.1)
        t2 = read_cpu()

        idle1, idle2 = t1[3], t2[3]
        total1 = sum(t1)
        total2 = sum(t2)

        delta_total = total2 - total1
        delta_idle = idle2 - idle1
        delta_used = delta_total - delta_idle

        cpu_pct = round(delta_used / delta_total * 100, 1) if delta_total else 0.0
        result["cpu_percent"] = cpu_pct
    except Exception as e:
        result["cpu_percent"] = None
        result["cpu_error"] = str(e)

    # --- RAM via /proc/meminfo ---
    try:
        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                key = parts[0].rstrip(":")
                val = int(parts[1])
                mem[key] = val
        total = mem.get("MemTotal", 0)
        available = mem.get("MemAvailable", 0)
        used = total - available
        ram_pct = round(used / total * 100, 1) if total else 0.0
        result["ram"] = {
            "total_kb": total,
            "used_kb": used,
            "available_kb": available,
            "percent": ram_pct,
        }
    except Exception as e:
        result["ram"] = {"error": str(e)}

    # --- Disk via os.statvfs ---
    try:
        st = os.statvfs("/")
        total = st.f_blocks * st.f_frsize
        free = st.f_bavail * st.f_frsize
        used = total - free
        disk_pct = round(used / total * 100, 1) if total else 0.0
        result["disk"] = {
            "total_bytes": total,
            "used_bytes": used,
            "free_bytes": free,
            "percent": disk_pct,
        }
    except Exception as e:
        result["disk"] = {"error": str(e)}

    return result


def _schedule_to_english(schedule):
    """Convert a cron schedule string to plain English."""
    parts = schedule.strip().split()
    if len(parts) < 5:
        return schedule  # not a valid cron line

    minute, hour, dom, month, dow = parts[0], parts[1], parts[2], parts[3], parts[4]
    command = " ".join(parts[5:]) if len(parts) > 5 else ""

    # Build time description
    if minute == "*" and hour == "*":
        time_desc = "every minute"
    elif minute.startswith("*/"):
        interval = minute[2:]
        time_desc = f"every {interval} minutes"
    elif hour == "*":
        time_desc = f"every hour at minute {minute}"
    elif minute == "0" and hour == "*":
        time_desc = "every hour"
    else:
        try:
            h = int(hour)
            m = int(minute)
            ampm = "am" if h < 12 else "pm"
            h12 = h if 1 <= h <= 12 else (h - 12 if h > 12 else 12)
            time_desc = f"at {h12}:{m:02d} {ampm}"
        except (ValueError, TypeError):
            time_desc = f"at {hour}:{minute}"

    # Day of month
    if dom != "*" and dom.isdigit():
        d = int(dom)
        if 11 <= d <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(d % 10, "th")
        time_desc += f" on the {d}{suffix}"

    # Day of week
    dow_names = ["Sunday", "Monday", "Tuesday", "Wednesday",
                 "Thursday", "Friday", "Saturday"]
    if dow != "*" and dow.isdigit():
        idx = int(dow) % 7
        time_desc += f" on {dow_names[idx]}"

    # Month
    month_names = ["", "January", "February", "March", "April", "May", "June",
                   "July", "August", "September", "October", "November", "December"]
    if month != "*" and month.isdigit():
        m_idx = int(month)
        if 1 <= m_idx <= 12:
            time_desc += f" in {month_names[m_idx]}"

    # Special frequency labels
    if dow in ("0", "7") and dom == "*":
        time_desc += " (weekly)"
    if dom == "1" and month == "*" and dow == "*":
        time_desc += " (monthly)"

    desc = time_desc.strip()
    if command:
        desc += f" — {command[:80]}"
    return desc


def cron_jobs():
    """Parse system crontabs and return labelled, human-readable jobs."""
    jobs = []

    def parse_crontab(path, label, has_username=True):
        try:
            with open(path) as f:
                first = f.read(256)
        except FileNotFoundError:
            return
        except Exception as e:
            jobs.append({"source": path, "label": label, "error": str(e)})
            return
        # Skip non-crontab files (JSON, binary, etc.)
        if first.lstrip().startswith(("{", "[")):
            return
        try:
            with open(path) as f:
                lines = f.readlines()
        except Exception:
            return

        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Skip environment variable assignments
            if "=" in line and not re.match(r'^\d|^\*|^\*/', line):
                continue
            parts = line.split()
            if len(parts) < 6:
                continue
            # System crontabs have username as the 6th field (index 5)
            if has_username and len(parts) >= 6:
                schedule_parts = parts[:5]
                command = " ".join(parts[6:])  # skip username
            else:
                schedule_parts = parts[:5]
                command = " ".join(parts[5:])
            schedule = " ".join(schedule_parts)
            jobs.append({
                "source": path,
                "label": label,
                "schedule_raw": schedule,
                "schedule_english": _schedule_to_english(schedule),
                "command": command[:120],
            })

    # User crontab (no username field)
    parse_crontab("/var/spool/cron/crontabs/root", "system", has_username=False)

    # System crontab (has username field)
    parse_crontab("/etc/crontab", "system", has_username=True)

    # /etc/cron.d/* (each has username field)
    cron_d = "/etc/cron.d"
    try:
        for fname in sorted(os.listdir(cron_d)):
            fpath = os.path.join(cron_d, fname)
            if os.path.isfile(fpath):
                parse_crontab(fpath, "system", has_username=True)
    except Exception as e:
        jobs.append({"source": cron_d, "label": "system", "error": str(e)})

    # Note: Hermes-managed cron jobs live in ~/.hermes/cron/ as JSON
    # and are tracked via the Hermes CLI — not parsed here since they
    # aren't standard crontab format.

    return jobs


# ---------------------------------------------------------------------------
# Board DB — personal task board (separate from Hermes kanban.db)
# ---------------------------------------------------------------------------
def board_init():
    """Create board.db and seed with 8 tasks if empty."""
    conn = sqlite3.connect(BOARD_DB)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT
        )
    """)
    cur.execute("SELECT COUNT(*) FROM tasks")
    if cur.fetchone()[0] == 0:
        seed = [
            ("task-001", "Review gateway_state.json schema", "done", "high",
             "Verify all platform keys present", "2026-06-18T10:00:00+00:00"),
            ("task-002", "Wire up SSE endpoint on /events", "done", "high",
             "5-second interval, ThreadingHTTPServer", "2026-06-18T11:00:00+00:00"),
            ("task-003", "Build activity_data() from agent-logs.db", "in_progress", "high",
             "Per-agent stats + 7-day breakdown", "2026-06-19T08:00:00+00:00"),
            ("task-004", "Add VPS health module (CPU/RAM/disk)", "in_progress", "medium",
             "Read /proc/stat, /proc/meminfo, os.statvfs", "2026-06-19T09:00:00+00:00"),
            ("task-005", "Create board.db with CRUD endpoints", "pending", "medium",
             "GET/POST/POST update/POST delete", "2026-06-20T06:00:00+00:00"),
            ("task-006", "Write start.sh launcher script", "pending", "low",
             "Kill old, start new, log to file", "2026-06-20T07:00:00+00:00"),
            ("task-007", "Parse cron jobs from /etc/crontab and cron.d", "pending", "medium",
             "Strip username field, convert to English", "2026-06-19T14:00:00+00:00"),
            ("task-008", "Build frontend dashboard HTML/JS", "pending", "high",
             "Consume /api/snapshot + /events SSE", "2026-06-20T08:00:00+00:00"),
        ]
        for row in seed:
            cur.execute("""
                INSERT OR IGNORE INTO tasks (id, title, status, priority, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, row)
    conn.commit()
    conn.close()


def board_list():
    conn = sqlite3.connect(BOARD_DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks ORDER BY created_at ASC")
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def board_create(title, status, priority, notes):
    import uuid
    task_id = f"task-{uuid.uuid4().hex[:8]}"
    ts = now_iso()
    conn = sqlite3.connect(BOARD_DB)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO tasks (id, title, status, priority, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (task_id, title, status, priority, notes, ts))
    conn.commit()
    conn.close()
    return task_id


def board_update(task_id, fields):
    allowed = {"title", "status", "priority", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    updates["updated_at"] = now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]
    conn = sqlite3.connect(BOARD_DB)
    cur = conn.cursor()
    cur.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


def board_delete(task_id):
    conn = sqlite3.connect(BOARD_DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    changed = cur.rowcount > 0
    conn.close()
    return changed


# ---------------------------------------------------------------------------
# Snapshot builder
# ---------------------------------------------------------------------------
def build_snapshot():
    return {
        "timestamp": now_iso(),
        "gateway": gateway_data(),
        "activity": activity_data(),
        "sessions": sessions_data(),
        "vps": vps_health(),
        "cron": cron_jobs(),
    }


# ---------------------------------------------------------------------------
# SSE clients
# ---------------------------------------------------------------------------
sse_clients = []
sse_lock = threading.Lock()


def sse_broadcast(data):
    """Send data to all connected SSE clients."""
    dead = []
    with sse_lock:
        for i, (conn, thread) in enumerate(sse_clients):
            try:
                conn.wfile.write(f"data: {json.dumps(data)}\n\n".encode())
                conn.wfile.flush()
            except Exception:
                dead.append(i)
        for i in reversed(dead):
            sse_clients.pop(i)


def sse_pusher():
    """Background thread: push snapshot to SSE clients every N seconds."""
    while True:
        time.sleep(SSE_INTERVAL)
        try:
            snapshot = build_snapshot()
            sse_broadcast(snapshot)
        except Exception:
            pass  # never crash the pusher


# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    """Routes requests to the right handler."""

    def log_message(self, fmt, *args):
        # Suppress default stderr logging
        pass

    # ---- helpers ----
    def _send(self, code, body, content_type="application/json"):
        payload = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, code, obj):
        self._send(code, json.dumps(obj, default=str))

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def do_OPTIONS(self):
        self._send(200, "")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        # Serve index.html
        if path == "/" or path == "/index.html":
            html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.html")
            try:
                with open(html_path, "r") as f:
                    html = f.read()
                self._send(200, html, "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send_json(404, {"error": "index.html not found"})
            return

        # API snapshot
        if path == "/api/snapshot":
            self._send_json(200, build_snapshot())
            return

        # Board list
        if path == "/api/board":
            self._send_json(200, board_list())
            return

        # SSE endpoint
        if path == "/events":
            self._handle_sse()
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Create task
        if path == "/api/board":
            try:
                body = self._read_body()
                task_id = board_create(
                    title=body.get("title", "Untitled"),
                    status=body.get("status", "pending"),
                    priority=body.get("priority", "medium"),
                    notes=body.get("notes", ""),
                )
                self._send_json(201, {"id": task_id})
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        # Update task
        if path == "/api/board/update":
            qs = parse_qs(parsed.query)
            task_id = qs.get("id", [None])[0]
            if not task_id:
                self._send_json(400, {"error": "missing id"})
                return
            try:
                body = self._read_body()
                ok = board_update(task_id, body)
                if ok:
                    self._send_json(200, {"ok": True})
                else:
                    self._send_json(404, {"error": "task not found or no changes"})
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        # Delete task
        if path == "/api/board/delete":
            qs = parse_qs(parsed.query)
            task_id = qs.get("id", [None])[0]
            if not task_id:
                self._send_json(400, {"error": "missing id"})
                return
            try:
                ok = board_delete(task_id)
                if ok:
                    self._send_json(200, {"ok": True})
                else:
                    self._send_json(404, {"error": "task not found"})
            except Exception as e:
                self._send_json(400, {"error": str(e)})
            return

        self._send_json(404, {"error": "not found"})

    def _handle_sse(self):
        """Register this connection as an SSE client and stream updates."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # Send initial snapshot
        try:
            snap = json.dumps(build_snapshot(), default=str)
            self.wfile.write(f"data: {snap}\n\n".encode())
            self.wfile.flush()
        except Exception:
            return

        # Register client
        with sse_lock:
            sse_clients.append((self, threading.current_thread()))

        # Keep connection alive — block until client disconnects
        try:
            while True:
                time.sleep(30)
                # Send keepalive comment
                self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
        except Exception:
            pass
        finally:
            with sse_lock:
                sse_clients[:] = [(c, t) for c, t in sse_clients if c is not self]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    board_init()

    # Start SSE pusher thread
    pusher = threading.Thread(target=sse_pusher, daemon=True)
    pusher.start()

    server = ThreadingHTTPServer((LISTEN_HOST, LISTEN_PORT), Handler)
    print(f"Mission Control Dashboard running on http://{LISTEN_HOST}:{LISTEN_PORT}")
    print(f"  GET  /           → index.html")
    print(f"  GET  /api/snapshot → full JSON snapshot")
    print(f"  GET  /events     → SSE stream (5s updates)")
    print(f"  GET  /api/board  → list tasks")
    print(f"  POST /api/board  → create task")
    print(f"  POST /api/board/update?id= → update task")
    print(f"  POST /api/board/delete?id= → delete task")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
