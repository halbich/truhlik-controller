#!/bin/bash
set -e

LOG_FILE="/var/log/truhlik-deploy.log"
APP_DIR="/opt/truhlik/app"
VENV_DIR="/opt/truhlik/venv"
DEPLOY_DIR="$APP_DIR/deploy"
LOCAL_DEPLOY="$DEPLOY_DIR/deploy.sh"
SYSTEMD_SERVICE="/etc/systemd/system/truhlik.service"
DEPLOY_TARGET="/opt/truhlik/deploy.sh"

# Vytvoření logu s právy, pokud neexistuje
sudo mkdir -p /var/log
sudo touch "$LOG_FILE"
sudo chown "$USER":"$USER" "$LOG_FILE"

# Zápis logu s časovou značkou
exec > >(sudo tee -a "$LOG_FILE") 2>&1

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ===== DEPLOY START ====="

cd "$APP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CHECK] Fetching origin..."
git fetch origin main

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CHECK] No update needed."
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ===== DEPLOY END ====="
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEPLOY] Updating to latest main..."
git reset --hard origin/main

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEPLOY] Installing dependencies..."
"$VENV_DIR/bin/pip" install --no-cache-dir -r requirements.txt

echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEPLOY] Restarting service..."
sudo systemctl restart truhlik

# ---- Aktualizace deploy skriptu, pokud se změnil ----
if ! cmp -s "$LOCAL_DEPLOY" "$DEPLOY_TARGET"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEPLOY] Updating deploy script..."
    sudo cp "$LOCAL_DEPLOY" "$DEPLOY_TARGET"
    sudo chmod +x "$DEPLOY_TARGET"
fi

# ---- Aktualizace systemd služby, pokud se změnila ----
if [ -f "$DEPLOY_DIR/truhlik.service" ]; then
    if ! cmp -s "$DEPLOY_DIR/truhlik.service" "$SYSTEMD_SERVICE"; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEPLOY] Updating systemd service..."
        sudo cp "$DEPLOY_DIR/truhlik.service" "$SYSTEMD_SERVICE"
        sudo systemctl daemon-reload
    fi
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ===== DEPLOY END ====="
