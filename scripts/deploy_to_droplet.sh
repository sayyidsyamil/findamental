#!/usr/bin/env bash
set -euo pipefail

: "${DROPLET_HOST:?Please set DROPLET_HOST, e.g. export DROPLET_HOST=root@1.2.3.4}"

echo "Syncing Findamental code to $DROPLET_HOST..."
rsync -avz --delete \
    --exclude '.venv' --exclude '__pycache__' --exclude '.git' \
    --exclude 'hermes-agent' \
    --exclude 'data/demo_filings/*.pdf' \
    ./ "$DROPLET_HOST":/opt/findamental/

echo "Remote install/update complete. Start Hermes or your service on the droplet as configured."
