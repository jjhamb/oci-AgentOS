#!/bin/bash
# ──────────────────────────────────────────────────────────────
# ROLLBACK: Pre-escalating state (Option B — Orchestrator pending/escalating)
# Created: 2026-06-28T21:27:00Z
# Purpose: Restore server.py and index.html to state before
#          orch_pending_task / orch_all_blocked / escalating features
# ──────────────────────────────────────────────────────────────

set -euo pipefail

DASHBOARD="/home/jayant/Desktop/Hermes-AgentOS-Dashboard"</longcat_arg_key>
<longcat_arg_value>replace
BACKUP_DIR="${DASHBOARD}/backups/auto"

# Find the latest pre-escalating backups
SERVER_BACKUP=$(ls -t ${BACKUP_DIR}/server_*_pre_escalating.py 2>/dev/null | head -1)
INDEX_BACKUP=$(ls -t ${BACKUP_DIR}/index_*_pre_escalating.html 2>/dev/null | head -1)

if [ -z "$SERVER_BACKUP" ] || [ -z "$INDEX_BACKUP" ]; then
    echo "ERROR: Pre-escalating backup not found in ${BACKUP_DIR}"
    ls -la ${BACKUP_DIR}/*pre_escalating* 2>/dev/null || echo "(no matches)"
    exit 1
fi

echo "=== ROLLBACK: Pre-escalating state ==="
echo "Server backup: ${SERVER_BACKUP}"
echo "Index backup:  ${INDEX_BACKUP}"
echo ""

# Create restore point (current state before rolling back)
TIMESTAMP=$(date -u +%Y-%m-%dT%H-%M-%S)
cp "${DASHBOARD}/backend/server.py" "${BACKUP_DIR}/server_${TIMESTAMP}_pre_rollback_to_pre_escalating.py"
cp "${DASHBOARD}/backend/index.html" "${BACKUP_DIR}/index_${TIMESTAMP}_pre_rollback_to_pre_escalating.html"
echo "[1/3] Safety backup created: ${TIMESTAMP}_pre_rollback_to_pre_escalating.*"

# Restore
cp "$SERVER_BACKUP" "${DASHBOARD}/backend/server.py"
cp "$INDEX_BACKUP" "${DASHBOARD}/backend/index.html"
echo "[2/3] Restored pre-escalating versions"

# Restart
pkill -f "server.py" 2>/dev/null && echo "[3/3] Server stopped (will auto-restart)" || echo "[3/3] Server not running"

echo ""
echo "=== ROLLBACK COMPLETE ==="
echo "Changes reverted:"
echo "  - Removed: orch_pending_task flag"
echo "  - Removed: orch_all_blocked flag"  
echo "  - Removed: status='escalating' state"
echo "  - Removed: .status-escalating CSS"
echo ""
echo "Server.py restored from: ${SERVER_BACKUP}"
echo "Index.html restored from: ${INDEX_BACKUP}"
echo ""
echo "To start server: cd ${DASHBOARD}/backend && python3 server.py &"
