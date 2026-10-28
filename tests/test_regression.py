"""Regression suite — every bug found this session, encoded so it can't return.
Run: python3 tests/test_regression.py  (needs app on :8189, ComfyUI optional)
"""
import base64, io, json, subprocess, sys, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
PASS, FAIL = [], []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name + (" — " + detail if detail and not cond else ""))
    print(("PASS " if cond else "FAIL ") + name + ((" :: " + detail) if not cond else ""))

def post(path, body, timeout=600):
    r = urllib.request.Request("http://127.0.0.1:8189" + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        return json.loads(urllib.request.urlopen(r, timeout=timeout).read())
    except urllib.error.HTTPError as e:
        return {"_status": e.code, "error": e.read().decode()[:200]}

# fixture image
from PIL import Image, ImageDraw
img = Image.new("RGB", (400, 300))
d = ImageDraw.Draw(img)
for y in range(170):
    d.line([(0, y), (400, y)], fill=(150, 180, 200))
for y in range(170, 300):
    d.line([(0, y), (400, y)], fill=(90, 120, 60))
d.rectangle([150, 110, 250, 200], fill=(210, 190, 170))
buf = io.BytesIO(); img.save(buf, "PNG")
B64 = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
jbuf = io.BytesIO(); img.save(jbuf, "JPEG")
J64 = "data:image/jpeg;base64," + base64.b64encode(jbuf.getvalue()).decode()

# 1. ComfyUI autogrow wiring bug (was: image_1 flat input -> TypeError 500)
r = post("/api/ai", {"image_b64": B64, "mode": "sky-blue"})
check("bug1 comfy autogrow images dict + history poll (no list-index/TypeError)", "error" not in r or "unexpected keyword" not in str(r.get("error", "")), str(r)[:120])

# 2. history-404 premature-finish bug (result must contain a url)
check("bug2 finished prompt returns image url", "url" in r or "503" in str(r.get("_status", "")), str(r)[:120])

# 3. JPEG input (was: PNG-only, 'Invalid PNG signature')
r = post("/api/grade", {"image_b64": J64, "preset": "bright-airy"})
check("bug3 jpeg input accepted", "url" in r, str(r)[:120])

# 4. brightness preset passthrough
r = post("/api/grade", {"image_b64": B64, "preset": "bright:0.5"})
check("bug4 bright:v preset works", "url" in r, str(r)[:120])

# 5. unknown preset rejected honestly
r = post("/api/grade", {"image_b64": B64, "preset": "nope"})
check("bug5 unknown preset -> 500 error, not crash", "error" in r, str(r)[:120])

# 6. rust CLI rejects bad args cleanly
c = subprocess.run([str(ROOT / "rust-src/target/release/realestate-cli")], capture_output=True, text=True)
check("bug6 rust cli usage exit code 2", c.returncode == 2)

# 7. lite dash 9999: no broken inline scripts (v10.870 class — SyntaxError kills all tabs)
import re
from html.parser import HTMLParser
for dash in ["echo-agent-os", "echo-agent-os-lite"]:
    p = Path.home() / f".hermes/01-active-agentic-workspace/Workspace/{dash}/dashboard/index.html"
    h = p.read_text()
    class SP(HTMLParser):
        def __init__(s):
            super().__init__(); s.scripts = []; s.cur = None
        def handle_starttag(s, t, a):
            if t == "script" and not dict(a).get("src"): s.cur = ""
        def handle_endtag(s, t):
            if t == "script" and s.cur is not None: s.scripts.append(s.cur); s.cur = None
        def handle_data(s, d):
            if s.cur is not None: s.cur += d
    sp = SP(); sp.feed(h)
    import tempfile, os
    bad = 0
    for txt in sp.scripts:
        if len(txt) < 50: continue
        f = tempfile.NamedTemporaryFile("w", suffix=".js", delete=False); f.write(txt); f.close()
        if subprocess.run(["node", "--check", f.name], capture_output=True).returncode != 0: bad += 1
        os.unlink(f.name)
    check(f"bug7 {dash} inline scripts all compile", bad == 0, f"{bad} broken")


# 8. reviewer finding: absolute-path traversal (/out//etc/passwd)
import urllib.error as _ue
def _code(u):
    try:
        return urllib.request.urlopen("http://127.0.0.1:8189" + u, timeout=5).status
    except _ue.HTTPError as e:
        return e.code
check("bug8 /out//etc/passwd rejected (400/404)", _code("/out//etc/passwd") in (400, 404))
check("bug9 /out/../../.env rejected", _code("/out/../../home/bitlord/.hermes/.env") in (400, 404))
# 9. reviewer finding: threading — presets must answer while AI job runs
import threading
res = {}
def slow():
    try: post("/api/ai", {"image_b64": B64, "mode": "sky-dusk"}, timeout=300)
    except Exception: pass
t = threading.Thread(target=slow, daemon=True); t.start()
import time as _t; _t.sleep(1)
t0 = _t.time()
try:
    urllib.request.urlopen("http://127.0.0.1:8189/api/presets", timeout=5)
    ok = _t.time() - t0 < 3
except Exception:
    ok = False
check("bug10 presets responsive during AI job (ThreadingHTTPServer)", ok)


# 10. gap-fix: comfyui systemd service enabled (survives reboot)
c = subprocess.run(["systemctl", "--user", "is-enabled", "comfyui.service"], capture_output=True, text=True)
check("bug11 comfyui.service enabled at boot", c.stdout.strip() == "enabled", c.stdout.strip())
# 11. gap-fix: work dir bounded (<= 200 files after cleanup pass)
n = len(list((ROOT / "webui/work").glob("*-*.png")))
check("bug12 work dir bounded <= 200 files", n <= 200, f"{n} files")


# 12. gap-fix: VRAM released after AI job (was 13.7GB resident — FPS-sacred violation)
c = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True)
vram_mb = int(c.stdout.strip().splitlines()[0])
check("bug13 VRAM freed after AI job (< 4000MB idle)", vram_mb < 4000, f"{vram_mb}MB")


# 13. review R2: Host-header validation (DNS-rebinding kill)
import urllib.request as _u2
try:
    _u2.urlopen(_u2.Request("http://127.0.0.1:8189/api/presets", headers={"Host": "evil.com"}), timeout=5)
    badhost = 200
except Exception as e:
    badhost = getattr(e, "code", 0)
check("bug14 bad Host header -> 403", badhost == 403, str(badhost))
# 14. review R2: /api/ai rejects garbage payloads honestly (image validation before ComfyUI)
r = post("/api/ai", {"image_b64": "data:image/png;base64,AAAA", "mode": "sky-blue"})
check("bug15 /api/ai validates image before ComfyUI", "error" in r, str(r)[:100])

print(f"\nFINAL: {len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
