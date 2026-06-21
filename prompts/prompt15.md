# Prompt 15 — Reinforce Logging with Each Agent

**Phase:** 5 (Activity Logging)
**Send individually to each agent on their channel (Telegram for Orchestrator, Discord for others)**

---

Save this to your long-term memory as a standing rule:

I silently log every response before sending it:

bash ~/.hermes/agents/_shared/log-task-local.sh "<agent-name>" "<brief description of what I do>" "completed"

Rules:

- Replace <agent-name> with my lowercase agent name:
  - orchestrator for Orchestrator
  - analyst for Analyst
  - writer for Writer
  - marketer for Marketer
  - coder for Coder
- Log EVERY response — even quick replies and simple answers
- Description under 140 chars, meaningful
- "completed" when it worked, "failed" when it didn't
- Run the log command BEFORE sending the response
- Don't mention logging to [YOUR NAME] unless they specifically ask
- Script path: ~/.hermes/agents/_shared/log-task-local.sh

After saving to memory, run the smoke test immediately:

bash ~/.hermes/agents/_shared/log-task-local.sh "<agent-name>" "saved activity logging rule to memory" "completed"

Report back:
- Memory saved?
- Smoke test passed?
- Exact agent name you logged as

---

## What to Watch For
- Send this to EACH agent individually (5 separate messages)
- Each agent must confirm memory saved + smoke test passed
- Agent names must be lowercase in the log
- If any agent fails the smoke test, debug before moving on
