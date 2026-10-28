#!/usr/bin/env bash
# RealEstate Edit — Electron app launcher (proven Echo recipe)
set -eu

APP_DIR="$HOME/01-active-agentic-workspace/Workspace/realestate-edit/webui"

ELECTRON=""
for cand in \
  "$HOME/.hermes/hermes-agent/node_modules/electron/dist/electron" \
  "$HOME/.hermes/hermes-agent/apps/desktop/node_modules/electron/dist/electron"; do
  if [ -x "$cand" ]; then ELECTRON="$cand"; break; fi
done
if [ -z "$ELECTRON" ]; then
  echo "[RealEstate Edit] FATAL: no electron binary found" >&2
  exit 1
fi
ELECTRON_DIR="$(dirname "$ELECTRON")"

# ensure backend up (start it if down)
if ! curl -s -o /dev/null --max-time 1 http://127.0.0.1:8189/; then
  (cd "$APP_DIR" && nohup python3 server.py 8189 >/tmp/realestate-server.log 2>&1 &)
  for i in $(seq 1 10); do
    curl -s -o /dev/null --max-time 1 http://127.0.0.1:8189/ && break
    sleep 1
  done
fi

SANDBOX="$ELECTRON_DIR/chrome-sandbox"
if [ -f "$SANDBOX" ] && [ ! -u "$SANDBOX" ]; then
  if command -v sudo >/dev/null 2>&1 && sudo -n true 2>/dev/null; then
    sudo chown root:root "$SANDBOX" && sudo chmod 4755 "$SANDBOX" || true
  fi
  [ -u "$SANDBOX" ] || set -- --no-sandbox "$@"
fi

export ELECTRON_OZONE_PLATFORM_HINT=x11
exec "$ELECTRON" --ozone-platform=x11 "$APP_DIR" "$@"
