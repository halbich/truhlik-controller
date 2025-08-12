#!/bin/bash
set -e

APP_DIR="/opt/truhlik/app"
VENV_DIR="/opt/truhlik/venv"

cd "$APP_DIR"
echo "[DEPLOY] Fetching main..."
git fetch origin main
git reset --hard origin/main

echo "[DEPLOY] Installing dependencies..."
"$VENV_DIR/bin/pip" install --no-cache-dir -r requirements.txt

echo "[DEPLOY] Restarting service..."
sudo systemctl restart truhlik
