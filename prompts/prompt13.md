# Prompt 13 — Build the Logging Backbone

**Phase:** 5 (Activity Logging)
**Send to:** Orchestrator

---

Create a SQLite database at ~/.hermes/agent-logs.db with this schema:

id: TEXT PRIMARY KEY (UUID)
agent_name: TEXT NOT NULL
task_description: TEXT NOT NULL
model_used: TEXT
status: TEXT NOT NULL (completed, failed, etc.)
created_at: TEXT NOT NULL (ISO 8601 timestamp)

Add indexes on agent_name, status, and created_at DESC.

Create a bash script at ~/.hermes/agents/_shared/log-task-local.sh that:

- Accepts 3–4 arguments: agent_name, task_description, status, optionally model_used
- Auto-detects model from ~/.hermes/hermes.json if model_used not provided
- Generates a UUID for id, gets current UTC timestamp, inserts the row using Python stdlib
- Prints: "LOGGED: agent_name | status | model_used"
- Creates the database and table automatically if they don't exist

Make it executable. Test it:

bash ~/.hermes/agents/_shared/log-task-local.sh "coder" "built the agent logging system" "completed"

Verify:

sqlite3 ~/.hermes/agent-logs.db "SELECT * FROM agent_logs ORDER BY created_at DESC LIMIT 5;"

Python stdlib only — no pip packages.

---

## What to Watch For
- Database at ~/.hermes/agent-logs.db
- Script must be executable (chmod +x)
- Test command should insert one row successfully
- Verify with sqlite3 query — should show the test entry
- Python stdlib only — no pip install needed
