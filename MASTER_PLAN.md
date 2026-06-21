# MASTER PLAN — Hermes AgentOS Mission Control Dashboard

## Overview
This plan breaks the Asad Tinkers guide into a step-by-step workflow. Each phase builds on the previous one. Follow the order strictly.

## Pre-Build Requirements

### VPS
- Ubuntu 22.04+ or 24.04 LTS
- 2+ vCPU, 4GB+ RAM
- Root access via SSH

### Accounts & Tokens Needed
- [ ] Discord bot token (from https://discord.com/developers/applications)
- [ ] Telegram bot token (from @BotFather)
- [ ] OpenRouter API key (or other model provider)
- [ ] Discord Server ID (Guild ID)
- [ ] Discord User ID
- [ ] Discord Channel ID (for home channel)

### Local Machine
- SSH client (built-in on Mac/Linux, PowerShell on Windows)
- Web browser (for dashboard access via SSH tunnel)

---

## Phase-by-Phase Execution Plan

### Phase 1: Orchestrator Setup (Prompts 1–2)
**Time:** ~10 minutes
**Risk:** Low
**What you'll do:**
1. Open Telegram, start a session with your Hermes bot
2. Send Prompt 1 — Orchestrator creates itself
3. Send Prompt 2 — Operating rules saved
4. Run post-phase audit

**Watch for:** Orchestrator should confirm all rules saved. If it tries to negotiate, push it to accept.

---

### Phase 2: Four Persistent Agents (Prompts 3–4)
**Time:** ~15 minutes
**Risk:** Low
**What you'll do:**
1. Send Prompt 3 — Creates Analyst, Writer, Marketer, Coder
2. Send Prompt 4 — Memory, workspaces, role boundaries
3. Run post-phase audit

**Watch for:** All agents must be in ONE profile. Verify workspace directories exist.

---

### Phase 3: Agent Collaboration (Prompts 5–8)
**Time:** ~20 minutes
**Risk:** Medium
**What you'll do:**
1. Send Prompt 5 — Routing table + slash commands
2. Send Prompt 6 — Shared team awareness
3. Send Prompt 7 — Full content pipeline
4. Send Prompt 8 — Test pipeline with real topic
5. Run post-phase audit

**Watch for:** Pipeline test (Prompt 8) is the first real integration test. Watch for silent failures.

---

### Phase 4: Discord Integration (Prompts 9–12)
**Time:** ~30 minutes
**Risk:** High (most failure-prone phase)
**What you'll do:**
1. Complete ALL Discord prerequisites (bot, server, intents, permissions)
2. Run `hermes setup` and configure Discord
3. Send Prompt 9 — Connect to Discord server
4. Send Prompt 10 — Verify bot permissions
5. Send Prompt 11 — Create agent channels
6. Send Prompt 12 — Bind agents to channels
7. Run post-phase audit

**Watch for:**
- Bot must have Administrator permission
- All 3 Privileged Gateway Intents must be enabled
- Channel IDs must be saved for Prompt 12
- Test "Who are you?" in each channel

---

### Phase 5: Activity Logging (Prompts 13–16)
**Time:** ~20 minutes
**Risk:** Low
**What you'll do:**
1. Send Prompt 13 — Build logging database + script
2. Send Prompt 14 — Roll out to all agents
3. Send Prompt 15 — Reinforce with each agent individually
4. Send Prompt 16 — Monthly retention cleanup
5. Run post-phase audit

**Watch for:**
- Prompt 15 must be sent to EACH agent individually (5 separate messages)
- Verify logs with sqlite3 query after each prompt
- Test cleanup script manually

---

### Phase 6: Dashboard Backend (Prompts 17–18)
**Time:** ~15 minutes
**Risk:** Medium
**What you'll do:**
1. Send Prompt 17 — Explore data sources (read-only)
2. Send Prompt 18 — Build server.py
3. Run post-phase audit

**Watch for:**
- Prompt 17 should NOT create any files
- server.py must respond to curl test
- All 5 data functions must work
- board.db should have 8 pre-seeded tasks

---

### Phase 7: Frontend Design System (Prompts 19–21)
**Time:** ~15 minutes
**Risk:** Low
**What you'll do:**
1. Send Prompt 19 — Design tokens (tokens.css)
2. Send Prompt 20 — Component primitives (components.js)
3. Send Prompt 21 — Dashboard skeleton (index.html)
4. Run post-phase audit

**Watch for:**
- No raw hex/pixel/font values — everything must use CSS variables
- Tab switching should work
- No data binding yet — just the visual shell

---

### Phase 8: Backup Protocol (Prompt 22)
**Time:** ~5 minutes
**Risk:** Critical
**What you'll do:**
1. Send Prompt 22 — Create backup folder + first backup
2. Confirm backup files exist

**⚠️ From this point on, BACKUP before EVERY prompt!**

---

### Phase 9: Overview Tab (Prompt 23)
**Time:** ~15 minutes
**Risk:** Medium
**What you'll do:**
1. **BACKUP** index.html and server.py
2. Send Prompt 23 — Build Overview tab
3. Verify SSE connection works
4. Check all data panels show real data

---

### Phase 10: Agents Tab (Prompts 24–25)
**Time:** ~20 minutes
**Risk:** Medium
**What you'll do:**
1. **BACKUP** index.html and server.py
2. Send Prompt 24 — Agent cards + log table
3. **BACKUP** index.html and server.py
4. Send Prompt 25 — Statistics section + donut chart
5. Verify agent cards show real data

---

### Phase 11: Tasks + Schedule Tabs (Prompts 26–27)
**Time:** ~15 minutes
**Risk:** Low
**What you'll do:**
1. **BACKUP** index.html and server.py
2. Send Prompt 26 — Tasks tab
3. **BACKUP** index.html and server.py
4. Send Prompt 27 — Schedule tab
5. Test task CRUD operations

---

### Phase 12: Content Tab + Document Protocol (Prompts 28–29)
**Time:** ~20 minutes
**Risk:** Low
**What you'll do:**
1. **BACKUP** index.html and server.py
2. Send Prompt 28 — Content tab backend + UI
3. Send Prompt 29 — Document storage protocol to all 5 agents
4. Verify agents created subfolders + test documents
5. Final post-build audit

---

## Post-Build: Remote Access Setup

After the dashboard is built:

### SSH Keys
```bash
# Generate key (if needed)
ssh-keygen -t ed25519 -C "$(whoami)@$(hostname)-agentos"

# Copy to VPS
ssh-copy-id root@YOUR_VPS_IP

# Verify
ssh root@YOUR_VPS_IP "echo 'SSH key auth working'"
```

### SSH Tunnel Access
```bash
# Create tunnel
ssh -L 51763:127.0.0.1:51763 root@YOUR_VPS_IP

# Access dashboard at http://localhost:51763
```

### One-Click Launcher (Mac)
Create `~/Desktop/AgentOS.command`:
```bash
#!/bin/bash
pkill -f "51763:127.0.0.1:51763" 2>/dev/null
sleep 1
ssh -o StrictHostKeyChecking=no -N -L 51763:127.0.0.1:51763 root@YOUR_VPS_IP &
sleep 2
open "http://localhost:51763"
```
```bash
chmod +x ~/Desktop/AgentOS.command
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot doesn't connect to Discord | Check token, intents, and OAuth2 permissions |
| Agent responds in wrong channel | Rebind agent to correct channel (Prompt 12) |
| Dashboard shows blank/white screen | Restore from backup, re-run prompt |
| SSE not working | Check server.py is running, port 51763 is open |
| Data panels empty | Verify databases exist and have data |
| Context window too large | Start a fresh Hermes session for each phase |
| Cron cleanup fails | Check script is executable, test manually |

## Total Estimated Time
- **Phases 1-3 (Agents):** ~45 minutes
- **Phase 4 (Discord):** ~30 minutes
- **Phase 5 (Logging):** ~20 minutes
- **Phase 6 (Backend):** ~15 minutes
- **Phase 7 (Design):** ~15 minutes
- **Phases 8-12 (Frontend):** ~75 minutes
- **Remote Access:** ~10 minutes
- **Total:** ~3.5 hours
