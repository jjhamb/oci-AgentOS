# Phase 5 Checklist: Activity Logging (Prompts 13–16)

## After Prompt 13 — Build the Logging Backbone
- [ ] ~/.hermes/agent-logs.db created with correct schema
- [ ] Indexes on agent_name, status, created_at DESC
- [ ] ~/.hermes/agents/_shared/log-task-local.sh created
- [ ] Script is executable (chmod +x)
- [ ] Test command inserts one row successfully
- [ ] sqlite3 verification query shows the test entry
- [ ] Python stdlib only (no pip packages)

## After Prompt 14 — Roll Out Logging to All Agents
- [ ] ~/.hermes/agents/_shared/LOGGING_POLICY.md created
- [ ] Orchestrator's AGENTS.md has logging pointer
- [ ] Analyst's AGENTS.md has logging pointer
- [ ] Writer's AGENTS.md has logging pointer
- [ ] Marketer's AGENTS.md has logging pointer
- [ ] Coder's AGENTS.md has logging pointer
- [ ] Orchestrator (Telegram) can reach the log script
- [ ] Smoke test shows entries from all 5 agents

## After Prompt 15 — Reinforce Logging with Each Agent
- [ ] Each agent received the prompt individually
- [ ] Each agent confirmed memory saved
- [ ] Each agent passed smoke test
- [ ] Agent names are lowercase in logs

## After Prompt 16 — Monthly Log Retention
- [ ] ~/.hermes/agents/_shared/cleanup-logs.sh created
- [ ] Script is executable
- [ ] RETENTION_DAYS set to 30
- [ ] Cron scheduled: 1st of month at 03:00
- [ ] Test run shows rows deleted + remaining count
- [ ] Deletion and notification are independent
- [ ] If Telegram fails, cleanup still completes

## Post-Phase Audit
```
Audit the Activity Logging build against the original prompt spec. Find:
1. Missing features / incomplete implementations
2. Bugs / broken reactivity / console errors
3. Deviations from design system
4. Data source mismatches

Give me a single copy-paste prompt I can use in a NEW session to fix everything found.
```
