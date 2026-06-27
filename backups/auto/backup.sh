#!/bin/bash
# Auto-backup script — run before every change
# Captures current state of served files into git-tracked backups/auto/
set -e
PROJECT_DIR="/home/jayant/Desktop/Hermes-AgentOS-Dashboard"
cd "$PROJECT_DIR"

TIMESTAMP=$(date -u +%Y-%m-%dT%H-%M-%S)
mkdir -p backups/auto
cp backend/index.html "backups/auto/index_${TIMESTAMP}.html"
cp backend/server.py "backups/auto/server_${TIMESTAMP}.py"
git add backups/auto/
git commit -m "auto: pre-change backup ${TIMESTAMP}" --allow-empty
git push || true
echo "BACKUP_OK: backups/auto/${TIMESTAMP}"
