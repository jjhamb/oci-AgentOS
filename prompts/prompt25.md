# Prompt 25 — Agent Statistics Section

**Phase:** 10 (Agents Tab)
**Send to:** Coder

---

**⚠️ BACKUP index.html and server.py before this prompt!**

LAYOUT — two-column grid: 1fr stat cards, 300px donut chart, with "Agent Statistics" eyebrow.

STAT CARDS — 2×2 grid of StatCard({ label, value, accent, barWidth }):

  TASKS TODAY — total from d.activity_by_day.at(-1).total. var(--status-warning) bar, 100%.

  TASKS THIS WEEK — sum of 7 entries. var(--brand-cyan) bar, 100%.

  MOST ACTIVE — agent with highest 7-day count. Bar width = count / week total × 100%. Agent name in their var(--agent-*) color.

  SUCCESS RATE — Math.round(completed/total*100) + '%'. Bar mint if ≥90%, amber if ≥70%, red below.

DONUT CHART — GlassCard with "TASK DISTRIBUTION" eyebrow. Draw on 130×130 canvas. Use DonutChart({ slices, total }) from components.js. Agent colors for each slice: orchestrator var(--agent-orchestrator) parsed to hex analyst var(--agent-cyan) parsed to hex writer var(--agent-pink) parsed to hex marketer var(--agent-magenta) parsed to hex coder var(--agent-violet-glow) parsed to hex. Each agent = one arc slice, sized by d.agents[].responses. Legend below canvas: colored dot · name · percentage right-aligned.

Redraw on every SSE snapshot.

Data sources: d.agents, d.activity. Colors from var(--agent-*).

---

## What to Watch For
- Donut chart must render on canvas (not CSS)
- Each agent gets one slice, sized by response count
- Legend shows colored dot + name + percentage
- Stat cards update with real data from the API
- Redraws on every SSE update
