# Prompt 24 — Agents Tab

**Phase:** 10 (Agents Tab)
**Send to:** Coder

---

**⚠️ BACKUP index.html and server.py before this prompt!**

HEADER — "SUBAGENTS" eyebrow, then "The Crew." display heading (clamp 36px–60px, weight 500). Right side: a GlassCard with three cells — Active (var(--status-active)), Idle (var(--status-idle)), Dormant (var(--status-dormant)).

AGENT CARDS — five GlassCard in a row, each with a 2px solid top border in var(--agent-*). Inside:

  — Top: Badge({ text: 'ORCH' | 'ANAL' | 'WRTR' | 'MRKT' | 'CODR', color: var(--agent-*), variant: 'solid' }) on left; platform pill (var(--brand-cyan) or var(--agent-orchestrator)) and status dot on right.

  — Agent name in var(--font-display), 22px.

  — Two-line role description in var(--text-muted).

  — ThinBar({ pct: 7-day counts, color: var(--agent-*) }) for activity chart.

  — 3-column stats: Responses · Success% (mint if 100%, amber if ≥80%, red below) · Model (mono, muted, truncated).

  — 3px load bar full card width in var(--agent-*) showing share of total.

  — Last task "↳ description" in muted mono, relative timestamp below ("4m ago", "2h ago").

AGENT LOG — GlassCard with filter pill row (ALL + each agent). Log table: Time · Agent · Task · Model · Status. Max height 420px. Use Badge for status colors.

Data sources: d.agents, d.activity. Colors from var(--agent-*).

---

## What to Watch For
- 5 agent cards, each with correct accent color
- ThinBar shows 7-day activity per agent
- Success rate color coding: mint (100%), amber (≥80%), red (below)
- Agent log table should be filterable by agent
- Status badges use correct colors
