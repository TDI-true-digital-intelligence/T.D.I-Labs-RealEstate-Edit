"""Cloud engine profiles for RealEstate Edit — plug in your API key and go.

What was copied from the local Qwen-Image 2.1 build: the ENGINE-AGNOSTIC prompt
library (AI_MODES in server.py — real-estate-tuned edit instructions, field-tested
2026-10-28) and the app contract: edit(image_png, prompt) -> png bytes.

Profiles (OpenAI-images-compatible /v1/images/edits):
  glm-cloud — Z.AI GLM-Image. TRUE image-to-image editing:
              image + "replace the sky with..." -> edited image.
              Same task class as local Qwen-Image 2.1 (both are instruction-edit models).
              API: https://api.z.ai/api  (docs.z.ai/guides/image/glm-image)
              env: REALESTATE_GLM_API_KEY (fallback GLM_API_KEY)
  custom    — any OpenAI-compatible endpoint (OpenAI gpt-image, WaveSpeed GLM-Image-Edit,
              self-hosted sglang serve zai-org/GLM-Image, etc.)
              env: REALESTATE_CUSTOM_BASE_URL + REALESTATE_CUSTOM_API_KEY (+ optional
                   REALESTATE_CUSTOM_MODEL, default "glm-image")
"""
import base64, json, os, urllib.error, urllib.request


class CloudEngineError(Exception):
    pass


def _edit(base_url, api_key, model, image_png, prompt, timeout=300):
    """POST {base}/v1/images/edits (multipart: model, image, prompt, response_format=b64_json)."""
    boundary = "----realestate-edit-7d1f"
    b64 = base64.b64encode(image_png).decode()
    parts = []
    for name, value in (("model", model), ("prompt", prompt), ("response_format", "b64_json")):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="input.png"\r\n'
        f'Content-Type: image/png\r\n\r\n'.encode() + image_png + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        base_url.rstrip("/") + "/v1/images/edits", body,
        {"Authorization": f"Bearer {api_key}",
         "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            out = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise CloudEngineError(f"{base_url} -> {e.code}: {e.read().decode()[:300]}")
    for item in out.get("data", []):
        if item.get("b64_json"):
            return base64.b64decode(item["b64_json"])
        if item.get("url"):
            with urllib.request.urlopen(item["url"], timeout=timeout) as r:
                return r.read()
    raise CloudEngineError("no image in response: " + json.dumps(out)[:200])


def glm_edit(api_key, image_png, prompt):
    return _edit("https://api.z.ai/api", api_key, os.environ.get("REALESTATE_GLM_MODEL", "glm-image"), image_png, prompt)


def custom_edit(api_key, image_png, prompt):
    return _edit(os.environ["REALESTATE_CUSTOM_BASE_URL"], api_key,
                 os.environ.get("REALESTATE_CUSTOM_MODEL", "glm-image"), image_png, prompt)


def get_engine(name):
    """Return (profile, api_key) or raise CloudEngineError with the exact env var to set."""
    if name == "glm-cloud":
        key = os.environ.get("REALESTATE_GLM_API_KEY") or os.environ.get("GLM_API_KEY")
        if not key:
            raise CloudEngineError("set REALESTATE_GLM_API_KEY (or GLM_API_KEY) to use GLM cloud")
        return glm_edit, key
    if name == "custom":
        key = os.environ.get("REALESTATE_CUSTOM_API_KEY")
        base = os.environ.get("REALESTATE_CUSTOM_BASE_URL")
        if not (key and base):
            raise CloudEngineError("set REALESTATE_CUSTOM_API_KEY + REALESTATE_CUSTOM_BASE_URL for a custom engine")
        return custom_edit, key
    raise CloudEngineError(f"unknown cloud profile: {name}")


PROFILES = {
    "glm-cloud": {
        "label": "GLM Cloud (Z.AI) — GLM-Image true image-edit",
        "env": "REALESTATE_GLM_API_KEY",
        "price": "~$0.015/image",
        "docs": "https://docs.z.ai/guides/image/glm-image",
    },
    "custom": {
        "label": "Custom OpenAI-compatible endpoint (WaveSpeed / self-hosted sglang GLM-Image / OpenAI)",
        "env": "REALESTATE_CUSTOM_API_KEY + REALESTATE_CUSTOM_BASE_URL",
        "docs": "https://github.com/zai-org/GLM-Image",
    },
}
