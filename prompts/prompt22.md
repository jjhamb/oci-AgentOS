# Prompt 22 — Backup Protocol & Version Badge

**Phase:** 8 (Backup Protocol)
**Send to:** Coder

---

1. BACKUP FOLDER

   Create a dedicated backups folder at:
   /root/agent-mission-control/backups/

   From this point forward, before making any change to index.html or server.py, always save a backup of the current file into that folder first.

   Backup naming convention:
     index_v{version}_{YYYY-MM-DDThh-mm}.html
     server_v{version}_{YYYY-MM-DDThh-mm}.py

   Never skip the backup step.

   Take the first backup now and confirm the full path.

2. VERSION BADGE

   Use Badge({ text: 'v1.0', color: 'var(--text-muted)', variant: 'subtle' }) — place it in the nav after the "/ ORCHESTRATOR" label. Increment it manually each time a meaningful set of changes is complete.

---

## ⚠️ CRITICAL — This is your safety net
- From NOW ON, before EVERY change to index.html or server.py, a backup MUST be taken
- One bad edit = white screen. The backup is your undo button.
- This protocol is NOT optional — it's the most important step in the entire build
- After this prompt, Prompts 23-29 will iterate on the frontend. BACKUP BEFORE EACH ONE.
