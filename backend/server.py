#!/usr/bin/env python3
"""
Hermes AgentOS — Mission Control Dashboard Backend
Read-only monitoring server on 127.0.0.1:51763
"""

import base64
import json
import os
import re
import sqlite3
import subprocess
import threading
import time
from datetime import datetime, timezone, timedelta
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

# Orchestrator activity tracking — the orchestrator IS the dashboard operator,
# so any time the server is serving requests, the orchestrator is "active".
# Updated on every /api/agents call (which the dashboard polls via SSE).
_orchestrator_last_active = time.time()
_orchestrator_lock = threading.Lock()

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
    """Query agent-logs.db for recent activity and per-agent stats.
    Also injects synthetic 'running' entries from kanban tasks so the
    Live Activity log and Overview feed show real-time kanban work."""
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

        conn.close()

        # Inject synthetic activity entries from kanban tasks
        # This makes the Live Activity log and Overview feed show real-time work
        try:
            kconn = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
            kconn.execute("PRAGMA query_only=1")
            kconn.row_factory = sqlite3.Row
            kcur = kconn.cursor()

            # Running tasks → in_progress entries
            kcur.execute("""
                SELECT assignee, title, body, started_at
                FROM tasks
                WHERE status = 'running' AND assignee IS NOT NULL
                ORDER BY started_at DESC
            """)
            for r in kcur.fetchall():
                # Map default-profile tasks to specialist agent for display
                agent_name = r["assignee"]
                if agent_name == "default":
                    agent_name = _map_default_task_to_specialist(r["title"], r.get("body", ""))
                synth_desc = f"running: {r['title']}"
                already = any(
                    e["agent_name"] == agent_name and e["task_description"] == synth_desc
                    for e in recent
                )
                if not already:
                    synth_entry = {
                        "id": f"kanban-{agent_name}-running",
                        "agent_name": agent_name,
                        "task_description": synth_desc,
                        "model_used": "",
                        "status": "in_progress",
                        "created_at": r["started_at"] if isinstance(r["started_at"], str) else (
                            datetime.fromtimestamp(r["started_at"], tz=timezone.utc).isoformat()
                            if r["started_at"] else datetime.now(timezone.utc).isoformat()
                        ),
                    }
                    recent.insert(0, synth_entry)

            # Recently completed tasks (last 2 hours) → completed entries
            # These persist so the activity log shows the full lifecycle
            kcur.execute("""
                SELECT assignee, title, body, completed_at, started_at
                FROM tasks
                WHERE status = 'done' AND assignee IS NOT NULL
                  AND completed_at IS NOT NULL
                ORDER BY completed_at DESC
                LIMIT 20
            """)
            for r in kcur.fetchall():
                # Map default-profile tasks to specialist agent for display
                agent_name = r["assignee"]
                if agent_name == "default":
                    agent_name = _map_default_task_to_specialist(r["title"], r.get("body", ""))

                # Only include tasks completed in the last 2 hours
                try:
                    completed_ts = r["completed_at"]
                    if isinstance(completed_ts, (int, float)):
                        completed_dt = datetime.fromtimestamp(completed_ts, tz=timezone.utc)
                    else:
                        completed_dt = datetime.fromisoformat(str(completed_ts).replace("Z", "+00:00"))
                        if completed_dt.tzinfo is None:
                            completed_dt = completed_dt.replace(tzinfo=timezone.utc)
                    age = datetime.now(timezone.utc) - completed_dt
                    if age > timedelta(hours=2):
                        continue
                except Exception:
                    continue

                synth_desc = f"completed: {r['title']}"
                already = any(
                    e["agent_name"] == agent_name and e["task_description"] == synth_desc
                    for e in recent
                )
                if not already:
                    synth_entry = {
                        "id": f"kanban-{agent_name}-done-{r['completed_at']}",
                        "agent_name": agent_name,
                        "task_description": synth_desc,
                        "model_used": "",
                        "status": "completed",
                        "created_at": r["completed_at"] if isinstance(r["completed_at"], str) else (
                            datetime.fromtimestamp(r["completed_at"], tz=timezone.utc).isoformat()
                            if r["completed_at"] else datetime.now(timezone.utc).isoformat()
                        ),
                    }
                    recent.insert(0, synth_entry)

            kconn.close()

        except Exception:
            pass

        # Sort all entries by created_at DESC so kanban-injected entries
        # are properly interleaved with agent-logs entries in time order
        def _parse_ts(ts):
            if not ts:
                return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(ts, str):
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt
                except Exception:
                    return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(ts, (int, float)):
                try:
                    return datetime.fromtimestamp(ts, tz=timezone.utc)
                except Exception:
                    return datetime.min.replace(tzinfo=timezone.utc)
            return datetime.min.replace(tzinfo=timezone.utc)

        recent.sort(key=lambda e: _parse_ts(e.get("created_at")), reverse=True)

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

        # Overall totals (reconnect — conn was closed above)
        conn2 = sqlite3.connect(AGENT_LOGS_DB)
        conn2.row_factory = sqlite3.Row
        cur2 = conn2.cursor()
        cur2.execute("SELECT COUNT(*) FROM agent_logs")
        total_logs = cur2.fetchone()[0]
        cur2.execute("SELECT COUNT(*) FROM agent_logs WHERE status = 'completed'")
        total_completed = cur2.fetchone()[0]
        cur2.execute("SELECT COUNT(*) FROM agent_logs WHERE status = 'failed'")
        total_failed = cur2.fetchone()[0]

        # 7-day daily breakdown
        cur2.execute("""
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
        daily = [dict(r) for r in cur2.fetchall()]

        conn2.close()
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

    return jobs


def cron_data():
    """Return combined system + Hermes cron jobs for the API."""
    jobs = cron_jobs()

    # Parse Hermes cron jobs from ~/.hermes/cron/jobs.json
    hermes_cron_path = os.path.expanduser("~/.hermes/cron/jobs.json")
    try:
        with open(hermes_cron_path) as f:
            hermes_data = json.load(f)
    except Exception:
        hermes_data = {"jobs": []}

    for j in hermes_data.get("jobs", []):
        schedule = j.get("schedule", {})
        if schedule.get("kind") == "interval":
            mins = schedule.get("minutes", 0)
            display = schedule.get("display", f"every {mins}m")
            schedule_english = f"Every {mins} minutes"
        elif schedule.get("kind") == "cron":
            expr = schedule.get("expr", "")
            display = schedule.get("display", expr)
            schedule_english = _schedule_to_english(expr)
        else:
            display = schedule.get("display", "unknown")
            schedule_english = ""

        prompt_text = j.get("prompt", "")
        # Strip the "You are the X profile..." prefix for display
        if " " in prompt_text:
            # Use the first sentence or first 80 chars
            short_cmd = prompt_text[:120]
        else:
            short_cmd = prompt_text[:120]

        jobs.append({
            "source": "hermes",
            "label": "hermes",
            "name": j.get("name", "Untitled"),
            "schedule_raw": display,
            "schedule_english": schedule_english,
            "command": short_cmd,
            "enabled": j.get("enabled", True),
            "last_status": j.get("last_status"),
            "owner": "hermes",
        })

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


def _map_default_task_to_specialist(title, body):
    """Map a kanban task with assignee='default' to a specialist agent.
    
    When orchestrator creates tasks in single-profile mode, all tasks use
    assignee='default'. The specialist role is determined by keywords in
    the task title/body.
    
    Returns the specialist agent name (e.g., 'analyst') or 'orchestrator'
    if no specialist keyword matches.
    """
    text = f"{title} {body}".lower()

    # Specialist role keywords (order matters — first match wins)
    # More specific agents listed BEFORE generic keywords that could match multiple
    specialist_keywords = [
        # Primary specialists (4)
        ("analyst", ["analyst", "research", "analysis", "market intel", "brief", "study", "trends"]),
        ("writer", ["writer", "blog", "content", "copy", "script", "article", "draft"]),
        ("coder", ["coder", "debug", "deploy", "implement", "ec2", "apache", "ses"]),
        ("marketer", ["marketer", "campaign", "promotion", "social media", "brand", "growth"]),
        # Infra workers (5) — specific keywords first
        ("infra", ["infra", "infrastructure", "server load", "uptime", "disk usage", "memory usage"]),
        ("executor", ["executor", "list files", "directory listing", "run command"]),
        ("sentinel", ["sentinel", "port status", "port check", "security scan"]),
        ("web", ["web", "website", "dns", "domain", "french.jhamb", "reachable"]),
        ("publisher", ["publisher", "publish", "report", "working directory"]),
        ("reviewer", ["reviewer", "review", "validate", "qa", "quality check"]),
        # Orchestrator last (catch-all for coordination tasks)
        ("orchestrator", ["orchestrator", "orchestration", "count tasks", "pipeline", "verify"]),
    ]
    for agent_name, keywords in specialist_keywords:
        for kw in keywords:
            if kw in text:
                return agent_name

    # Default: orchestrator handles it directly
    return "orchestrator"


def agents_data():
    """Return status for all 11 agents based on agent-logs.db activity + kanban."""
    global _orchestrator_last_active
    # Update orchestrator activity — the dashboard is being polled, so the
    # orchestrator (the operator viewing this dashboard) is engaged.
    try:
        with _orchestrator_lock:
            _orchestrator_last_active = time.time()
    except Exception:
        pass

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

        # Check Discord session activity per agent (via state.db)
        # Maps agent names to their Discord channels
        agent_discord_channels = {
            "analyst": "1517738142738808932",
            "writer": "1517738145620168799",
            "marketer": "1517738148824875169",
            "coder": "1517738152150827098",
            "orchestrator": "1518146157833097216",
            "infra": "1518146234530005052",
        }
        discord_session_active = {}  # agent_name → True if recent Discord activity
        try:
            sconn = sqlite3.connect(STATE_DB)
            sconn.row_factory = sqlite3.Row
            scur = sconn.cursor()
            # Get recent Discord sessions (within 5 min)
            now_ts = time.time()
            five_min_ago = now_ts - 300
            scur.execute("""
                SELECT id, source, started_at, message_count, title, user_id
                FROM sessions
                WHERE source = 'discord'
                  AND message_count > 0
                  AND started_at > ?
                ORDER BY started_at DESC
                LIMIT 20
            """, (five_min_ago,))
            recent_discord_sessions = scur.fetchall()
            
            # Check if any recent Discord session matches an agent's channel
            # Since we can't directly map session → channel, we use a heuristic:
            # If there's a recent Discord session with activity, check if the
            # session title or ID pattern matches known agent names
            for r in recent_discord_sessions:
                session_title = (r["title"] or "").lower()
                for agent_name, channel_id in agent_discord_channels.items():
                    if agent_name not in discord_session_active:
                        if agent_name in session_title or channel_id in str(r["id"] or ""):
                            discord_session_active[agent_name] = True
            
            # Also check: any Discord session with recent messages (within 5 min)
            # This catches direct agent interactions even without title matching
            if recent_discord_sessions:
                # If there are recent Discord sessions, mark agents whose channels
                # are in the active session list as potentially active
                for r in recent_discord_sessions:
                    # Check messages in this session for recent activity
                    scur.execute("""
                        SELECT COUNT(*) as msg_count, MAX(timestamp) as last_msg
                        FROM messages
                        WHERE session_id = ?
                          AND timestamp > ?
                        LIMIT 1
                    """, (r["id"], five_min_ago))
                    msg_row = scur.fetchone()
                    if msg_row and msg_row["msg_count"] > 0:
                        # This session has recent messages — try to match to agent
                        session_title = (r["title"] or "").lower()
                        for agent_name, channel_id in agent_discord_channels.items():
                            if agent_name not in discord_session_active:
                                if agent_name in session_title:
                                    discord_session_active[agent_name] = True
            
            sconn.close()
        except Exception:
            pass  # state.db may not be accessible

        # Check kanban for running tasks + task titles per agent
        kanban_running = {}
        kanban_task_titles = {}
        # Track synthetic activity entries generated for default-profile tasks
        # so the orchestrator's kanban delegation logic can attribute work to specialists
        kanban_specialist_active = set()  # specialist agents with non-done default-profile tasks (ready or running)
        kanban_specialist_ready = set()   # specialist agents with ready (not yet started) tasks
        try:
            kconn = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
            kconn.execute("PRAGMA query_only=1")
            kconn.row_factory = sqlite3.Row
            kcur = kconn.cursor()
            # Get ALL non-archived tasks including ready/running/done (need body for default→specialist mapping)
            kcur.execute("""
                SELECT assignee, title, body, created_at, started_at, completed_at, status
                FROM tasks
                WHERE status IN ('ready', 'running', 'done', 'blocked')
                  AND assignee IS NOT NULL
                ORDER BY created_at DESC
            """)
            all_tasks = [dict(r) for r in kcur.fetchall()]
            kconn.close()

            # Remap 'default' assignee to specialist agent based on task title/body
            for t in all_tasks:
                assignee = t["assignee"]
                if assignee == "default":
                    specialist = _map_default_task_to_specialist(t["title"], t.get("body", ""))
                    assignee = specialist
                    # Track ALL non-done tasks (ready + running) for pulsating glow
                    has_started = t.get("started_at") is not None
                    has_completed = t.get("completed_at") is not None
                    is_completed = has_completed
                    if not is_completed:
                        kanban_specialist_active.add(specialist)
                        if not has_started:
                            kanban_specialist_ready.add(specialist)

                # A task is "running" if it has started_at but no completed_at
                # A task is "done" if it has completed_at
                has_started = t.get("started_at") is not None
                has_completed = t.get("completed_at") is not None
                is_running = has_started and not has_completed

                # For running tasks: count and title
                if is_running:
                    kanban_running[assignee] = kanban_running.get(assignee, 0) + 1
                    if assignee not in kanban_task_titles:
                        kanban_task_titles[assignee] = t["title"]

            # For recently completed tasks: add titles (within 2 hours)
            for t in all_tasks:
                assignee = t["assignee"]
                if assignee == "default":
                    specialist = _map_default_task_to_specialist(t["title"], t.get("body", ""))
                    assignee = specialist

                completed_ts = t.get("completed_at")
                if not completed_ts:
                    continue
                if assignee in kanban_task_titles:
                    continue  # already have a running task title
                try:
                    if isinstance(completed_ts, (int, float)):
                        completed_dt = datetime.fromtimestamp(completed_ts, tz=timezone.utc)
                    else:
                        completed_dt = datetime.fromisoformat(str(completed_ts).replace("Z", "+00:00"))
                        if completed_dt.tzinfo is None:
                            completed_dt = completed_dt.replace(tzinfo=timezone.utc)
                    age = datetime.now(timezone.utc) - completed_dt
                    if age > timedelta(hours=2):
                        continue
                except Exception:
                    continue
                kanban_task_titles[assignee] = t["title"]

        except Exception:
            pass  # kanban DB may not exist yet

        # Build agent list
        agents = []
        # Track which agents are pulsating (for orchestrator delegation glow)
        pulsating_agents = set()

        for name, meta in AGENT_REGISTRY.items():
            stats = db_stats.get(name, {})
            li = last_info.get(name, {})
            total = stats.get("total", 0)
            last_seen = stats.get("last_seen", "")

            # Determine status
            # Three-tier model:
            #   pulsating = task on kanban not yet done (ready/running) — glow animation ON
            #   active    = task just completed (≤2min ago) — solid glow, no pulse
            #   idle      = nothing for >2min — dim/flat
            #
            # Orchestrator:
            #   pulsating = any tile pulsating, OR activity within 2min on default channels
            #   active    = all tasks done, <10min since last activity
            #   idle      = nothing for >10min
            if name == "orchestrator":
                # Orchestrator: pulsating if any tile is pulsating OR recent activity
                # active if all done but <10min, idle if >10min
                orch_pulsating = False
                orch_active = False

                # Pulsating if any specialist tile is pulsating (kanban tasks in flight)
                if kanban_specialist_active:
                    orch_pulsating = True

                # Also pulsating if any specialist just completed (within 2 min grace)
                # This keeps orchestrator in sync with specialist lifecycle
                if not orch_pulsating:
                    for spec_name in AGENT_REGISTRY:
                        if spec_name == 'orchestrator':
                            continue
                        spec = None
                        for a in agents:
                            if a['name'] == spec_name:
                                spec = a
                                break
                        if spec and spec.get('status') == 'active':
                            orch_pulsating = True
                            break

                # Also check: any non-done kanban tasks assigned to orchestrator/infra directly
                if not orch_pulsating:
                    try:
                        kconn2 = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
                        kconn2.execute("PRAGMA query_only=1")
                        kconn2.row_factory = sqlite3.Row
                        kcur2 = kconn2.cursor()
                        kcur2.execute("""
                            SELECT COUNT(*) as cnt
                            FROM tasks
                            WHERE status NOT IN ('done', 'archived')
                              AND assignee IN ('orchestrator', 'infra')
                        """)
                        row = kcur2.fetchone()
                        if row and row["cnt"] > 0:
                            orch_pulsating = True
                        kconn2.close()
                    except Exception:
                        pass

                # Also pulsating if recent activity on default channels (<2min)
                if not orch_pulsating and last_seen:
                    try:
                        last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                        if last_dt.tzinfo is None:
                            last_dt = last_dt.replace(tzinfo=timezone.utc)
                        age = datetime.now(timezone.utc) - last_dt
                        if age < timedelta(minutes=2):
                            orch_pulsating = True
                    except Exception:
                        pass

                # Discord session activity also triggers pulsating
                if not orch_pulsating and discord_session_active.get(name, False):
                    orch_pulsating = True

                if orch_pulsating:
                    status = "pulsating"
                    pulsating_agents.add(name)
                else:
                    # All done — check how long since last activity
                    try:
                        last_activity_ts = None
                        try:
                            kconn2 = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
                            kconn2.execute("PRAGMA query_only=1")
                            kconn2.row_factory = sqlite3.Row
                            kcur2 = kconn2.cursor()
                            kcur2.execute("""
                                SELECT MAX(completed_at) as max_completed
                                FROM tasks
                                WHERE status = 'done'
                                  AND assignee IN ('orchestrator', 'infra')
                                  AND completed_at IS NOT NULL
                            """)
                            row2 = kcur2.fetchone()
                            if row2 and row2["max_completed"]:
                                ct = row2["max_completed"]
                                if isinstance(ct, (int, float)):
                                    last_activity_ts = datetime.fromtimestamp(ct, tz=timezone.utc)
                                else:
                                    last_activity_ts = datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
                            kconn2.close()
                        except Exception:
                            pass

                        # Use whichever is more recent: last_seen or last task completion
                        last_dt = None
                        if last_seen:
                            try:
                                last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                                if last_dt.tzinfo is None:
                                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                            except Exception:
                                pass
                        if last_activity_ts and (last_dt is None or last_activity_ts > last_dt):
                            last_dt = last_activity_ts

                        # Orchestrator IS the dashboard operator — use server's own
                        # activity timestamp (updated on every /api/agents SSE poll)
                        # This is the most reliable signal that someone is actively
                        # using the dashboard (and thus the orchestrator is engaged).
                        try:
                            with _orchestrator_lock:
                                orch_age = time.time() - _orchestrator_last_active
                            if orch_age < 600:  # 10 min window
                                last_dt = datetime.fromtimestamp(
                                    _orchestrator_last_active, tz=timezone.utc
                                )
                        except Exception:
                            pass

                        if last_dt:
                            age = datetime.now(timezone.utc) - last_dt
                            if age < timedelta(minutes=10):
                                status = "active"
                            else:
                                status = "idle"
                        else:
                            status = "idle"
                    except Exception:
                        status = "idle"

            else:
                # Specialist agents (including infra's workers):
                # pulsating = has a kanban task that is not done (ready/running)
                # active = most recent task completed within 2 min
                # idle = nothing for >2 min

                is_pulsating = False
                has_recent_completion = False

                # Check if this agent has a running kanban task
                if kanban_running.get(name, 0) > 0:
                    is_pulsating = True

                # Also check default-profile tasks remapped to this specialist
                if not is_pulsating and name in kanban_specialist_active:
                    is_pulsating = True

                if is_pulsating:
                    status = "pulsating"
                    pulsating_agents.add(name)
                else:
                    # Check if any task completed within last 2 min
                    # Need to check direct assignee tasks; for 'default' tasks we map by title
                    try:
                        kconn3 = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
                        kconn3.execute("PRAGMA query_only=1")
                        kconn3.row_factory = sqlite3.Row
                        kcur3 = kconn3.cursor()
                        # First: check direct assignee
                        kcur3.execute("""
                            SELECT MAX(completed_at) as max_completed
                            FROM tasks
                            WHERE status = 'done'
                              AND assignee = ?
                              AND completed_at IS NOT NULL
                        """, (name,))
                        row3 = kcur3.fetchone()
                        max_ct = None
                        if row3 and row3["max_completed"]:
                            max_ct = row3["max_completed"]
                        # Second: check default-assignee tasks that map to this specialist
                        kcur3.execute("""
                            SELECT id, title, completed_at
                            FROM tasks
                            WHERE status = 'done'
                              AND assignee = 'default'
                              AND completed_at IS NOT NULL
                            ORDER BY completed_at DESC LIMIT 5
                        """)
                        for r in kcur3.fetchall():
                            specialist = _map_default_task_to_specialist(r["title"], "")
                            if specialist == name:
                                if max_ct is None or r["completed_at"] > max_ct:
                                    max_ct = r["completed_at"]
                                break  # most recent matching task
                        kconn3.close()
                        if max_ct:
                            ct = max_ct
                            if isinstance(ct, (int, float)):
                                completed_dt = datetime.fromtimestamp(ct, tz=timezone.utc)
                            else:
                                completed_dt = datetime.fromisoformat(str(ct).replace("Z", "+00:00"))
                                if completed_dt.tzinfo is None:
                                    completed_dt = completed_dt.replace(tzinfo=timezone.utc)
                            age = datetime.now(timezone.utc) - completed_dt
                            if age < timedelta(minutes=2):
                                has_recent_completion = True
                    except Exception:
                        pass

                    # Also check last_seen within 2 min as fallback for activity
                    if not has_recent_completion and last_seen:
                        try:
                            last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                            if last_dt.tzinfo is None:
                                last_dt = last_dt.replace(tzinfo=timezone.utc)
                            age = datetime.now(timezone.utc) - last_dt
                            if age < timedelta(minutes=2):
                                has_recent_completion = True
                        except Exception:
                            pass

                    if has_recent_completion:
                        status = "active"
                    elif total == 0:
                        status = "dormant"
                    elif discord_session_active.get(name, False):
                        status = "active"
                    else:
                        status = "idle"

            # Task display: prefer kanban running task title, fall back to last log entry
            last_task = li.get("task", "")
            if kanban_task_titles.get(name):
                last_task = kanban_task_titles[name]

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
                "last_task": last_task,
                "model": li.get("model", ""),
                "last_seen": last_seen,
            })

        return {
            "agents": agents,
            "total": len(agents),
            "pulsating": sum(1 for a in agents if a["status"] == "pulsating"),
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
# Terminal execution
# ---------------------------------------------------------------------------
TERMINAL_TIMEOUT = 30
TERMINAL_MAX_OUTPUT = 50000  # 50KB cap

# Commands that are never allowed
TERMINAL_BLOCKLIST = [
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=/dev/zero",
    ":(){:|:&};:", "chmod -R 777 /", "chown -R",
]

def terminal_exec(command, cwd="/home/jayant"):
    """Execute a shell command safely and return stdout, stderr, exit_code."""
    if not command or not command.strip():
        return "", "empty command", 1

    # Blocklist check
    cmd_lower = command.strip().lower()
    for blocked in TERMINAL_BLOCKLIST:
        if blocked.lower() in cmd_lower:
            return "", f"blocked: {blocked}", 1

    # Resolve cwd
    if not cwd:
        cwd = "/home/jayant"
    cwd = os.path.expanduser(cwd)
    if not os.path.isdir(cwd):
        cwd = "/home/jayant"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=TERMINAL_TIMEOUT,
        )
        stdout = result.stdout[:TERMINAL_MAX_OUTPUT]
        stderr = result.stderr[:TERMINAL_MAX_OUTPUT]
        return stdout, stderr, result.returncode
    except subprocess.TimeoutExpired:
        return "", f"timeout after {TERMINAL_TIMEOUT}s", 124
    except Exception as e:
        return "", str(e), 1


# ---------------------------------------------------------------------------
# Content file browser API
# ---------------------------------------------------------------------------
from content_api import (
    content_safe_path,
    content_list_directory,
    content_get_file,
    content_save_file,
)

import sys as _sys
import importlib.util as _util
_SIP_CLIENT_PATH = os.path.expanduser("~/.hermes/agents/_shared/sip-client.py")
_spec = _util.spec_from_file_location("sip_client", _SIP_CLIENT_PATH)
_sip_mod = _util.module_from_spec(_spec)
_spec.loader.exec_module(_sip_mod)
load_sip_config = _sip_mod.load_sip_config
save_sip_config = _sip_mod.save_sip_config
generate_sipjs_app = _sip_mod.generate_sipjs_app
SIPClient = _sip_mod.SIPClient

# ---------------------------------------------------------------------------
# Hermes Chat Session (tmux-backed)
# ---------------------------------------------------------------------------
HERMES_SESSION_NAME = "dashboard_hermes"
HERMES_SESSION = None  # Will hold the tmux session name

def hermes_session_create():
    """Create a new tmux session running Hermes chat."""
    global HERMES_SESSION
    try:
        # Kill any existing session
        subprocess.run(
            ["tmux", "kill-session", "-t", HERMES_SESSION_NAME],
            capture_output=True, timeout=5
        )
        # Create new tmux session with hermes
        subprocess.run(
            ["tmux", "new-session", "-d", "-s", HERMES_SESSION_NAME, "-x", "120", "-y", "40",
             "hermes"],
            capture_output=True, timeout=10
        )
        HERMES_SESSION = HERMES_SESSION_NAME
        return True, "Hermes session started"
    except Exception as e:
        return False, str(e)

def hermes_session_send(command):
    """Send a command to the Hermes tmux session and return output."""
    if not HERMES_SESSION:
        return "No active Hermes session. Click 'Hermes Chat' to start one."
    try:
        # Send the command
        subprocess.run(
            ["tmux", "send-keys", "-t", HERMES_SESSION, command, "Enter"],
            capture_output=True, timeout=5
        )
        # Wait for response
        time.sleep(3)
        # Capture output
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", HERMES_SESSION, "-p"],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout[-2000:]  # Last 2000 chars
    except Exception as e:
        return f"Error: {e}"

def hermes_session_status():
    """Check if Hermes tmux session is alive."""
    try:
        result = subprocess.run(
            ["tmux", "has-session", "-t", HERMES_SESSION_NAME],
            capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------
class Handler(BaseHTTPRequestHandler):
    """Routes requests to the right handler."""

    def log_message(self, fmt, *args):
        # Suppress default stderr logging
        pass

    # ---- helpers ----
    def _send(self, code, body, content_type="application/json", cache=False):
        payload = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if not cache:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("Pragma", "no-cache")
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

        # Cron jobs (system + Hermes)
        if path == "/api/cron":
            self._send_json(200, cron_data())
            return

        # Content - file browser API
        if path == "/api/content/list":
            qs = parse_qs(parsed.query)
            dir_path = qs.get("path", ["/home/jayant"])[0]
            safe = content_safe_path(dir_path)
            if safe is None:
                self._send_json(403, {"error": "access denied"})
                return
            if not os.path.isdir(safe):
                self._send_json(404, {"error": "not found"})
                return
            entries = content_list_directory(safe)
            if entries is None:
                self._send_json(403, {"error": "permission denied"})
                return
            self._send_json(200, {"path": safe, "entries": entries})
            return

        if path == "/api/content/get":
            qs = parse_qs(parsed.query)
            file_path = qs.get("path", [None])[0]
            if not file_path:
                self._send_json(400, {"error": "missing path"})
                return
            safe = content_safe_path(file_path)
            if safe is None:
                self._send_json(403, {"error": "access denied"})
                return
            if not os.path.isfile(safe):
                self._send_json(404, {"error": "not found"})
                return
            result = content_get_file(safe)
            self._send_json(200, result)
            return

        if path == "/api/content/download":
            qs = parse_qs(parsed.query)
            file_path = qs.get("path", [None])[0]
            if not file_path:
                self._send_json(400, {"error": "missing path"})
                return
            safe = content_safe_path(file_path)
            if safe is None or not os.path.isfile(safe):
                self._send_json(404, {"error": "not found"})
                return
            try:
                with open(safe, "rb") as f:
                    data = f.read()
                self._send(200, data, "application/octet-stream")
            except Exception as e:
                self._send_json(500, {"error": str(e)})
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

        # Activity rate (per-minute metrics for sparkline)
        if path == "/api/activity/rate":
            result = {}
            try:
                now_ts = time.time()
                min_ago = now_ts - 60
                day_ago = now_ts - 86400

                # Agent calls in last 60s (agent_logs.created_at is ISO text)
                conn = sqlite3.connect(AGENT_LOGS_DB)
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM agent_logs WHERE created_at > datetime('now', '-1 minute')")
                result['calls_per_min'] = cur.fetchone()[0]

                # Failures in last 60s
                cur.execute("SELECT COUNT(*) FROM agent_logs WHERE status='failed' AND created_at > datetime('now', '-1 minute')")
                result['failures_per_min'] = cur.fetchone()[0]

                # 24h totals for corrected stat tiles
                cur.execute("SELECT COUNT(*) FROM agent_logs WHERE created_at > datetime('now', '-24 hours')")
                result['calls_24h'] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM agent_logs WHERE status='completed' AND created_at > datetime('now', '-24 hours')")
                result['completed_24h'] = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM agent_logs WHERE status='failed' AND created_at > datetime('now', '-24 hours')")
                result['failed_24h'] = cur.fetchone()[0]
                conn.close()

                # Messages in last 60s + 24h (messages.timestamp is REAL unix epoch)
                conn2 = sqlite3.connect(STATE_DB)
                conn2.row_factory = sqlite3.Row
                cur2 = conn2.cursor()
                cur2.execute("SELECT COUNT(*) FROM messages WHERE timestamp > ?", (min_ago,))
                result['messages_per_min'] = cur2.fetchone()[0]
                cur2.execute("SELECT COUNT(*) FROM messages WHERE timestamp > ?", (day_ago,))
                result['messages_24h'] = cur2.fetchone()[0]

                # Token throughput in last 60s (sessions.started_at is REAL unix epoch)
                cur2.execute("""
                    SELECT COALESCE(SUM(input_tokens), 0) + COALESCE(SUM(output_tokens), 0)
                    FROM sessions
                    WHERE started_at > ?
                """, (min_ago,))
                result['tokens_per_min'] = cur2.fetchone()[0]

                # Token totals 24h
                cur2.execute("""
                    SELECT COALESCE(SUM(input_tokens), 0), COALESCE(SUM(output_tokens), 0),
                           COALESCE(SUM(cache_read_tokens), 0), COALESCE(SUM(cache_write_tokens), 0)
                    FROM sessions WHERE started_at > ?
                """, (day_ago,))
                row = cur2.fetchone()
                result['tokens_24h'] = {'input': row[0], 'output': row[1], 'cache_read': row[2], 'cache_write': row[3]}

                # Active sessions in last 60s
                cur2.execute("SELECT COUNT(*) FROM sessions WHERE started_at > ?", (min_ago,))
                result['active_sessions'] = cur2.fetchone()[0]
                conn2.close()

                # Active running tasks from kanban
                result['active_tasks'] = 0
                try:
                    kconn = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
                    kconn.execute("PRAGMA query_only=1")
                    kcur = kconn.cursor()
                    kcur.execute("SELECT COUNT(*) FROM tasks WHERE status = 'running'")
                    result['active_tasks'] = kcur.fetchone()[0]
                    kconn.close()
                except Exception:
                    pass

                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # SIP config
        if path == "/api/sip/config":
            self._send_json(200, load_sip_config())
            return

        # SIP web softphone app
        if path in ("/api/sip/webapp", "/api/sip/v2"):
            html = generate_sipjs_app(config=load_sip_config())
            self._send(200, html, "text/html; charset=utf-8")
            return

        # Static assets (SIP.js bundle, etc.)
        if path.startswith("/static/"):
            static_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", path[len("/static/"):])
            if not os.path.isfile(static_file):
                self._send_json(404, {"error": "not found"})
                return
            ext = os.path.splitext(static_file)[1]
            ct = {"js": "application/javascript", "css": "text/css"}.get(ext, "application/octet-stream")
            with open(static_file, "rb") as f:
                self._send(200, f.read(), ct)
            return

        # SSE endpoint
        if path == "/events":
            self._handle_sse()
            return

        self._send_json(404, {"error": "not found"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Terminal exec
        if path == "/api/terminal/exec":
            try:
                body = self._read_body()
                cmd = body.get("command", "")
                cwd = body.get("cwd", "/home/jayant")
                stdout, stderr, exit_code = terminal_exec(cmd, cwd)
                self._send_json(200, {
                    "stdout": stdout,
                    "stderr": stderr,
                    "exit_code": exit_code,
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # Hermes session create
        if path == "/api/terminal/hermes/start":
            ok, msg = hermes_session_create()
            self._send_json(200 if ok else 500, {"ok": ok, "message": msg})
            return

        # Hermes session send
        if path == "/api/terminal/hermes/send":
            try:
                body = self._read_body()
                cmd = body.get("command", "")
                output = hermes_session_send(cmd)
                self._send_json(200, {"output": output})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # Hermes session status
        if path == "/api/terminal/hermes/status":
            alive = hermes_session_status()
            self._send_json(200, {"alive": alive})
            return

        # SIP config save
        if path == "/api/sip/config":
            try:
                body = self._read_body()
                save_sip_config(body)
                self._send_json(200, {"ok": True, "message": "SIP config saved"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # SIP make call
        if path == "/api/sip/call":
            try:
                body = self._read_body()
                target = body.get("target", "")
                if not target:
                    self._send_json(400, {"error": "missing target"})
                    return
                client = SIPClient()
                ok = client.call(target)
                self._send_json(200, {"ok": ok, "message": f"Calling {target}"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        # Content - save file
        if path == "/api/content/save":
            try:
                body = self._read_body()
                file_path = body.get("path", "")
                content = body.get("content", "")
                if not file_path:
                    self._send_json(400, {"error": "missing path"})
                    return
                safe = content_safe_path(file_path)
                if safe is None:
                    self._send_json(403, {"error": "access denied"})
                    return
                result = content_save_file(safe, content)
                self._send_json(200, result)
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

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
    server.allow_reuse_address = True
    print(f"Mission Control Dashboard running on http://{LISTEN_HOST}:{LISTEN_PORT}")
    print(f"  GET  /           → index.html")
    print(f"  GET  /api/snapshot → full JSON snapshot")
    print(f"  GET  /events     → SSE stream (5s updates)")
    print(f"  GET  /api/board  → list tasks")
    print(f"  GET  /api/cron  → cron jobs (system + Hermes)")
    print(f"  GET  /api/content/list  → list directory")
    print(f"  GET  /api/content/get  → read file")
    print(f"  GET  /api/content/download  → download file")
    print(f"  POST /api/board  → create task")
    print(f"  POST /api/board/update?id= → update task")
    print(f"  POST /api/board/delete?id= → delete task")
    print(f"  GET  /api/sip/config → SIP config")
    print(f"  POST /api/sip/config → save SIP config")
    print(f"  GET  /api/sip/webapp → SIP.js softphone")
    print(f"  POST /api/sip/call → make SIP call")
    print(f"  POST /api/terminal/exec → execute command")
    print(f"  POST /api/terminal/hermes/start → start Hermes chat session")
    print(f"  POST /api/terminal/hermes/send → send to Hermes session")
    print(f"  POST /api/terminal/hermes/status → check Hermes session status")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
