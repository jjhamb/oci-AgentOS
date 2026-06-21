# Prompt 21 — Dashboard Skeleton

**Phase:** 7 (Frontend Design System)
**Send to:** Coder

---

Import `tokens.css` and `components.js`

Build the index.html skeleton for the full dashboard shell - just the visual shell, no content inside any tab yet: fixed nav bar with Hermes brand mark (gradient ring + pulsing dot), five tab buttons (Overview, Agents, Tasks, Schedule, Content) in a pill, active tab as solid white pill with dark text, and a status pill on the right with pulsing mint dot, "All systems operational", and a live 24-hour clock.

Use only:

- GlassCard({ ... }) for panel backgrounds
- Badge({ text: 'v1.0', color: 'var(--text-muted)', variant: 'subtle' }) in the nav
- All colors from var(--brand-*), var(--bg-*), var(--text-*), var(--agent-*), var(--status-*)
- All spacing from var(--space-*)
- All radii from var(--radius-*)
- var(--font-display) for headings/numbers, var(--font-mono) for labels/code
- var(--blur-heavy) for backdrop blur

No data, no SSE, no JavaScript beyond the clock and tab switching. Just the shell. The Content tab panel can be an empty placeholder div for now — it gets filled later.

Now that the Skeleton is built, let's Access it and tweak it to our taste. You can ask coder for access instructions, or use the command below to create a SSH tunnel

Terminal window

# On your local machine (Mac/Linux/WSL):
ssh -L 51763:127.0.0.1:51763 root@<your-vps-ip>

---

## What to Watch For
- This is the VISUAL SHELL only — no data binding yet
- Nav bar should have: brand mark, 5 tabs, version badge, status pill, live clock
- Active tab should be highlighted (white pill style)
- Tab switching should work (clicking tabs shows/hides panels)
- No SSE, no API calls, no data — just the layout
- After this, you can access the dashboard via SSH tunnel to verify the shell looks right
