# Prompt 28 — Content Tab (Backend + UI)

**Phase:** 12 (Content and Document Storage)
**Send to:** Coder

---

**⚠️ BACKUP index.html and server.py before this prompt!**

Build the content tab:

BACKEND — add these endpoints to server.py:

  GET /api/content — returns a JSON list of every .md file under /root/.hermes/content/. Each entry: { agent, filename, title (first H1), modified_at, size }.

  GET /api/content/get?path= — returns the raw markdown content of a single file. Validate the path is under /root/.hermes/content/ — reject any traversal attempts.

  POST /api/content/save — body { path, content }. Same path validation. Writes the content back to disk and updates modified_at.

UI — a two-column layout: a 280px sidebar on the left and a content panel filling the rest.

  SIDEBAR — group documents by agent. For each agent, a mono uppercase agent name header in their accent color, then a list of their documents. Each row: title (Inter Tight, 13px), filename below in muted mono. Clicking a row selects it. The selected row has a subtle white background and a 2px left border in the agent's color.

  PREVIEW PANEL — header with the document title (Inter Tight 22px), the agent badge, modified date, and two buttons: "View" and "Edit".

  View mode: renders the markdown into HTML (use marked.min.js — already loaded by the page) to parse and render. Style headings and code blocks to match the dashboard palette.

  Edit mode: replaces the rendered div with a full-width textarea containing the raw markdown. Save button calls POST /api/content/save with the textarea value, then returns to view mode. Cancel restores the previous view without saving.

  Empty state (no doc selected): centered muted mono text "Select a document to read".

Wire the Content tab into the existing switchTab() function — add:

  if (name === 'content') loadContentDocs();

alongside the existing overview/tutorial hooks. Without this the tab renders blank.

Auto-select the first document in the list if one exists.

---

## What to Watch For
- Backend adds 3 new endpoints to server.py
- Path validation is critical — reject directory traversal attacks
- Sidebar groups docs by agent with accent colors
- View mode renders markdown as HTML (using marked.js)
- Edit mode shows raw markdown in textarea
- Content tab must be wired into switchTab() — otherwise it renders blank
- Auto-select first document if any exist
