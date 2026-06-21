# Hermes AgentOS Mission Control Dashboard

**Source:** https://asadtinkers.com/guides/hermes-agentos-mission-control-dashboard/
**Author:** Asad Zane (asadtinkers)
**Guide Updated:** Jun 17, 2026
**Build Date:** Jun 19, 2026

---

## What You'll Build

- 🤖 **Orchestrator** on Telegram — top-level coordinator
- 🎯 **4 Persistent Specialists** on Discord — Analyst, Writer, Marketer, Coder
- 📊 **Live Dashboard** — Overview, Agents, Statistics, Tasks, Schedule, Content tabs
- 🔐 **Secure Remote Access** — SSH tunnels + Tailscale
- 💾 **Automatic Logging & Retention** — every agent action recorded
- 📁 **Content Library** — all long-form agent output saved as markdown

## VPS Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 2GB | 4GB+ |
| CPU | 1 vCPU | 2+ vCPU |
| Storage | 25GB SSD | 35GB+ SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

## Build Phases

| Phase | Prompts | What It Builds |
|-------|---------|----------------|
| Phase 1 | 1–2 | Orchestrator on Telegram + Operating Rules |
| Phase 2 | 3–4 | Four Persistent Agents + Memory & Workspaces |
| Phase 3 | 5–8 | Agent Collaboration + Routing + Pipeline |
| Phase 4 | 9–12 | Discord Integration |
| Phase 5 | 13–16 | Activity Logging System |
| Phase 6 | 17–18 | Dashboard Backend (server.py) |
| Phase 7 | 19–21 | Frontend Design System + Skeleton |
| Phase 8 | 22 | Backup Protocol |
| Phase 9 | 23 | Overview Tab (Ops Console) |
| Phase 10 | 24–25 | Agents Tab |
| Phase 11 | 26–27 | Tasks + Schedule Tabs |
| Phase 12 | 28–29 | Content Tab + Document Protocol |

## How to Use

1. **One fresh Hermes session per phase** — not per prompt
2. Start with Phase 1, Prompt 1 on your VPS Hermes
3. After each phase, run the post-build audit (see checklists/)
4. For Prompts 21–29: **BACKUP** index.html and server.py before each prompt
5. Watch context window — if responses get weird, start a fresh session

## Folder Structure

```
Hermes-AgentOS-Dashboard/
├── README.md              # This file
├── MASTER_PLAN.md         # Detailed plan with watch-points per prompt
├── prompts/
│   ├── prompt01.md        # All 29 prompts, individually filed
│   ├── prompt02.md
│   └── ...through prompt29.md
└── checklists/
    ├── phase1_checklist.md    # Verification steps per phase
    ├── phase2_checklist.md
    └── ...through phase12_checklist.md
```

## Critical Rules

1. **Single profile only** — all agents in one Hermes profile
2. **Frontier models recommended** — weak models hallucinate imports
3. **Backup before every frontend prompt** (21–29) — one bad edit = white screen
4. **Post-build audit after each phase** — catch bugs early
