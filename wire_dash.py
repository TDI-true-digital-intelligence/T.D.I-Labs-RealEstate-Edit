#!/usr/bin/env python3
"""Wire realestate-edit square + page into a dash (3333 or 9999).
Pattern proven by SPINE Console (v10.820). One asset: button + view + hide-list entry + enter hook + iframe page.
Inserts BEFORE the SPINE tab button; view inserted before SPINE view; API proxy for /api/realestate/*.
"""
import re, sys, subprocess

dash = sys.argv[1]
paths = {
    "3333": ("os.path.expanduser("~/.hermes/01-active-agentic-workspace/Workspace")/echo-agent-os/dashboard", "echo-agent-os.service"),
    "9999": ("os.path.expanduser("~/.hermes/01-active-agentic-workspace/Workspace")/echo-agent-os-lite/dashboard", "echo-agent-os-lite.service"),
}
root, unit = paths[dash]
idx = f"{root}/index.html"
srv = f"{root}/server.py"
html = open(idx).read()
MARK = "realestate-edit square"

if MARK in html:
    print("already wired"); sys.exit(0)

subprocess.run(["git", "-C", root, "add", "-A"], check=True)
subprocess.run(["git", "-C", root, "commit", "-m", f"checkpoint before realestate square ({dash})", "--allow-empty"], check=True)

# 1) square button — anchor: full SPINE tab button tag
BTN_ANCHOR = re.search(r'<button class="nav-tab top-sq" id="tab-spine".*?</button>', html, re.S).group(0)
RE_BTN = ('<button class="nav-tab top-sq" id="tab-realestate" onclick="setTab(\'realestate\')" '
          'title="RealEstate Edit — AI sky, grass & color profiles (Rust + Qwen-Image 2.1)">'
          '<svg class="icn" width="34" height="34" style="color:#34d399;filter:drop-shadow(0 0 6px rgba(52,211,153,.55)) drop-shadow(0 1px 2px rgba(2,6,23,.9))" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>'
          '<span class="sq-label">RealEstate Edit</span></button>\n        ')
html = html.replace(BTN_ANCHOR, RE_BTN + BTN_ANCHOR, 1)

# 2) hide-list entries (both sweep lists)
html, n = re.subn(r"(\['brief','adhd'[^]]*)'spine'", r"\1'spine','realestate'", html, count=0)
print("hide-list inserts:", n)

# 3) view — insert before the SPINE view
VIEW_ANCHOR = re.search(r'<div id="view-spine".*?</div>', html, re.S).group(0)
# find the full line containing the opening of view-spine
spine_line_start = html.index('<div id="view-spine"')
RE_VIEW = '''<!-- realestate-edit square: AI + Rust real estate photo editing (app on :8189) -->
    <div id="view-realestate" class="hidden eng-wrap" style="flex-direction:column;max-height:none">
      <div class="eng-welcome-title" style="font-size:46px">REAL<span style="background:linear-gradient(90deg,#34d399,#38bdf8);-webkit-background-clip:text;background-clip:text;color:transparent">ESTATE</span> EDIT</div>
      <div style="font-family:var(--font-display);font-weight:400;font-size:15px;letter-spacing:.05em;color:var(--muted);margin-top:6px">Sky · Grass · Color profiles — Rust engine (instant) + Qwen-Image 2.1 AI (ComfyUI :8188). App: http://127.0.0.1:8189</div>
      <iframe src="/realestate/" style="flex:1;min-height:640px;width:100%;border:1px solid var(--card-border);border-radius:12px;background:var(--card);margin-top:12px" title="RealEstate Edit"></iframe>
    </div>

    '''
html = html[:spine_line_start] + RE_VIEW + html[spine_line_start:]

# 4) enter hook next to spine enter hook
hook = "if(id==='spine') { try{ spineEnter(); }catch(e){} }"
if hook in html:
    html = html.replace(hook, hook + "\n  if(id==='realestate') { try{ console.log('realestate enter'); }catch(e){} }", 1)
    print("enter hook wired")

open(idx, "w").write(html)

# 5) server.py: proxy /realestate/* to :8189 — insert next to spine tags route
spysrc = open(srv).read()
PROXY = '''        elif path.startswith('/realestate/'):
            sub = path[len('/realestate/'):] or 'index.html'
            try:
                import urllib.request as _u
                rq = _u.Request('http://127.0.0.1:8189/' + sub)
                body = _u.urlopen(rq, timeout=10).read()
                ctype = 'text/html' if sub.endswith('.html') else ('application/javascript' if sub.endswith('.js') else 'image/png')
                self.send_response(200); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)
            except Exception as e:
                self.send_response(502); self.send_header('Content-Type', 'application/json'); self.end_headers(); self.wfile.write(json.dumps({'error': str(e)}).encode())
'''
anchor = "elif path == '/api/spine/tags':"
if anchor in spysrc:
    spysrc = spysrc.replace(anchor, PROXY + "        " + anchor, 1)
    open(srv, "w").write(spysrc)
    print("server proxy wired")
else:
    print("WARN: spine tags anchor not found in server.py")

print("DONE", dash)
