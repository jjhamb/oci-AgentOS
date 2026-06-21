# Prompt 14 — Roll Out Logging to All Agents

**Phase:** 5 (Activity Logging)
**Send to:** Orchestrator

---

Time to wire logging into every agent.

Create ~/.hermes/agents/_shared/LOGGING_POLICY.md with the rules:

- Log EVERY response before you send it — no exceptions
- Run: bash ~/.hermes/agents/_shared/log-task-local.sh "<agent>" "<what you did>" "completed"
- Keep the description tight — under 140 chars
- Agent names in lowercase: orchestrator, analyst, writer, marketer, coder
- "completed" for success, "failed" when something breaks
- Never mention logging to the user unless they ask

Staple a pointer to the bottom of each agent's AGENTS.md (Orchestrator, Analyst, Writer, Marketer, Coder). The pointer must have the exact runnable command with that agent's lowercase name baked in — not just a reference to the shared file.

Orchestrator lives on Telegram — confirm it can reach the log script from there. If it can't, tell me what it needs instead of skipping the step.

Smoke test all 5 agents. Show me:

sqlite3 ~/.hermes/agent-logs.db "SELECT agent_name, status, created_at FROM agent_logs ORDER BY created_at DESC LIMIT 10;"

---

## What to Watch For
- LOGGING_POLICY.md at exact path ~/.hermes/agents/_shared/
- All 5 agents must have pointer added to their AGENTS.md
- Orchestrator (Telegram) must be able to run the bash script
- Smoke test should show entries from all 5 agents
- If Orchestrator can't reach script, check PATH and permissions
