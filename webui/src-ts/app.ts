// realestate-edit — TypeScript source (app.ts)
// The served app.js is the compiled plain-JS form of this file (identical logic).
// Build: npx esbuild src-ts/app.ts --outfile=../app.js --target=es2020
// Types for the API surface:

export interface PresetsResponse {
  presets: string[];        // rust engine profiles: bright-airy | hdr-punch | warm-dusk | blue-sky-day | natural-clean
  ai_modes: string[];       // qwen modes: sky-blue | sky-dusk | grass | declutter | custom
  comfy_up: boolean;        // ComfyUI :8188 reachable
}

export interface EditResult {
  url: string;              // result image path on this server
  engine: 'rust' | 'qwen-image-2.1-turbo';
  prompt?: string;          // the AI prompt used (ai path)
}

let IMG: string | null = null; // dataURL
const $ = (id: string) => document.getElementById(id) as HTMLElement;

async function boot(): Promise<void> {
  const r = (await fetch('/api/presets').then(r => r.json())) as PresetsResponse;
  ($('preset') as HTMLSelectElement).innerHTML = r.presets.map(p => `<option>${p}</option>`).join('');
  ($('aimode') as HTMLSelectElement).innerHTML = r.ai_modes.map(m => `<option>${m}</option>`).join('');
  $('status').textContent = r.comfy_up ? 'ComfyUI: UP ✓ (AI edits available)' : 'ComfyUI: DOWN (color profiles still work)';
}

function loadFile(f: File | undefined): void {
  if (!f) return;
  const rd = new FileReader();
  rd.onload = () => { IMG = rd.result as string; ($('before') as HTMLImageElement).src = IMG!; ($('before') as HTMLElement).hidden = false; $('status').textContent = 'loaded ' + f.name; };
  rd.readAsDataURL(f);
}

async function post<T>(url: string, body: object): Promise<T> {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json().catch(() => { throw new Error('bad response'); });
  if (!r.ok) throw new Error((j as any).error || String(r.status));
  return j as T;
}

function showResult(j: EditResult): void {
  const after = $('after') as HTMLImageElement;
  after.src = j.url + '?t=' + Date.now();
  after.hidden = false;
  ($('dl') as HTMLAnchorElement).href = j.url;
  ($('dl') as HTMLElement).hidden = false;
  $('status').textContent = '✓ engine=' + j.engine + (j.prompt ? ' · ' + j.prompt.slice(0, 80) : '');
}

async function grade(): Promise<void> {
  if (!IMG) { $('status').textContent = 'load an image first'; return; }
  $('status').textContent = 'grading (rust engine)…';
  try { showResult(await post<EditResult>('/api/grade', { image_b64: IMG, preset: ($('preset') as HTMLSelectElement).value })); }
  catch (e: any) { $('status').textContent = '✗ ' + e.message; }
}

async function aiedit(): Promise<void> {
  if (!IMG) { $('status').textContent = 'load an image first'; return; }
  const mode = ($('aimode') as HTMLSelectElement).value;
  $('status').textContent = 'AI editing (qwen-image-2.1, ~30-90s)…';
  try {
    const body: any = { image_b64: IMG, mode };
    if (mode === 'custom') body.prompt = ($('aiprompt') as HTMLInputElement).value;
    showResult(await post<EditResult>('/api/ai', body));
  } catch (e: any) { $('status').textContent = '✗ ' + e.message; }
}
