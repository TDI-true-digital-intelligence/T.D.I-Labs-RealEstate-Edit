#!/usr/bin/env python3
"""realestate-edit server — port 8189.
Two engines: (1) Rust color engine (instant, always on), (2) ComfyUI Qwen-Image-2.1 AI edit (:8188).
No personal data, no auth by design (localhost only)."""
import json, os, re, subprocess, sys, time, urllib.request, uuid
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "work"
UPLOADS = Path.home() / "ComfyUI" / "input"
OUTPUTS = Path.home() / "ComfyUI" / "output"
RUST_CLI = ROOT.parent / "rust-src" / "target" / "release" / "realestate-cli"
COMFY = "http://127.0.0.1:8188"
PRESETS = ["bright-airy", "hdr-punch", "warm-dusk", "blue-sky-day", "natural-clean"]
AI_MODES = {
    "sky-blue":  "Replace the sky with a clear vivid blue sky with soft white clouds. Keep the house, trees, ground and everything else exactly the same. Photorealistic real estate photography.",
    "sky-dusk":  "Replace the sky with a warm golden dusk sky with soft orange gradient. Keep the house, trees, ground and everything else exactly the same. Photorealistic real estate photography.",
    "grass":     "Replace the lawn with a lush healthy vibrant green grass. Keep the house, sky, driveway and everything else exactly the same. Photorealistic real estate photography.",
    "remove-people": "Remove all people from the photo. Fill in the background naturally where they were. Keep everything else exactly the same. Photorealistic real estate photography.",
    "remove-animals": "Remove all animals and pets from the photo. Fill in the background naturally where they were. Keep everything else exactly the same. Photorealistic real estate photography.",
    "declutter": "Remove all clutter, bins, hoses, cables, toys and stray objects from the scene. Keep the house, sky, lawn and everything else exactly the same. Photorealistic real estate photography.",
    "virtual-furniture": "Furnish this empty room beautifully with modern neutral furniture: sofa, coffee table, rug, floor lamp. Photorealistic interior photography, real estate virtual staging.",
    "add-tv":    "Add a large modern flat-screen TV on the wall, switched on showing a colourful landscape screensaver. Keep everything else exactly the same. Photorealistic interior photography.",
    "replace-tv": "Replace the TV screen image with a bright colourful nature landscape. Keep the TV frame and everything else exactly the same. Photorealistic interior photography.",
    "replace-art": "Replace the artwork and pictures on the walls with bright modern abstract art. Keep the frames and everything else exactly the same. Photorealistic interior photography.",
    "brighten":  "Make this photo bright, airy and well-lit like a professional real estate listing photo. Increase brightness and lift shadows. Keep all content exactly the same.",
    "custom":    ""
}
for d in (WORK, UPLOADS, OUTPUTS):
    d.mkdir(parents=True, exist_ok=True)

def _cleanup_work(max_age_s=3600 * 24, max_files=200):
    """Keep the work dir bounded: delete files older than a day, cap total count (oldest first)."""
    try:
        files = sorted(WORK.glob("*-*.png"), key=lambda f: f.stat().st_mtime)
        import time as _t
        now = _t.time()
        for f in files:
            if now - f.stat().st_mtime > max_age_s:
                f.unlink(missing_ok=True)
        files = sorted(WORK.glob("*-*.png"), key=lambda f: f.stat().st_mtime)
        while len(files) > max_files:
            files.pop(0).unlink(missing_ok=True)
    except Exception:
        pass

import cloud_engines

def comfy_post(path, payload):
    req = urllib.request.Request(COMFY + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())

def comfy_get(path):
    try:
        return json.loads(urllib.request.urlopen(COMFY + path, timeout=30).read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {}  # unknown/purged id
        raise

def wait_prompt(pid, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        # /history/{pid}: present once queued, stays after completion
        h = comfy_get(f"/history/{pid}").get(pid)
        if h:
            if h.get("status", {}).get("status_str") == "error":
                return False
            if h.get("outputs"):
                return True
        time.sleep(2)
    return False

class H(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a): pass

    def do_GET(self):
        host = self.headers.get("Host", "")
        if host not in ("127.0.0.1:8189", "localhost:8189"):
            return self._send(403, {"error": "bad host"})

        p = self.path.split("?")[0]
        if p in ("/", "/index.html"):
            self._send(200, (ROOT / "index.html").read_bytes(), "text/html")
        elif p == "/app.js":
            self._send(200, (ROOT / "app.js").read_bytes(), "application/javascript")
        elif p == "/api/presets":
            self._send(200, {"presets": PRESETS, "ai_modes": list(AI_MODES), "comfy_up": self._comfy_up(), "cloud_profiles": cloud_engines.PROFILES})
        elif p.startswith("/out/"):
            name = p[5:]
            if not re.fullmatch(r"[0-9a-f]{10}-(out|ai)\.png", name):
                return self._send(400, {"error": "bad path"})
            f = WORK / name
            if f.exists():
                ctype = "image/png" if f.suffix == ".png" else "image/jpeg"
                self._send(200, f.read_bytes(), ctype)
            else:
                self._send(404, {"error": "not found"})
        elif p.startswith("/work/"):
            name = p[6:]
            if not re.fullmatch(r"[0-9a-f]{10}-(in|out)\.png", name):
                return self._send(400, {"error": "bad path"})
            f = WORK / name
            if f.exists():
                self._send(200, f.read_bytes(), "image/png")
            else:
                self._send(404, {"error": "not found"})
        else:
            self._send(404, {"error": "bad path"})

    def _comfy_up(self):
        try:
            comfy_get("/system_stats")
            return True
        except Exception:
            return False

    def do_POST(self):
        host = self.headers.get("Host", "")
        if host not in ("127.0.0.1:8189", "localhost:8189"):
            return self._send(403, {"error": "bad host"})

        p = self.path
        try:
            if p == "/api/grade":
                # JSON: {image_b64, preset} -> rust engine. preset may be "bright:0.5"
                cl = int(self.headers.get("Content-Length", 0))
                if cl > 60 * 1024 * 1024:
                    return self._send(413, {"error": "payload too large (max 60MB)"})
                body = json.loads(self.rfile.read(cl))
                import base64
                sid = uuid.uuid4().hex[:10]
                raw = base64.b64decode(body["image_b64"].split(",")[-1])
                src = WORK / f"{sid}-in.png"
                dst = WORK / f"{sid}-out.png"
                # normalize ANY format (jpeg/cr2/webp/heic) to PNG via Pillow before the Rust engine
                from PIL import Image
                import io as _io
                try:
                    im = Image.open(_io.BytesIO(raw)); im.load()
                except Exception:
                    # CR2/RAW fallback: rawpy if installed, else dcraw, else reject honestly
                    try:
                        import rawpy
                        with rawpy.imread(_io.BytesIO(raw)) as rw:
                            im = Image.fromarray(rw.postprocess())
                    except Exception:
                        return self._send(415, {"error": "unsupported image format (install rawpy for CR2/RAW)"})
                im.convert("RGB").save(src, "PNG")
                preset = str(body["preset"])
                import re as _re
                if not (_re.fullmatch(r"bright:-?\d+(\.\d+)?", preset) or preset in PRESETS):
                    return self._send(400, {"error": "bad preset"})
                r = subprocess.run([str(RUST_CLI), str(src), str(dst), preset],
                                   capture_output=True, text=True, timeout=120)
                if r.returncode != 0:
                    return self._send(500, {"error": r.stderr or "rust engine failed"})
                self._send(200, {"url": f"/work/{sid}-out.png", "engine": "rust"})
            elif p == "/api/ai":
                # JSON: {image_b64, mode, prompt?} -> comfyui qwen 2.1
                cl = int(self.headers.get("Content-Length", 0))
                if cl > 60 * 1024 * 1024:
                    return self._send(413, {"error": "payload too large (max 60MB)"})
                body = json.loads(self.rfile.read(cl))
                import base64
                sid = uuid.uuid4().hex[:10]
                src = UPLOADS / f"re_{sid}.png"
                # validate + normalize the image BEFORE handing bytes to ComfyUI (bomb/format guard)
                from PIL import Image as _I
                import io as _io2
                _I.MAX_IMAGE_PIXELS = 80_000_000  # hard pixel cap
                raw = base64.b64decode(body["image_b64"].split(",")[-1])
                try:
                    im = _I.open(_io2.BytesIO(raw)); im.load()
                    if im.width * im.height > 80_000_000:
                        return self._send(413, {"error": "image too large (80MP max)"})
                    im.convert("RGB").save(src, "PNG")
                except Exception as e:
                    return self._send(415, {"error": f"invalid image: {e}"})
                prompt_text = body.get("prompt") or AI_MODES.get(body["mode"], AI_MODES["sky-blue"])
                engine = body.get("engine", "auto")
                if engine.startswith("cloud:") or (engine == "auto" and not self._comfy_up()):
                    prof = engine.split(":", 1)[1] if ":" in engine else "glm-cloud"
                    fn, key = cloud_engines.get_engine(prof)
                    prompt_text = body.get("prompt") or AI_MODES.get(body["mode"], AI_MODES["sky-blue"])
                    # re-encode the validated image we already saved at src
                    out = WORK / f"{sid}-ai.png"
                    out.write_bytes(fn(key, src.read_bytes(), prompt_text))
                    _cleanup_work()
                    return self._send(200, {"url": f"/out/{sid}-ai.png", "engine": "cloud/" + prof, "prompt": prompt_text})
                wf = json.loads((ROOT.parent / "workflows" / "qwen21_turbo_edit_api.json").read_text())
                wf["4"]["inputs"]["image"] = src.name
                wf["6"]["inputs"]["prompt"] = prompt_text
                # match aspect: use source dims rounded to /32
                from PIL import Image
                with Image.open(src) as im:
                    w, h = im.size
                scale = (1024 * 1024 / (w * h)) ** 0.5
                wf["7"]["inputs"]["width"] = max(32, min(2048, int(w * scale) // 32 * 32))
                wf["7"]["inputs"]["height"] = max(32, min(2048, int(h * scale) // 32 * 32))
                wf["6"]["inputs"]["resolution"] = 1024
                r = comfy_post("/prompt", {"prompt": wf})
                pid = r["prompt_id"]
                if not wait_prompt(pid):
                    return self._send(500, {"error": "ComfyUI execution failed/timed out"})
                hist = comfy_get(f"/history/{pid}")
                entry = hist.get(pid, {})
                imgs = []
                for out in entry.get("outputs", {}).values():
                    imgs += out.get("images", [])
                if not imgs:
                    return self._send(500, {"error": "ComfyUI finished but no image returned"})
                fname = imgs[0]["filename"]
                out = WORK / f"{sid}-ai.png"
                out.write_bytes((OUTPUTS / fname).read_bytes())
                _cleanup_work()
                # free VRAM after the job (Qwen weights ~13GB — FPS is sacred)
                try:
                    comfy_post("/free", {"unload_models": True, "free_memory": True})
                except Exception:
                    pass
                self._send(200, {"url": f"/out/{sid}-ai.png", "engine": "qwen-image-2.1-turbo", "prompt": prompt_text})
            else:
                self._send(404, {"error": "bad path"})
        except Exception as e:
            self._send(500, {"error": str(e)})

if __name__ == "__main__":
    _cleanup_work()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8189
    print(f"realestate-edit server on :{port}")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
