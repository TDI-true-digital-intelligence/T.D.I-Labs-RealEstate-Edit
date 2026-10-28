// realestate-edit app.js — frontend logic (vanilla TS-style JS, compiled via esbuild optional)
// State: one image at a time; grade = rust engine; ai = comfyui qwen 2.1.
let IMG = null; // dataURL
const $ = id => document.getElementById(id);

async function boot() {
  const r = await fetch('/api/presets').then(r => r.json());
  $('preset').innerHTML = r.presets.map(p => `<option>${p}</option>`).join('');
  $('aimode').innerHTML = r.ai_modes.map(m => `<option>${m}</option>`).join('');
  $('status').textContent = r.comfy_up ? 'ComfyUI: UP ✓ (AI edits available)' : 'ComfyUI: DOWN (color profiles still work)';
}

$('drop').onclick = () => $('file').click();
$('file').onchange = e => loadFile(e.target.files[0]);
$('drop').ondragover = e => { e.preventDefault(); $('drop').classList.add('on'); };
$('drop').ondragleave = () => $('drop').classList.remove('on');
$('drop').ondrop = e => { e.preventDefault(); $('drop').classList.remove('on'); loadFile(e.dataTransfer.files[0]); };

function loadFile(f) {
  if (!f) return;
  const rd = new FileReader();
  rd.onload = () => { IMG = rd.result; $('before').src = IMG; $('before').hidden = false; $('after').hidden = true; $('after-ph').style.display = 'flex'; $('status').textContent = 'loaded ' + f.name; };
  rd.readAsDataURL(f);
}

async function post(url, body) {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => ({ error: 'bad response' }));
  if (!r.ok) throw new Error(j.error || r.status);
  return j;
}

function showResult(j) {
  $('after').src = j.url + '?t=' + Date.now();
  $('after').hidden = false;
  $('after-ph').style.display = 'none';
  $('dl').href = j.url;
  $('dl').hidden = false;
  $('status').textContent = '✓ engine=' + j.engine + (j.prompt ? ' · ' + j.prompt.slice(0, 80) : '');
}

$('brightness').oninput = e => $('brval').textContent = (e.target.value > 0 ? '+' : '') + (e.target.value / 100).toFixed(2);

async function brighten() {
  if (!IMG) return ($('status').textContent = 'load an image first');
  const v = ($('brightness').value / 100).toFixed(2);
  $('status').textContent = 'brightness ' + v + ' (rust engine)…';
  try { showResult(await post('/api/grade', { image_b64: IMG, preset: 'bright:' + v })); }
  catch (e) { $('status').textContent = '✗ ' + e.message; }
}

async function grade() {
  if (!IMG) return ($('status').textContent = 'load an image first');
  $('status').textContent = 'grading (rust engine)…';
  try { showResult(await post('/api/grade', { image_b64: IMG, preset: $('preset').value })); }
  catch (e) { $('status').textContent = '✗ ' + e.message; }
}

async function aiedit() {
  if (!IMG) return ($('status').textContent = 'load an image first');
  const mode = $('aimode').value;
  $('status').textContent = 'AI editing (qwen-image-2.1, ~30-90s)…';
  try {
    const body = { image_b64: IMG, mode, engine: $('aiengine').value };
    if (mode === 'custom') body.prompt = $('aiprompt').value;
    showResult(await post('/api/ai', body));
  } catch (e) { $('status').textContent = '✗ ' + e.message; }
}

boot();
