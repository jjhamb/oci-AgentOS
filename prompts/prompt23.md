# Prompt 23 — Overview Tab (The Ops Console)

**Phase:** 9 (Overview Tab)
**Send to:** Coder

---

**⚠️ BACKUP index.html and server.py before this prompt!**

Wire up the live data connection: SSE from /events, polling fallback every 8 seconds. Then build the full Overview tab.

LIVE OPS CONSOLE — a full-width GlassCard({ children: three columns, style: 'display:grid; grid-template-columns: 180px 1fr 1fr; gap: var(--space-5)' }). Colors from var(--agent-*), var(--brand-*), var(--status-*). Spacing from var(--space-*). Fonts from var(--font-display), var(--font-mono).

  Left — a radar SVG 180×180 (viewBox 0 0 140 140). Four faint concentric circles, two hairline crosshair lines. CSS-animated sweep group. Five agent dots rendered by JS, positioned by share of total responses.

  Agent accent colors: var(--agent-orchestrator) · var(--agent-analyst) · var(--agent-writer) · var(--agent-marketer) · var(--agent-coder)

  Center — "CURRENT DIRECTIVE" mono label. A line of cyan mono text cycling through recent log entries formatted as "AGENTNAME · task description". Below it: "CONTEXT WINDOW" section cycling each agent with their fill-bar and last status.

  Right — "VPS HEALTH". Three ProgressBar({ pct: ..., color: var(--brand-cyan) }) with color thresholds (amber > 70%, red > 85%). Footer: "HERMES DBs" and total DB size in gold.

  Footer — 5-cell equal grid: Queue · Sessions · Errors · Today · Uptime. Mono numbers. Errors is mint when zero, red if above.

STATS STRIP — five StatCard({ label, value, accent, barWidth }) in a row, each with a 2px solid top border:

  Integrity (var(--status-active)) · Agent Calls (var(--brand-cyan)) · Messages (var(--agent-orchestrator)) · Tokens In (var(--brand-gold)) · Cache Hits (var(--brand-pink)).

  Integrity shows success rate with jittering decimal. Below: "N of 5 responsive" with pulsing mint dot.

BOTTOM SECTION — two GlassCard side by side (1.2fr · 1fr):

  Left "Throughput": large response count in cyan, sparkline canvas with violet→cyan gradient, glowing dot at rightmost point. Redraws every 900ms.

  Right "Activity": live feed of 8 most recent log entries using Badge for agent name and status colors.

DATA SOURCES — same as before: d.agents, d.activity, d.vps, d.kanban, d.sessions, d.stats, d.gateway, d.activity_by_day

---

## What to Watch For
- SSE connection to /events must work (with polling fallback)
- Radar SVG should show 5 agent dots with correct colors
- VPS health bars should show real CPU/RAM/disk data
- Stats strip should show live numbers from the API
- Activity feed should show the 8 most recent log entries
- If anything is blank, check the SSE/API connection
