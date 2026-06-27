# Hermes AgentOS Dashboard — File Map

> **Last updated:** 2026-06-27  
> **Working file:** `tabs/overview.html`  
> **Served as:** `backend/index.html` (copy on deploy)

## File Roles

| File | Role | Editable? |
|------|------|-----------|
| `tabs/overview.html` | **SOURCE OF TRUTH** — Overview tab + Agents tab (merged) | ✅ YES |
| `backend/index.html` | Served copy — `index.html` replaces old skeleton | ❌ Copy only |
| `tabs/agents_restored.html` | Pure backup from commit `dcd79d2` (three-tier status) | ❌ Reference |
| `tabs/agents.html` | Original standalone agents file (untouched) | ❌ Reference |
| `tabs/overview.html.bak` | Local backup (pre-fix snapshot) | ❌ Reference |
| `backend/index.html.bak` | Local backup (pre-merge, old skeleton) | ❌ Reference |
| `backend/server.py` | Python backend — API endpoints, static serving | ✅ YES |

## Deploy Flow

```
Edit: tabs/overview.html
    ↓
Copy: cp tabs/overview.html backend/index.html
    ↓
Restart: pkill -f server.py && python3 server.py
    ↓
Hard-refresh browser: Ctrl+Shift+R
```

## Restore Points

| Commit | What's safe to restore | Where to start |
|--------|----------------------|----------------|
| `dcd79d2` | `tabs/agents.html` — three-tier agents tab (standalone) | Use as reference, copy agents section into current `tabs/overview.html` |
| `d7dd435` | Current HEAD — merged Overview+Agents, all fixes | **Start here** — `tabs/overview.html` is working |
| `0178e07` | Old `tabs/overview.html` (pre-agents, older Overview) | ⚠️ Loses agents tab work — DO NOT use as base |

## Key Decisions

- `index.html` = copy of `tabs/overview.html` (replaces old skeleton)
- `Cache-Control: no-store` required on all served HTML
- Provider poll interval: 15s
- Sparkline: 24h hourly trend (2 series: sessions + tokens)
- Quota: `SUM(api_call_count)` from `state.db`, 11 keys × 200/day = 2200
- Agents SSE structure: `data.agents.agents` (nested — use `agents?.agents?.find()`)
- Three-tier status: `pulsating` / `active` / `idle` (CSS: `.status-pulsating`)

## Quick Restore (if everything breaks)

```bash
cd ~/Desktop/Hermes-AgentOS-Dashboard
git checkout d7dd435 -- tabs/overview.html
cp tabs/overview.html backend/index.html
pkill -f "python.*server.py" 2>/dev/null; sleep 1
cd backend && python3 server.py > /tmp/server.log 2>&1 &
```
