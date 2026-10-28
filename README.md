# RealEstate Edit — T.D.I Lab

Open-source real-estate photo editor: **sky replacement, grass greening, and real-estate color profiles.**
Two engines, one app:

| Engine | What | Speed |
|---|---|---|
| **Rust color engine** | 5 real-estate profiles (Bright & Airy, HDR Punch, Warm Dusk, Blue Sky Day, Natural Clean) — sky tint, grass green, white balance, vibrance, local contrast | instant (<1s) |
| **Qwen-Image 2.1 Turbo** (ComfyUI) | True AI edits: replace sky, green the lawn, declutter the scene, custom prompts | 30–90s |

100% local. No cloud. No telemetry. No personal data — the app ships with zero names, accounts, or keys.

## Parts

```
realestate-edit/
├── webui/           # the app (Python stdlib server :8189 + frontend + Electron shell)
│   ├── server.py    # API: /api/grade (rust), /api/ai (ComfyUI :8188)
│   ├── index.html / app.js
│   ├── src-ts/app.ts  # TypeScript source of app.js
│   ├── main.js / launch.sh / package.json / icon.png  # Ubuntu desktop app
├── rust-src/        # Rust color engine (realestate-engine lib + realestate-cli)
├── workflows/       # ComfyUI API workflow (Qwen-Image 2.1 Turbo edit)
├── wire_dash.py     # wires the square+page into dash 3333 / 9999
└── install.sh       # clean-machine installer
```

## Install (Ubuntu 24.04)

```bash
./install.sh          # builds the Rust engine, installs icons + .desktop, systemd services
```

Requirements: Python 3.11+, Rust (cargo), Node (only for the Electron shell, optional), ComfyUI + Qwen-Image 2.1 weights (optional, for AI mode — see below).

### AI mode weights (optional)
Place in ComfyUI `models/` (from `Comfy-Org/Qwen-Image-2.1` on HuggingFace):
- `diffusion_models/qwen_image_2.1_turbo_int8_convrot.safetensors`
- `text_encoders/qwen3vl_8b_w4a8.safetensors`
- `vae/qwen_image_2.1_vae_bf16.safetensors`

## Run

```bash
realestate-edit-server &      # or: systemctl --user start realestate-edit.service
realestate-edit               # desktop app (Electron shell)
# browser: http://127.0.0.1:8189
```

## Use

1. Drop a photo in.
2. **Color profile** → pick preset → Apply (instant Rust).
3. **AI edit** → pick mode (sky-blue / sky-dusk / grass / declutter / custom) → Run (Qwen 2.1).

## Dashboards

The square `RealEstate Edit` is wired into Echo Agent OS (:3333) and Agentic OS Lite (:9999) — the page embeds this app via same-origin proxy `/realestate/`.

## Engine detail (Rust)

Sky region = top 45% of frame, luminance-gated (catches grey/blown sky, spares roofs).
Grass region = bottom 45%, green-dominance-gated (spares driveways).
Profiles adjust: sky tint + boost, grass green shift, white balance, exposure, vibrance, unsharp local contrast.

## License

MIT — © T.D.I Lab 2026. Qwen-Image weights follow their own research license (Qwen). No personal data anywhere in this repo.

## Legal
MIT © 2026 Robert Shields Jr. McDougall. See LICENSE + AI-ASSISTANCE.md. Qwen-Image weights = separate Qwen research license. Not financial or real-estate advice.

## Cloud engine profiles (GLM) — no local model needed

The AI modes now run on **cloud profiles** — anyone with a GLM API key can connect:

```
export REALESTATE_GLM_API_KEY=sk-...   # Z.AI key with image-API credits
# optional: REALESTATE_GLM_MODEL (default glm-image)
```

- Engine selector in the UI: **auto** (local ComfyUI if running → cloud fallback) or **GLM Cloud** directly.
- Uses Z.AI `POST /v1/images/edits` (OpenAI-compatible) — GLM-Image does true image-to-image editing: your photo + "replace the sky with a clear blue sky" → edited photo. Same task class as local Qwen-Image 2.1; the prompt library is shared.
- ~$0.015/image (Z.AI pricing).
- **Custom endpoint profile** for WaveSpeed `z-ai/glm-image/edit`, self-hosted `sglang serve zai-org/GLM-Image` (:30000/v1/images/edits), or OpenAI gpt-image — set `REALESTATE_CUSTOM_BASE_URL` + `REALESTATE_CUSTOM_API_KEY` (+ `REALESTATE_CUSTOM_MODEL`).

Errors are honest: no key → tells you the env var; no credits → passes the API message through.
