#!/bin/bash
set -e

LOG_FILE="/opt/truhlik/deploy.log"

# Přesměruj stdout i stderr do logu
exec >> "$LOG_FILE" 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

APP_DIR="/opt/truhlik/app"
VENV_DIR="/opt/truhlik/venv"
DEPLOY_DIR="$APP_DIR/deploy"
LOCAL_DEPLOY="$DEPLOY_DIR/deploy.sh"
SYSTEMD_SERVICE="/etc/systemd/system/truhlik.service"
DEPLOY_TARGET="/opt/truhlik/deploy.sh"

log "===== DEPLOY START ====="

cd "$APP_DIR"

log "[CHECK] Fetching origin..."
git fetch origin main

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    log "[CHECK] No update needed."
    log "===== DEPLOY END ====="
    exit 0
fi

log "[DEPLOY] Updating to latest main..."
git reset --hard origin/main

log "[DEPLOY] Installing dependencies..."
"$VENV_DIR/bin/pip" install --no-cache-dir -r requirements.txt

log "[DEPLOY] Restarting service..."
sudo systemctl restart truhlik

# ---- Aktualizace deploy skriptu, pokud se změnil ----
if ! cmp -s "$LOCAL_DEPLOY" "$DEPLOY_TARGET"; then
    log "[DEPLOY] Updating deploy script..."
    sudo cp "$LOCAL_DEPLOY" "$DEPLOY_TARGET"
    sudo chmod +x "$DEPLOY_TARGET"
fi

# ---- Aktualizace systemd služby, pokud se změnila ----
if [ -f "$DEPLOY_DIR/truhlik.service" ]; then
    if ! cmp -s "$DEPLOY_DIR/truhlik.service" "$SYSTEMD_SERVICE"; then
        log "[DEPLOY] Updating systemd service..."
        sudo cp "$DEPLOY_DIR/truhlik.service" "$SYSTEMD_SERVICE"
        sudo systemctl daemon-reload
    fi
fi

log "===== DEPLOY END ====="
