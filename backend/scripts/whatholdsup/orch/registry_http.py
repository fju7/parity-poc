"""Every registry lookup in an orchestrated run is retried, and an outage stops the run (advisor's ruling 2
after attempt 12, 2026-11-23, extending ruling 2 after attempt 11).

install(log) wraps urllib.request.urlopen in this process: a timeout, connection error, HTTP 5xx or 429 is
retried, 4 attempts in all with backoff 2/4/8 s, and the last error is re-raised unchanged. When the URL is a
REGISTRY's and it is still unavailable, one line goes to LOG. The orchestrator installs it in its own process
and, through orch/site/sitecustomize.py on PYTHONPATH, in every step's subprocess; after each step it stops the
run "registry unavailable; run again later" if LOG has a line, however the module read the failure. So no
status (a retraction, a correction, an identifier, "not found") is ever recorded from a subset of registries.
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ATTEMPTS = 4
BACKOFF = (2, 4, 8)
REGISTRY_HOSTS = {"www.ebi.ac.uk", "ebi.ac.uk", "europepmc.org", "www.europepmc.org", "api.crossref.org",
                  "eutils.ncbi.nlm.nih.gov", "www.ncbi.nlm.nih.gov", "pubmed.ncbi.nlm.nih.gov",
                  "clinicaltrials.gov", "www.clinicaltrials.gov", "api.unpaywall.org", "api.openalex.org",
                  "api.datacite.org"}
_orig = None
_log = None
_sleep = time.sleep


def url_of(req) -> str:
    return req.full_url if isinstance(req, urllib.request.Request) else str(req)


def is_registry(url: str) -> bool:
    u = urllib.parse.urlsplit(url)
    host = (u.hostname or "").lower()
    return host in REGISTRY_HOSTS or (host == "doi.org" and u.path.startswith("/api/"))


def transient(e: Exception) -> bool:
    if isinstance(e, urllib.error.HTTPError):
        return e.code >= 500 or e.code == 429
    return isinstance(e, (TimeoutError, ConnectionError, urllib.error.URLError, OSError))


def _wrapped(req, *a, **kw):
    url = url_of(req)
    for i in range(ATTEMPTS):
        try:
            return _orig(req, *a, **kw)
        except Exception as e:
            if not transient(e):
                raise
            if i + 1 >= ATTEMPTS:
                if is_registry(url) and _log:
                    with open(_log, "a", encoding="utf-8") as fh:
                        fh.write(json.dumps({"url": url[:300], "error": "%s: %s" % (type(e).__name__, e),
                                             "attempts": ATTEMPTS,
                                             "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}) + "\n")
                raise
            _sleep(BACKOFF[min(i, len(BACKOFF) - 1)])


def install(log) -> None:
    global _orig, _log
    _log = str(log)
    if _orig is None:
        _orig = urllib.request.urlopen
        urllib.request.urlopen = _wrapped


def uninstall() -> None:
    global _orig, _log
    if _orig is not None:
        urllib.request.urlopen = _orig
    _orig, _log = None, None


def installed() -> bool:
    return _orig is not None


def outages(log) -> list[dict]:
    try:
        return [json.loads(l) for l in open(log, encoding="utf-8") if l.strip()]
    except (OSError, ValueError):
        return []
