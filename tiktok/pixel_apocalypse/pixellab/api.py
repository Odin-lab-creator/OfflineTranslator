"""Мини-клиент PixelLab API v2.

Авторизация: ключ подставляет сетевой прокси среды (сетевой секрет для api.pixellab.ai).
Запасной вариант — переменная окружения PIXELLAB_API_KEY. Ключ в коде и в репозитории не хранится.
"""
import base64
import io
import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://api.pixellab.ai/v2"


def _req(method, path, body=None, raw=False, timeout=120):
    url = path if path.startswith("http") else BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        r.add_header("Content-Type", "application/json")
    key = os.environ.get("PIXELLAB_API_KEY")
    if key:
        r.add_header("Authorization", f"Bearer {key}")
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            payload = resp.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} → {e.code}: {e.read()[:500].decode(errors='replace')}") from None
    return payload if raw else json.loads(payload)


def get(path, **kw):
    return _req("GET", path, **kw)


def post(path, body):
    return _req("POST", path, body)


def balance():
    return get("/balance")


def wait_job(job_id, every=5, limit=900):
    t0 = time.time()
    while True:
        j = get(f"/background-jobs/{job_id}")
        st = j.get("status")
        if st in ("completed", "failed"):
            return j
        if time.time() - t0 > limit:
            raise TimeoutError(f"job {job_id} всё ещё {st}")
        time.sleep(every)


def b64png(img):
    """PIL.Image → {'type': 'base64', 'base64': ...} для полей Base64Image."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return {"type": "base64", "base64": base64.b64encode(buf.getvalue()).decode()}
