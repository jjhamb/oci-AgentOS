# Prompt 17 — Explore the Data Sources

**Phase:** 6 (Dashboard Backend)
**Send to:** Coder (Discord #coder-build)

---

Project folder: /root/agent-mission-control/ · Port: 51763 · Bind to 127.0.0.1 only

Python stdlib only: no pip, no npm. Everything in one server.py and one index.html.

All SQLite connections must be read-only (file:path?mode=ro + PRAGMA query_only=1).

Data lives in HERMES_HOME=/root/.hermes — never write to any of these:

- agent-logs.db — the logging database we built
- state.db — auto-created by Hermes, stores sessions and token usage
- kanban.db — auto-created by Hermes, its internal task board
- gateway_state.json — live gateway status, rewritten by Hermes on every change

This is a read-only mission control dashboard for the Hermes system we just set up.

Read the schemas of state.db, kanban.db, and gateway_state.json. Show a sample timestamp from every timestamp column so we know if they're ISO strings or Unix floats. Don't create any files yet.

---

## What to Watch For
- This is a READ-ONLY exploration — no files should be created
- Note the timestamp format for each database (ISO vs Unix float)
- Pay attention to table names and column names — these are used in Prompt 18
- If any database doesn't exist yet, note that — it may need to be created by running Hermes first
