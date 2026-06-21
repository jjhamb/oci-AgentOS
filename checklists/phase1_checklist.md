# Phase 1 Checklist: Orchestrator Setup (Prompts 1–2)

## After Prompt 1 — Create Orchestrator
- [ ] Orchestrator acknowledges its role as cross-platform coordinator
- [ ] Orchestrator names all 4 specialist agents (Analyst, Writer, Marketer, Coder)
- [ ] Orchestrator confirms hierarchy: Owner > Orchestrator > Specialists
- [ ] Owner name is saved for introductions to other agents

## After Prompt 2 — Operating Rules
- [ ] Progress reporting rule saved (Step X of Y format)
- [ ] Approval rule saved (plan before execute)
- [ ] Communication rules saved (short, clear, no fluff)
- [ ] Delegation rules saved (one-line, structured briefs)
- [ ] Context window rule saved (200K token warning)
- [ ] Orchestrator confirms all rules saved

## Post-Phase Audit
Run in a fresh Hermes session:
```
Audit the Orchestrator Setup build against the original prompt spec. Find:
1. Missing features / incomplete implementations
2. Bugs / broken reactivity / console errors
3. Deviations from design system
4. Data source mismatches

Give me a single copy-paste prompt I can use in a NEW session to fix everything found.
```
