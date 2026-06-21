# Phase 3 Checklist: Agent Collaboration (Prompts 5–8)

## After Prompt 5 — Routing Table & Slash Commands
- [ ] Routing table created with 3-5 natural language examples per agent
- [ ] /analyst slash command works
- [ ] /writer slash command works
- [ ] /marketer slash command works
- [ ] /coder slash command works
- [ ] Fallback behavior defined (ask or route to Orchestrator)

## After Prompt 6 — Shared Team Awareness
- [ ] All 5 agents received team structure info
- [ ] Owner role defined (highest authority)
- [ ] Orchestrator role defined (system-wide coordinator)
- [ ] All 4 specialists know their roles and teammates
- [ ] Handoff behavior confirmed (agents redirect, don't absorb)

## After Prompt 7 — Full Content Pipeline
- [ ] Pipeline sequence: Analyst → Writer → Marketer
- [ ] "Run full pipeline on [topic]" command registered
- [ ] Pipeline works both automatically and manually

## After Prompt 8 — Test Full Pipeline
- [ ] Analyst produced research findings
- [ ] Writer produced blog post (800+ words)
- [ ] Marketer produced social media posts + promotion strategy
- [ ] No agent went silent or skipped steps
- [ ] Output quality is acceptable

## Post-Phase Audit
```
Audit the Agent Collaboration build against the original prompt spec. Find:
1. Missing features / incomplete implementations
2. Bugs / broken reactivity / console errors
3. Deviations from design system
4. Data source mismatches

Give me a single copy-paste prompt I can use in a NEW session to fix everything found.
```
