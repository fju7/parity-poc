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
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "civicscale-verify (resolve/fetch/bind; contact fred.ugast@uspv.co)",
      "Accept-Encoding": "gzip"}
CACHE_DIR: Path | None = Path(os.environ["VERIFY_CACHE_DIR"]) if os.environ.get("VERIFY_CACHE_DIR") else None
PAUSE = 0.15

# PER-REGISTRY RATE LIMITS, requests per second, keyed by host. Retry on 429
# fixed one topic; the first-Monday bindings pass over ten topics is the same
# burst, larger, and a check whose own call rate manufactures the divergence
# it reports is the noise failure in a new costume. Values are the published
# or de-facto polite rates: Europe PMC and Crossref ask for well under 10/s
# (Crossref's polite pool is 50/s with a mailto; we stay far below), the eCFR
# and codes.ohio.gov have no stated limit and get 2/s, ClinicalTrials.gov v2
# documents ~50/min. The limit in force is recorded on every re-check record.
RATE_LIMITS = {
    "www.ebi.ac.uk": 3.0,          # Europe PMC
    "api.crossref.org": 5.0,
    "doi.org": 5.0,
    "clinicaltrials.gov": 0.8,     # ~50/min documented
    "www.ecfr.gov": 2.0,
    "codes.ohio.gov": 2.0,
    "www.cms.gov": 1.0,            # PDFs
    "api.unpaywall.org": 5.0,
    "*": 2.0,                      # generic fetch: any other host
}
_last_call: dict[str, float] = {}


def _throttle(url: str) -> None:
    host = urllib.parse.urlsplit(url).hostname or "*"
    rate = RATE_LIMITS.get(host, RATE_LIMITS["*"])
    gap = 1.0 / rate
    wait = _last_call.get(host, 0.0) + gap - time.monotonic()
    if wait > 0:
        time.sleep(wait)
    _last_call[host] = time.monotonic()


def rate_limits_in_force() -> dict:
    return dict(RATE_LIMITS)


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
        _throttle(url)
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
    if CACHE_DIR:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (CACHE_DIR / (_key(url) + ".bin")).write_bytes(body)
        (CACHE_DIR / (_key(url) + ".meta")).write_text(
            "\n".join(f"{k}\t{v}" for k, v in {"status": status, "url": url, **headers}.items()))
    return status, body, headers
