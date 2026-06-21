# Prompt 27 — Schedule Tab

**Phase:** 11 (Tasks and Schedule Tab)
**Send to:** Coder

---

**⚠️ BACKUP index.html and server.py before this prompt!**

Build the schedule tab, a read only view for every cron job on the server

DATA — d.crons from cron_jobs(). Each entry: source, schedule, command, owner ("hermes" or "system"), friendly description.

LAYOUT — two sections: HERMES JOBS and SYSTEM JOBS. Each a mono eyebrow and GlassCard per job.

JOB CARDS — each GlassCard({ children }) with:

  — Owner Badge (violet for hermes, muted for system) top-right
  — Command in var(--font-mono), 13px, truncated with hover full-text
  — "SCHEDULE" cron expression · "NEXT RUN" relative time
  — Plain-English schedule description in muted
  — Source file path at very bottom

Empty state: "No scheduled jobs in this group." centered in muted mono.

Read-only — no writes.

---

## What to Watch For
- Two sections: HERMES JOBS and SYSTEM JOBS
- Each job card shows: owner badge, command, schedule, next run, description
- Commands should be truncated (hover for full text)
- Plain-English schedule (e.g., "Every day at 3:00 AM")
- Read-only — no edit/delete buttons
