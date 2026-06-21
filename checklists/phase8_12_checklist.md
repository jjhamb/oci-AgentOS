# Phase 8-12 Checklists: Frontend Tabs

## Phase 8 (Prompt 22) — Backup Protocol
- [ ] /root/agent-mission-control/backups/ folder created
- [ ] First backup taken (index_v1.0_*.html, server_v1.0_*.py)
- [ ] Version badge (v1.0) placed in nav
- [ ] Backup naming convention confirmed
- [ ] **Remember: BACKUP before EVERY subsequent prompt!**

## Phase 9 (Prompt 23) — Overview Tab
- [ ] SSE connection to /events works (polling fallback every 8s)
- [ ] Radar SVG shows 5 agent dots with correct colors
- [ ] Current Directive cycles through recent log entries
- [ ] VPS Health shows real CPU/RAM/disk with color thresholds
- [ ] Stats strip shows 5 StatCards with live data
- [ ] Throughput sparkline redraws every 900ms
- [ ] Activity feed shows 8 most recent log entries
- [ ] All data from d.agents, d.activity, d.vps, d.sessions, d.stats, d.gateway

## Phase 10 (Prompts 24–25) — Agents Tab
- [ ] "The Crew" header with Active/Idle/Dormant summary
- [ ] 5 agent cards with correct accent colors
- [ ] ThinBar shows 7-day activity per agent
- [ ] Success rate color coding works (mint/amber/red)
- [ ] Agent log table is filterable by agent
- [ ] Donut chart renders on canvas with correct colors
- [ ] Stat cards (Tasks Today, Week, Most Active, Success Rate) show real data

## Phase 11 (Prompts 26–27) — Tasks + Schedule Tabs
- [ ] Tasks tab: 3 columns (Pending, In Progress, Done)
- [ ] "+ Add task" button in Pending column
- [ ] Task cards show title, priority, notes, relative time
- [ ] ▶ moves forward, ◀ moves back, ✕ deletes
- [ ] Optimistic updates work (revert on failure)
- [ ] Schedule tab: HERMES JOBS and SYSTEM JOBS sections
- [ ] Job cards show owner badge, command, schedule, next run, description
- [ ] Commands truncated with hover full-text
- [ ] Read-only (no edit/delete)

## Phase 12 (Prompts 28–29) — Content Tab + Document Protocol
- [ ] GET /api/content returns JSON list of .md files
- [ ] GET /api/content/get?path= returns raw markdown
- [ ] POST /api/content/save writes content back
- [ ] Path validation rejects directory traversal
- [ ] Sidebar groups docs by agent with accent colors
- [ ] View mode renders markdown as HTML
- [ ] Edit mode shows raw markdown in textarea
- [ ] Content tab wired into switchTab()
- [ ] All 5 agents created their subfolders
- [ ] All 5 agents saved test documents
- [ ] Test documents follow naming convention (YYYY-MM-DD_kebab-case.md)

## Final Post-Build Audit
```
Audit the complete dashboard build against the original prompt spec. Find:
1. Missing features / incomplete implementations
2. Bugs / broken reactivity / console errors
3. Deviations from design system
4. Data source mismatches

Give me a single copy-paste prompt I can use in a NEW session to fix everything found.
```
