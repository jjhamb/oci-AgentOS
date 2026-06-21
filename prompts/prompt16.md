# Prompt 16 — Monthly Log Retention

**Phase:** 5 (Activity Logging)
**Send to:** Orchestrator

---

Set up monthly log cleanup — permanent deletion, no archiving.

Create ~/.hermes/agents/_shared/cleanup-logs.sh that:

- Deletes rows in agent-logs.db older than RETENTION_DAYS (set to 30 at the top)
- Runs VACUUM afterward to reclaim disk space
- Prints: rows deleted, total remaining
- Python stdlib + bash only, no pip packages
- Creates db/table if missing (safe to run fresh)

Make it executable. Schedule via cron: 1st of month at 03:00 server time. Show me the exact crontab line.

After cleanup, Orchestrator sends a short Telegram message:

"Monthly log cleanup ran: deleted X rows, Y remaining (retention: 30 days)."

Deletion must NOT depend on the notification. If Telegram is unreachable, cleanup still completes and logs locally that the notify step failed.

Run it once manually as a test and show me the summary output.

---

## What to Watch For
- Script must be executable
- Cron should be: `0 3 1 * * /root/.hermes/agents/_shared/cleanup-logs.sh`
- Test run should show rows deleted + remaining count
- Deletion and notification must be independent (deletion first, notify second)
- If Telegram fails, cleanup still completes
