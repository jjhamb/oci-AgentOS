# Prompt 26 — Tasks Tab (Personal Operator Board)

**Phase:** 11 (Tasks and Schedule Tab)
**Send to:** Coder

---

**⚠️ BACKUP index.html and server.py before this prompt!**

Build the tasks tab:

LAYOUT — 3-column grid using GlassCard per column (Pending, In Progress, Done). Each column has mono header with status name, count Badge, and "+ Add task" button in Pending only.

TASK CARDS — each is a GlassCard({ children }) showing:

  — Title in var(--font-display)
  — Priority chip (low/medium/high) on right, color-coded
  — Optional notes (muted, 2 lines max)
  — Footer with relative time and quick-action buttons: ◀ ▶ ✕

ADD-TASK MODAL — clicking "+ Add task" opens an inline form with title, priority dropdown (low/medium/high), and notes. Save calls POST /api/board with the values; the new card appears in Pending without a page refresh.

INTERACTIONS — optimistic updates: ▶ moves card to next status, ◀ moves back, ✕ deletes. Revert on API failure.

Data: re-fetch /api/board after every write. Independent from SSE snapshot.

---

## What to Watch For
- 3 columns: Pending, In Progress, Done
- "+ Add task" only in Pending column
- Task cards show title, priority, notes, relative time
- ▶ moves forward, ◀ moves back, ✕ deletes
- Optimistic updates — UI updates immediately, reverts on failure
- Data comes from /api/board (separate from SSE snapshot)
