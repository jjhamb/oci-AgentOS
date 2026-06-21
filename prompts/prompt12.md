# Prompt 12 — Bind Agents to Channels

**Phase:** 4 (Discord Integration)
**Send to:** Orchestrator

---

Bind each of the 4 agents to their dedicated channel using the IDs you just captured.

Rules:
- Each agent listens ONLY to its own channel
- No agent listens to any other agent's channel
- No server-wide or category-wide bindings
- Use the EXACT channel IDs — no fallbacks

Bindings:
- Analyst → analyst-briefs channel
- Writer → writer-scripts channel
- Marketer → marketer-marketing channel
- Coder → coder-build channel

Confirm each binding as a clean list: agent name → channel name → channel ID.

Test: I'll go into each channel and ask "Who are you?" Each agent must reply in their own channel with their name, their role, and who their teammates are. If any agent responds in the wrong channel or fails to respond in its own, fix it before we move on.

Discord health check: Use `/status` to check Discord token usage and verify the bot is connected and responsive. If responses get weird or the context window feels full, use `/new` to start a fresh session.

---

## What to Watch For
- Each agent responds ONLY in its own channel — no cross-talk
- Test with "Who are you?" in each channel
- If an agent responds in wrong channel, rebinding is needed
- Save channel IDs in a safe place for reference
