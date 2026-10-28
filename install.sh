#!/usr/bin/env bash
# RealEstate Edit — clean-machine installer (no personal data, no accounts)
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HERE"
BIN_DIR="$HOME/.local/bin"
DATA_DIR="$HOME/.local/share/realestate-edit"

echo "== RealEstate Edit installer =="

# 1) Rust engine
if command -v cargo >/dev/null; then
  echo "[1/5] building Rust engine…"
  (cd "$APP_DIR/rust-src" && cargo build --release)
else
  echo "[1/5] cargo not found — install rustup first; skipping engine build"
fi

# 2) server + CLI symlinks
mkdir -p "$BIN_DIR" "$DATA_DIR"
ln -sf "$APP_DIR/webui" "$DATA_DIR/app"
cat > "$BIN_DIR/realestate-edit-server" <<EOF
#!/usr/bin/env bash
exec python3 "$APP_DIR/webui/server.py" 8189
EOF
cat > "$BIN_DIR/realestate-edit" <<EOF
#!/usr/bin/env bash
exec "$APP_DIR/webui/launch.sh" "\$@"
EOF
chmod +x "$BIN_DIR/realestate-edit-server" "$BIN_DIR/realestate-edit"

# 3) icons (9 sizes, own name — never touch sibling apps)
for s in 16 32 48 64 128 256 512; do
  mkdir -p "$HOME/.local/share/icons/hicolor/${s}x${s}/apps"
  cp "$APP_DIR/webui/icon.png" "$HOME/.local/share/icons/hicolor/${s}x${s}/apps/realestate-edit.png"
done

# 4) .desktop entry
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/realestate-edit.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=RealEstate Edit
GenericName=Real estate photo editor
Comment=AI sky, grass & color profiles for real estate photos
Exec=$BIN_DIR/realestate-edit
Icon=realestate-edit
Terminal=false
Categories=Graphics;Photography;
StartupWMClass=realestate-edit
EOF

# 5) systemd user service (server)
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/realestate-edit.service" <<EOF
[Unit]
Description=RealEstate Edit server (port 8189)
After=network.target

[Service]
ExecStart=/usr/bin/python3 $APP_DIR/webui/server.py 8189
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
systemctl --user daemon-reload
systemctl --user enable --now realestate-edit.service 2>/dev/null || true

echo "== done =="
echo "  server : systemctl --user status realestate-edit  (http://127.0.0.1:8189)"
echo "  app    : realestate-edit  (or app grid: RealEstate Edit)"
echo "  AI mode: needs ComfyUI on :8188 with Qwen-Image 2.1 weights (see README)"
