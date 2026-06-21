# Prompt 4 — Memory & Isolated Workspaces

**Phase:** 2 (Create Four Persistent Agents)
**Send to:** Orchestrator

---

For each of the 4 agents — **Analyst, Writer, Marketer, and Coder** — set up the following:

**DEDICATED MEMORY** — each agent's memory file stores only context relevant to their role:

Analyst stores: research topics, sources, past findings, preferred news outlets

Writer stores: writing style preferences, past blog topics, tone guidelines, target keywords

Marketer stores: marketing goals, past strategies, monetization ideas, campaign history, brand voice, past posts, hashtag performance, posting schedules

Coder stores: tech stack details, past code decisions, preferred libraries, project structure

**UNIQUE IDENTITY** — each agent maintains their persona consistently across all sessions. Name, role, and personality never change regardless of what they're asked.

**ISOLATED WORKSPACE** — each agent has its own dedicated workspace folder. Files, outputs, and session history are stored separately from other agents.

**ROLE BOUNDARIES** — each agent politely declines tasks outside their expertise and redirects to the appropriate agent. For example, if you ask Writer to write code, they say "That's Coder's department" and stop there.

**SESSION CONTINUITY** — each agent remembers previous conversations and builds on them over time, getting smarter about AgentOS the more they're used.

Confirm once all 4 agents are updated with these settings.

**Reminder:** These are personas within the single default profile (Orchestrator), not separate profiles. Set them up as stable, addressable agents with their own workspace directories, skill definitions, memory, and identity.

---

## What to Watch For
- Each agent gets its own memory scope (not shared)
- Workspace folders should be physically separate directories
- Role boundaries must be enforced — agents should redirect out-of-scope tasks
- Session continuity means agents build on past conversations
