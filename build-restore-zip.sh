#!/usr/bin/env bash
# RealEstate Edit — restore-quality build (app + mechanics only, NO personal data)
set -eu
SRC="$HOME/01-active-agentic-workspace/Workspace/realestate-edit"
OUT="$HOME/01-active-agentic-workspace/Workspace/realestate-edit-restore-quality"
VER="$(date +%Y%m%d-%H%M%S)"
STAGE="$OUT/realestate-edit-$VER"
mkdir -p "$STAGE"

# app source — exclude rust build artifacts, work files, test outputs
rsync -a --exclude '.git' --exclude 'rust-src/target' --exclude 'webui/work' --exclude 'test/*.png' --exclude '__pycache__' --exclude '*.pyc' "$SRC/" "$STAGE/"

# self-contained restore instructions
cat > "$STAGE/RESTORE.md" <<'EOF'
# Restore Guide — RealEstate Edit

1. Unzip anywhere. `cd realestate-edit-*`
2. `./install.sh` — builds Rust engine, installs icons, .desktop, systemd service (server :8189).
3. Open http://127.0.0.1:8189 or launch "RealEstate Edit" from the app grid.

## AI mode (optional)
- Install ComfyUI (github.com/comfyanonymous/ComfyUI) + torch cu128 venv.
- Download from HuggingFace `Comfy-Org/Qwen-Image-2.1`:
  - diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors
  - text_encoders/qwen3vl_8b_w4a8.safetensors
  - vae/qwen_image_2.1_vae_bf16.safetensors
- Start ComfyUI on :8188. The app auto-detects it.

## Dash squares (Echo boxes only)
- 3333: `python3 wire_dash.py 3333` then `systemctl --user restart echo-agent-os`
- 9999: `python3 wire_dash.py 9999` then `systemctl --user restart echo-agent-os-lite`

No personal data in this archive: no names, accounts, keys, or user files.
EOF

cd "$OUT" && zip -qr "realestate-edit-restore-quality-$VER.zip" "realestate-edit-$VER"
sha256sum "realestate-edit-restore-quality-$VER.zip" > "realestate-edit-restore-quality-$VER.zip.sha256"
echo "BUILT: $OUT/realestate-edit-restore-quality-$VER.zip"
ls -la "$OUT" | tail -3
