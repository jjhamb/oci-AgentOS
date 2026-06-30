# AgentOS Dashboard — Deployment & Restore Guide

## Quick Start (Fresh Machine)

```bash
# 1. Clone
git clone https://github.com/jjhamb/oci-AgentOS.git
cd oci-AgentOS

# 2. Install Python deps (into venv)
python3 -m venv .venv
source .venv/bin/activate
pip install websockets

# 3. Start server
cd backend
python3 server.py
```

Dashboard: `http://localhost:51763`
Terminal WS: `ws://localhost:51763` (port 51765)

---

## Ports Required

| Port | Protocol | Purpose |
|------|----------|---------|
| 51763 | HTTP | Dashboard UI + REST API + SSE |
| 51765 | WS | PTY terminal WebSocket |

Both must be accessible. On the current OCI ARM server:
- UFW allows 22/80/443 only
- Tailscale `ts-input` chain allows all traffic to 100.100.160.29
- Access via `http://100.100.160.29:51763` works through Tailscale

### Firewall Rules (if NOT using Tailscale)
```bash
sudo ufw allow 51763/tcp
sudo ufw allow 51765/tcp
```

---

## File Manifest (portability checklist)

### Core (required)
| File | Purpose |
|------|---------|
| `backend/server.py` | Main HTTP+WS server |
| `backend/index.html` | Dashboard frontend |
| `backend/components.js` | Shared UI components |
| `backend/content_api.py` | File content API |
| `backend/tokens.css` | Design tokens |
| `backend/highlight.min.js` | Code highlighting |
| `backend/highlight-github-dark.min.css` | Code theme |
| `backend/marked.min.js` | Markdown renderer |
| `backend/xterm.min.js` | xterm.js terminal |
| `backend/xterm.min.css` | xterm.js styles |
| `backend/xterm-addon-fit.min.js` | Terminal resize |
| `tabs/terminal.html` | PTY terminal tab |
| `tabs/overview.html` | Overview tab |
| `tabs/agents.html` | Agents tab |
| `tabs/tasks.html` | Tasks tab |
| `tabs/schedule.html` | Schedule tab |
| `tabs/content.html` | Content viewer tab |
| `tabs/architecture.html` | Architecture tab |
| `tabs/sip.html` | SIP softphone tab |
| `components.js` | Root-level shared components |
| `index.html` | Root redirect |
| `tokens.css` | Root-level tokens |
| `ui-flow.html` | Tile/radar state documentation |

### Optional (nice to have)
| File | Purpose |
|------|---------|
| `backend/start.sh` | Startup script |
| `backend/sip-gateway*.py/js` | SIP gateway |
| `backend/static/sip-0.21.2.min.js` | SIP.js library |
| `backend/udp-bridge.py` | UDP bridge |
| `tabs/mezzaria-style/` | Mezzaria doc templates |
| `prompts/` | AI prompts |
| `checklists/` | Phase checklists |
| `scripts/` | Utility scripts |
| `rollback_pre_escalating.sh` | Rollback script |

### Generated at runtime (NOT in git, will be recreated)
| File | Purpose |
|------|---------|
| `backend/state.db` | Session state (SQLite) |
| `backend/board.db` | Kanban board (SQLite) |
| `backend/agent_logs.db` | Agent activity logs |
| `backend/server.log` | Server log |
| `backend/server.pid` | PID file |
| `backend/node_modules/` | Node deps (puppeteer for screenshots) |

---

## Dependencies

### Python (pip)
```
websockets>=15.0
```
Stdlib only otherwise: `asyncio`, `threading`, `pty`, `select`, `fcntl`, `termios`, `struct`, `json`, `sqlite3`, `os`, `subprocess`, `http.server`

### System
- Python 3.10+
- Linux (uses `pty`, `termios`, `fcntl`)
- Tailscale (for remote access without opening firewall)

---

## Server Architecture

```
Main thread:     terminal_ws_thread() → asyncio event loop → websockets.serve(pty_handler, 0.0.0.0, 51765)
Thread 1:        http_thread → ThreadingHTTPServer → Handler (port 51763)
Thread 2:        sse_pusher → SSE stream push loop
Thread 3+:       pty_reader (per terminal session) → reads PTY master → pushes to queue
```

### PTY Flow
```
Browser keydown → window listener → ws.send(data) → server receives → os.write(master_fd)
PTY output → pty_reader thread → asyncio queue → websocket.send() → term.write()
```

---

## Known Issues & Fixes

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| Numbers not typing in terminal | `json.loads("1")` parses as valid JSON int, digit silently dropped | Only treat `{`-prefixed messages as JSON commands |
| Terminal not visible (TDZ) | `const container` used before declaration | Moved declaration to before first use |
| Terminal WS not connecting via HTTPS | `wss://` fails without TLS cert | Force `ws://` always |
| Red flash on hermes startup | `Warning: Unknown toolsets: messaging` in config | Cosmetic only — harmless |

---

## Rollback

```bash
# Quick revert last change
git reset --hard HEAD~1

# Revert to known-good commit
git reset --hard c163cd4

# Full rollback script
bash rollback_pre_escalating.sh
```

---

## Backup & Restore

### Backup (what to save)
```bash
# Everything needed to restore
tar czf agentos-backup.tar.gz \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='*.db' \
  --exclude='*.log' \
  --exclude='*.pid' \
  --exclude='backups' \
  .
```

### Restore
```bash
tar xzf agentos-backup.tar.gz
cd Hermes-AgentOS-Dashboard/backend
python3 -m venv .venv && source .venv/bin/activate
pip install websockets
python3 server.py
```

---

## Obsidian Vault

Post-commit hook auto-syncs to: `jjhamb@100.76.21.8 ~/vault/`
