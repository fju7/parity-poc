"""One HTTP getter for every registry, with a record/replay cache.

When CACHE_DIR is set, a response is stored under sha1(url) and served from
there next time. The golden-set tests replay from tests/verify/fixtures so
they run offline and deterministically; the recording script populated
that directory once, live, and a person read what came back before it
became a control.
"""
from __future__ import annotations

import gzip
import hashlib
import os
import time
import urllib.request
from pathlib import Path

UA = {"User-Agent": "civicscale-verify (resolve/fetch/bind; contact fred.ugast@uspv.co)",
      "Accept-Encoding": "gzip"}
CACHE_DIR: Path | None = Path(os.environ["VERIFY_CACHE_DIR"]) if os.environ.get("VERIFY_CACHE_DIR") else None
PAUSE = 0.15


def _key(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()


def get(url: str, timeout: int = 45) -> tuple[int, bytes, dict]:
    """(status, body, headers). Status 0 means no response at all. Never raises."""
    if CACHE_DIR:
        p = CACHE_DIR / (_key(url) + ".bin")
        m = CACHE_DIR / (_key(url) + ".meta")
        if p.exists():
            meta = dict(line.split("\t", 1) for line in m.read_text().splitlines() if "\t" in line) if m.exists() else {}
            return int(meta.get("status", "200")), p.read_bytes(), meta
    status, body, headers = 0, b"", {}
    # Retry on throttling and transient failure. On 2026-09-14 a re-check
    # minutes after a publish saw 15 of 17 sources "unreachable" because
    # Europe PMC throttled ~60 calls in a minute; one 429 is not link rot.
    for attempt, wait in enumerate((0, 3, 8, 20)):
        if wait:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                body = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    body = gzip.decompress(body)
                status = r.status
                headers = {"content-type": r.headers.get("Content-Type", ""), "final_url": r.geturl()}
        except urllib.error.HTTPError as e:
            status = e.code
            try:
                body = e.read()
            except Exception:
                body = b""
        except Exception as e:  # noqa: BLE001
            status, headers = 0, {"error": f"{type(e).__name__}: {e}"}
        if status in (0, 408, 425, 429, 500, 502, 503, 504):
            headers["retries"] = str(attempt)
            continue
        break
    time.sleep(PAUSE)
    if CACHE_DIR:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / (_key(url) + ".bin")).write_bytes(body)
        (CACHE_DIR / (_key(url) + ".meta")).write_text(
            "\n".join(f"{k}\t{v}" for k, v in {"status": status, "url": url, **headers}.items()))
    return status, body, headers
