#!/bin/bash
set -e

LOG_FILE="/opt/truhlik/deploy.log"
exec >> "$LOG_FILE" 2>&1

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

FORCE=false
while [ $# -gt 0 ]; do
    case "$1" in
        -f|--force)
            FORCE=true
            shift
            ;;
        *)
            log "[WARN] Unknown argument: $1"
            shift
            ;;
    esac
done

APP_DIR="/opt/truhlik/app"
VENV_DIR="/opt/truhlik/venv"
DEPLOY_DIR="$APP_DIR/deploy"
LOCAL_DEPLOY="$DEPLOY_DIR/deploy.sh"
DEPLOY_TARGET="/opt/truhlik/deploy.sh"

CODE_CHANGED=false

deploy_service() {
    local SERVICE_NAME="$1"
    local LOCAL_SERVICE="$DEPLOY_DIR/$SERVICE_NAME"
    local SYSTEMD_SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

    if [ -f "$LOCAL_SERVICE" ]; then
        if [ "$FORCE" = true ] || [ ! -f "$SYSTEMD_SERVICE_PATH" ] || ! cmp -s "$LOCAL_SERVICE" "$SYSTEMD_SERVICE_PATH"; then
            log "[DEPLOY] Installing $SERVICE_NAME..."
            sudo cp "$LOCAL_SERVICE" "$SYSTEMD_SERVICE_PATH"
            log "[SYSTEMD] Reloading daemon..."
            sudo systemctl daemon-reload
        else
            log "[CHECK] $SERVICE_NAME is up to date."
        fi
    else
        log "[WARN] $LOCAL_SERVICE not found; skipping $SERVICE_NAME update."
    fi

    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        log "[CHECK] $SERVICE_NAME already enabled."
    else
        log "[SYSTEMD] Enabling $SERVICE_NAME..."
        sudo systemctl enable "$SERVICE_NAME"
    fi

    if systemctl is-active --quiet "$SERVICE_NAME"; then
        if [ "$CODE_CHANGED" = true ] || [ "$FORCE" = true ]; then
            log "[SYSTEMD] Restarting $SERVICE_NAME to apply changes..."
            sudo systemctl restart "$SERVICE_NAME"
        else
            log "[CHECK] $SERVICE_NAME already running."
        fi
    else
        log "[SYSTEMD] Starting $SERVICE_NAME..."
        sudo systemctl start "$SERVICE_NAME"
    fi
}

log "===== DEPLOY START ====="
cd "$APP_DIR"

log "[CHECK] Fetching origin..."
git fetch origin main

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ] && [ "$FORCE" = false ]; then
    log "[CHECK] No update needed."
else
    if [ "$FORCE" = true ]; then
        log "[FORCE] Deployment forced."
    fi

    log "[DEPLOY] Updating to latest main..."
    git reset --hard origin/main
    CODE_CHANGED=true

    log "[DEPLOY] Installing dependencies..."
    "$VENV_DIR/bin/pip" install --no-cache-dir -r requirements.txt  --extra-index-url https://www.piwheels.org/simple
fi

if [ "$FORCE" = true ] || ! cmp -s "$LOCAL_DEPLOY" "$DEPLOY_TARGET"; then
    log "[DEPLOY] Updating deploy script..."
    sudo cp "$LOCAL_DEPLOY" "$DEPLOY_TARGET"
    sudo chmod +x "$DEPLOY_TARGET"
fi

# --- Deploy services ---
deploy_service "truhlik.service"
deploy_service "truhlik-api.service"

log "===== DEPLOY END ====="
