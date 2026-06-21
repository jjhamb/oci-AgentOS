# Prompt 29 — Agent Document Storage Protocol

**Phase:** 12 (Content and Document Storage)
**Send to:** All 5 agents (Telegram for Orchestrator, Discord for others)

---

When you produce any long-form document — articles, research reports, scripts, outlines, briefs, plans, transcripts, summaries, or any deliverable longer than ~15 lines — you must save it to your dedicated agent folder, not return it as a chat response.

Folder structure:

  /root/.hermes/content/
    ├── orchestrator/
    ├── analyst/
    ├── writer/
    ├── marketer/
    └── coder/

Each agent writes only to its own lowercase subfolder. Never write into another agent's folder.

Rules:

1. Save to your own folder only.
   Orchestrator → /root/.hermes/content/orchestrator/
   Analyst      → /root/.hermes/content/analyst/
   Writer       → /root/.hermes/content/writer/
   Marketer     → /root/.hermes/content/marketer/
   Coder        → /root/.hermes/content/coder/

2. Use markdown (.md) for every long-form document. No .txt, no inline chat dumps.

3. Filename convention: YYYY-MM-DD_short-kebab-case-title.md
   Example: 2026-05-01_competitor-scan.md
   Lowercase only, hyphens between words, no spaces, no special characters.

4. First line must be a top-level heading (# Title) that matches the document's purpose. The Content tab uses this as the display title — make it descriptive and human-readable, not a slug.

5. Structure the body with proper markdown: ## and ### for sections, **bold** for emphasis, `inline code` for technical terms, fenced code blocks with language tags for code, and - bullet lists where they help. The Content tab renders all of this — write so it reads well in the preview panel.

6. What counts as long-form (save to folder): articles, research summaries, scripts, outreach drafts, strategy docs, meeting notes, technical guides, post-mortems, anything intended to be reread or reused.

7. What does not (return inline in chat): single-sentence answers, quick status updates, one-line confirmations, tool call results, conversational replies.

8. One document per file. If a task produces multiple deliverables, save each as its own file.

9. Never overwrite silently. If a filename collides, append -v2, -v3, or use a more specific title.

10. Stay in your lane. Write content that fits your role. If a task falls outside your role, hand it off rather than writing it yourself.

11. After saving, confirm in chat with your agent name, the full path, and a one-line summary. Example:

    Analyst → /root/.hermes/content/analyst/2026-05-01_competitor-scan.md — competitive analysis of 6 platforms.

This protocol exists because the Content tab in the dashboard reads directly from /root/.hermes/content/. If you return long-form work in chat instead of saving it there, it doesn't show up in the dashboard, can't be previewed, edited, or downloaded, and effectively gets lost.

Create your subfolder now if it doesn't exist. Save a short test document to confirm the protocol is working. Confirm with the standard one-line format above.

---

## What to Watch For
- Send to ALL 5 agents individually
- Each agent must create its subfolder and save a test document
- Test document should follow the naming convention and have a proper # heading
- Each agent confirms with the standard one-line format
- Verify files exist on disk after: `ls -la /root/.hermes/content/*/`
