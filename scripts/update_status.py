#!/usr/bin/env python3
"""Update STATUS.md with current progress"""
with open('/home/jayant/.hermes/agents/Orchestrator/STATUS.md', 'r') as f:
    content = f.read()

# Update Phase 11 and 12 status
content = content.replace(
    '|||| Phase 11 — Tasks + Schedule | 26–27 | ❌ Not done |',
    '|||| Phase 11 — Tasks + Schedule | 26–27 | ✅ Complete (Tasks: 6-column kanban, /api/kanban live polling. Schedule: Hermes + System job sections, /api/cron) |'
)
content = content.replace(
    '|||| Phase 12 — Content Tab | 28–29 | ❌ Not done |',
    '|||| Phase 12 — Content Tab | 28–29 | ✅ Complete (File browser with sidebar + resizable split pane, preview for md/docx/xlsx/pdf/png/code, edit+save, download) |'
)

# Update tab status table
content = content.replace(
    '|| Tasks | 26 | ✅ Complete (standalone — 6-column kanban, live polling, agent colors, priority badges. Fixed: integer priority handling, removed duplicate status-strip, col min-height 500px, doubled label fonts) |',
    '|| Tasks | 26 | ✅ Complete — MERGED into index.html (6-column kanban, /api/kanban live polling, agent colors, priority badges) |'
)
content = content.replace(
    '|| Schedule | 27 | ❌ Not done |',
    '|| Schedule | 27 | ✅ Complete — MERGED into index.html (Hermes + System job sections, /api/cron, owner badges, cron schedule + English description) |'
)
content = content.replace(
    '|| Content | 28–29 | ❌ Not done |',
    '|| Content | 28–29 | ✅ Complete — MERGED into index.html (File browser, resizable split pane, preview for md/docx/xlsx/pdf/png/code, edit+save, download) |'
)

# Add Terminal tab
content = content.replace(
    '|| Content | 28–29 | ✅ Complete — MERGED into index.html (File browser, resizable split pane, preview for md/docx/xlsx/pdf/png/code, edit+save, download) |',
    '|| Content | 28–29 | ✅ Complete — MERGED into index.html (File browser, resizable split pane, preview for md/docx/xlsx/pdf/png/code, edit+save, download) |\n|| Terminal | Extra | ✅ Complete — MERGED into index.html (Quick-action buttons, command exec via /api/terminal/exec, history, cwd tracking) |'
)

# Update Phase 4 dashboard status
content = content.replace(
    '|| **Additive tabs (v2.0)** | 🔶 **IN PROGRESS** | Agents tab ✅ (tile diagram, curved SVG lines, glow states, activity log, detail panel); Tasks/Schedule/Content — prompts 26–29 pending |',
    '|| **Additive tabs (v2.0)** | ✅ **COMPLETE** | All 6 tabs live: Overview, Agents, Tasks (kanban), Schedule (cron), Content (file browser), Terminal (command exec). All merged into index.html. |'
)

# Update last updated
from datetime import datetime
content = content.replace(
    '**Last Updated:** 2026-06-21',
    f'**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M")}'
)

with open('/home/jayant/.hermes/agents/Orchestrator/STATUS.md', 'w') as f:
    f.write(content)

print("STATUS.md updated")
