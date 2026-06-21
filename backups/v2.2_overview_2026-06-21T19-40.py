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
KANBAN_DB         = os.path.expanduser("~/.hermes/kanban.db")
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
def _pid_uptime(pid):
    """Get process uptime in seconds from /proc/[pid]/stat (starttime field)."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            stat_line = f.read()
        # Fields after comm may contain spaces; comm is in parens, split after last ')'
        after_comm = stat_line.rsplit(")", 2)[-1]
        fields = after_comm.split()
        # starttime is field index 19 after pid (0-indexed from after_comm = index 19-2=17)
        # Fields: state(0) ppid(1) pgrp(2) session(3) tty(4) tpgid(5) flags(6) minflt(7)
        #         cminflt(8) majflt(9) utime(10) stime(11) cutime(12) cstime(13)
        #         priority(14) nice(15) num_threads(16) itrealvalue(17) starttime(18)
        starttime_ticks = int(fields[18])
        clock_ticks = os.sysconf("SC_CLK_TCK")
        starttime_sec = starttime_ticks / clock_ticks
        # Get system boot time from /proc/stat btime
        with open("/proc/stat") as f:
            for line in f:
                if line.startswith("btime "):
                    boot_time = int(line.split()[1])
                    break
        process_start_unix = boot_time + starttime_sec
        uptime = int(time.time() - process_start_unix)
        return max(0, uptime)
    except Exception:
        return None


def gateway_data():
    """Read gateway_state.json and return parsed state."""
    try:
        raw = read_file(GATEWAY_STATE_PATH)
        if not raw:
            return {"error": "gateway_state.json not found or empty"}
        data = json.loads(raw)
        # Compute gateway uptime from actual process start time via /proc
        pid = data.get("pid")
        uptime_seconds = None
        if pid and isinstance(pid, int):
            uptime_seconds = _pid_uptime(pid)
        if uptime_seconds is None:
            # Fallback: try start_time if it looks like a valid Unix timestamp
            start = data.get("start_time", 0)
            if start and isinstance(start, (int, float)) and 1e9 < start < time.time():
                uptime_seconds = int(time.time() - start)
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

    # --- OS uptime via /proc/uptime ---
    try:
        with open("/proc/uptime") as f:
            uptime_str = f.readline().split()[0]
        result["os_uptime_seconds"] = int(float(uptime_str))
    except Exception as e:
        result["os_uptime_seconds"] = None
        result["os_uptime_error"] = str(e)

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
# Agents data — 11 agents with status from agent-logs.db + gateway
# ---------------------------------------------------------------------------
# Agent registry: name → {role, profile, discord_channel, accent}
AGENT_REGISTRY = {
    "orchestrator": {
        "role": "Controller", "profile": "default",
        "channel": "#orchestrator-main", "accent": "agent-orchestrator",
        "emoji": "⚡", "is_infra": False,
    },
    "analyst": {
        "role": "Research & Intel", "profile": "default",
        "channel": "#analyst-briefs", "accent": "agent-analyst",
        "emoji": "🔍", "is_infra": False,
    },
    "writer": {
        "role": "Content & Copy", "profile": "default",
        "channel": "#writer-scripts", "accent": "agent-writer",
        "emoji": "✍️", "is_infra": False,
    },
    "marketer": {
        "role": "Strategy & Growth", "profile": "default",
        "channel": "#marketer-marketing", "accent": "agent-marketer",
        "emoji": "📣", "is_infra": False,
    },
    "coder": {
        "role": "Dev & Automation", "profile": "default",
        "channel": "#coder-build", "accent": "agent-coder",
        "emoji": "💻", "is_infra": False,
    },
    "infra": {
        "role": "Infrastructure", "profile": "infra",
        "channel": "#infra-ops", "accent": "brand-gold",
        "emoji": "🏗️", "is_infra": True,
    },
    "executor": {
        "role": "Runbook Execution", "profile": "executor",
        "channel": None, "accent": "brand-amber",
        "emoji": "⚙️", "is_infra": True,
    },
    "sentinel": {
        "role": "Monitoring & Alerts", "profile": "sentinel",
        "channel": None, "accent": "brand-red",
        "emoji": "🛡️", "is_infra": True,
    },
    "web": {
        "role": "Web & SSL", "profile": "web",
        "channel": None, "accent": "brand-cyan",
        "emoji": "🌐", "is_infra": True,
    },
    "publisher": {
        "role": "Deployment", "profile": "publisher",
        "channel": None, "accent": "brand-mint",
        "emoji": "🚀", "is_infra": True,
    },
    "reviewer": {
        "role": "QA & Validation", "profile": "reviewer",
        "channel": None, "accent": "brand-violet",
        "emoji": "✅", "is_infra": True,
    },
}


def agents_data():
    """Return status for all 11 agents based on agent-logs.db activity."""
    try:
        conn = sqlite3.connect(AGENT_LOGS_DB)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Per-agent latest activity
        cur.execute("""
            SELECT agent_name,
                   COUNT(*) AS total,
                   SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed,
                   SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                   MAX(created_at) AS last_seen
            FROM agent_logs
            GROUP BY agent_name
        """)
        db_stats = {r["agent_name"]: dict(r) for r in cur.fetchall()}

        # Last task + model per agent
        last_info = {}
        for name in db_stats:
            cur.execute("""
                SELECT task_description, model_used
                FROM agent_logs
                WHERE agent_name = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
            """, (name,))
            row = cur.fetchone()
            if row:
                last_info[name] = {"task": row[0], "model": row[1]}

        conn.close()

        # Build agent list
        agents = []
        for name, meta in AGENT_REGISTRY.items():
            stats = db_stats.get(name, {})
            li = last_info.get(name, {})
            total = stats.get("total", 0)
            last_seen = stats.get("last_seen", "")

            # Determine status
            if total == 0:
                status = "dormant"
            elif last_seen:
                # Check if last activity is within 1 hour
                try:
                    from datetime import datetime, timezone, timedelta
                    last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) - last_dt < timedelta(hours=1):
                        status = "active"
                    else:
                        status = "idle"
                except Exception:
                    status = "idle"
            else:
                status = "dormant"

            agents.append({
                "name": name,
                "role": meta["role"],
                "profile": meta["profile"],
                "channel": meta["channel"],
                "accent": meta["accent"],
                "emoji": meta["emoji"],
                "is_infra": meta["is_infra"],
                "status": status,
                "total_logs": total,
                "completed": stats.get("completed", 0),
                "failed": stats.get("failed", 0),
                "last_task": li.get("task", ""),
                "model": li.get("model", ""),
                "last_seen": last_seen,
            })

        return {
            "agents": agents,
            "total": len(agents),
            "active": sum(1 for a in agents if a["status"] == "active"),
            "idle": sum(1 for a in agents if a["status"] == "idle"),
            "dormant": sum(1 for a in agents if a["status"] == "dormant"),
        }
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Kanban data — read-only from Hermes kanban.db
# ---------------------------------------------------------------------------
def kanban_data():
    """Read tasks from Hermes kanban.db (read-only)."""
    try:
        conn = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
        conn.execute("PRAGMA query_only=1")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            SELECT id, title, body, assignee, status, priority,
                   created_at, started_at, completed_at, last_heartbeat_at,
                   workspace_kind, tenant
            FROM tasks
            WHERE status != 'archived'
            ORDER BY created_at DESC
            LIMIT 100
        """)
        tasks = []
        for r in cur.fetchall():
            t = dict(r)
            # Convert Unix integer timestamps to ISO
            for field in ("created_at", "started_at", "completed_at", "last_heartbeat_at"):
                val = t.get(field)
                if val and isinstance(val, (int, float)):
                    try:
                        dt = datetime.fromtimestamp(val, tz=timezone.utc)
                        t[field] = dt.isoformat()
                    except (OSError, ValueError, OverflowError):
                        pass
            tasks.append(t)

        # Status counts
        cur.execute("""
            SELECT status, COUNT(*) as count
            FROM tasks
            WHERE status != 'archived'
            GROUP BY status
        """)
        status_counts = {r["status"]: r["count"] for r in cur.fetchall()}

        conn.close()
        return {
            "tasks": tasks,
            "total": len(tasks),
            "status_counts": status_counts,
        }
    except Exception as e:
        return {"error": str(e)}


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
        "agents": agents_data(),
        "kanban": kanban_data(),
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

        # Serve standalone tab snapshots from tabs/ directory
        if path.startswith("/tabs/") and path.endswith(".html"):
            tab_name = os.path.basename(path)
            tab_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tabs", tab_name)
            try:
                with open(tab_path, "r") as f:
                    html = f.read()
                self._send(200, html, "text/html; charset=utf-8")
            except FileNotFoundError:
                self._send_json(404, {"error": f"tab {tab_name} not found"})
            return

        # API snapshot
        if path == "/api/snapshot":
            self._send_json(200, build_snapshot())
            return

        # Board list
        if path == "/api/board":
            self._send_json(200, board_list())
            return

        # Agents endpoint
        if path == "/api/agents":
            self._send_json(200, agents_data())
            return

        # Kanban endpoint (read-only from Hermes kanban.db)
        if path == "/api/kanban":
            self._send_json(200, kanban_data())
            return

        # Live activity feed (last N entries)
        if path == "/api/activity/live":
            qs = parse_qs(parsed.query)
            limit = int(qs.get("limit", [20])[0])
            limit = min(max(limit, 1), 100)  # clamp 1-100
            try:
                conn = sqlite3.connect(AGENT_LOGS_DB)
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, agent_name, task_description, model_used, status, created_at
                    FROM agent_logs
                    ORDER BY created_at DESC, id DESC
                    LIMIT ?
                """, (limit,))
                rows = [dict(r) for r in cur.fetchall()]
                conn.close()
                self._send_json(200, {"entries": rows, "count": len(rows)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
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
