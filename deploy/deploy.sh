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

log "===== DEPLOY START ====="
cd "$APP_DIR"

log "[CHECK] Fetching origin..."
git fetch origin main

LOCAL_COMMIT=$(git rev-parse HEAD)
REMOTE_COMMIT=$(git rev-parse origin/main)

if [ "$LOCAL_COMMIT" = "$REMOTE_COMMIT" ] && [ "$FORCE" = false ]; then
    log "[CHECK] No update needed."
    log "===== DEPLOY END ====="
    exit 0
fi

if [ "$FORCE" = true ]; then
    log "[FORCE] Deployment forced."
fi

log "[DEPLOY] Updating to latest main..."
git reset --hard origin/main

log "[DEPLOY] Installing dependencies..."
"$VENV_DIR/bin/pip" install --no-cache-dir -r requirements.txt

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



log "===== DEPLOY END ====="
