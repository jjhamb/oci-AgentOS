# Phase 6 Checklist: Dashboard Backend (Prompts 17–18)

## After Prompt 17 — Explore the Data Sources
- [ ] state.db schema examined (table names, column names)
- [ ] kanban.db schema examined
- [ ] gateway_state.json structure examined
- [ ] Timestamp formats noted (ISO vs Unix float)
- [ ] No files created (read-only exploration)

## After Prompt 18 — Build the Backend Server
- [ ] /root/agent-mission-control/server.py created
- [ ] Server binds to 127.0.0.1:51763
- [ ] GET / serves index.html
- [ ] GET /api/snapshot returns JSON
- [ ] GET /events pushes SSE updates every 5 seconds
- [ ] gateway_data() reads gateway_state.json
- [ ] activity_data() queries agent-logs.db (last 50 entries, per-agent stats)
- [ ] sessions_data() queries state.db (session count, token totals)
- [ ] vps_health() reads /proc/stat, /proc/meminfo, os.statvfs
- [ ] cron_jobs() reads crontab files
- [ ] All data functions wrapped in try/except
- [ ] board.db created with tasks table (8 pre-seeded tasks)
- [ ] GET /api/board, POST /api/board, POST /api/board/update, POST /api/board/delete all work
- [ ] start.sh launcher created
- [ ] Server responds to curl test

## Post-Phase Audit
```
Audit the Dashboard Backend build against the original prompt spec. Find:
1. Missing features / incomplete implementations
2. Bugs / broken reactivity / console errors
3. Deviations from design system
4. Data source mismatches

Give me a single copy-paste prompt I can use in a NEW session to fix everything found.
```
