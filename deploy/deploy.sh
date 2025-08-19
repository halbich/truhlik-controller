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
SYSTEMD_SERVICE="/etc/systemd/system/truhlik.service"
DEPLOY_TARGET="/opt/truhlik/deploy.sh"

# --- truhlik-api.service paths ---
API_SERVICE_NAME="truhlik-api.service"
LOCAL_API_SERVICE="$DEPLOY_DIR/$API_SERVICE_NAME"
SYSTEMD_API_SERVICE="/etc/systemd/system/$API_SERVICE_NAME"

UPDATED_SYSTEMD=false
CODE_CHANGED=false

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
    "$VENV_DIR/bin/pip" install --no-cache-dir -r requirements.txt
fi

if [ "$FORCE" = true ] || ! cmp -s "$LOCAL_DEPLOY" "$DEPLOY_TARGET"; then
    log "[DEPLOY] Updating deploy script..."
    sudo cp "$LOCAL_DEPLOY" "$DEPLOY_TARGET"
    sudo chmod +x "$DEPLOY_TARGET"
fi


# Zajištění, že startup.sh existuje
if [ ! -f "$APP_DIR/startup.sh" ]; then
    log "[DEPLOY] Creating startup.sh..."
    cat <<'EOF' > "$APP_DIR/startup.sh"
#!/bin/bash
exec /opt/truhlik/venv/bin/python -u /opt/truhlik/app/main.py
EOF
    chmod +x "$APP_DIR/startup.sh"
fi

# --- Deploy truhlik-api.service ---
if [ -f "$LOCAL_API_SERVICE" ]; then
    if [ "$FORCE" = true ] || [ ! -f "$SYSTEMD_API_SERVICE" ] || ! cmp -s "$LOCAL_API_SERVICE" "$SYSTEMD_API_SERVICE"; then
        log "[DEPLOY] Installing $API_SERVICE_NAME..."
        sudo cp "$LOCAL_API_SERVICE" "$SYSTEMD_API_SERVICE"
        UPDATED_SYSTEMD=true
    else
        log "[CHECK] $API_SERVICE_NAME is up to date."
    fi
else
    log "[WARN] $LOCAL_API_SERVICE not found; skipping $API_SERVICE_NAME update."
fi

if [ "$UPDATED_SYSTEMD" = true ]; then
    log "[SYSTEMD] Reloading daemon..."
    sudo systemctl daemon-reload
fi

# Enable a start API služby
if systemctl is-enabled --quiet "$API_SERVICE_NAME"; then
    log "[CHECK] $API_SERVICE_NAME already enabled."
else
    log "[SYSTEMD] Enabling $API_SERVICE_NAME..."
    sudo systemctl enable "$API_SERVICE_NAME"
fi

if systemctl is-active --quiet "$API_SERVICE_NAME"; then
    if [ "$CODE_CHANGED" = true ] || [ "$FORCE" = true ] || [ "$UPDATED_SYSTEMD" = true ]; then
        log "[SYSTEMD] Restarting $API_SERVICE_NAME to apply changes..."
        sudo systemctl restart "$API_SERVICE_NAME"
    else
        log "[CHECK] $API_SERVICE_NAME already running."
    fi
else
    log "[SYSTEMD] Starting $API_SERVICE_NAME..."
    sudo systemctl start "$API_SERVICE_NAME"
fi

log "===== DEPLOY END ====="