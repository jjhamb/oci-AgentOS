# Prompt 7 — Full Content Pipeline

**Phase:** 3 (Agent Collaboration)
**Send to:** Orchestrator

---

Set up a supervisor flow with this sequence:

1. **Analyst** researches the topic first
2. **Analyst** passes findings to **Writer**
3. **Writer** writes the blog/content
4. **Writer** passes content to **Marketer**
5. **Marketer** creates social media posts from the content
6. **Marketer** builds the marketing/promotion strategy from the same content
7. **Marketer** delivers the final promotion plan

This should work as both an automatic pipeline when triggered, and manually when I ask.

Add a command I can use to kick off the full pipeline:

Run full pipeline on [topic]

Confirm once the supervisor flow and pipeline command are set up.

---

## What to Watch For
- Pipeline must be sequential: Analyst → Writer → Marketer
- Each step should pass output to the next agent
- The "Run full pipeline on [topic]" command must be registered
- Coder is NOT in this pipeline (coder handles technical tasks separately)
