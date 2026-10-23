#!/usr/bin/env python3
"""One retrieval route for every cited source a snapshot could not reach.

    retrieve_sources.py [--only SOURCE_ID,...]

Reads ~/Projects/whu-study-private/scoring/m1/sources/manifest.json and tries
every row whose extent is "unreachable", whichever system cited it, by the
same routes in the same order (scoring prep round 2, 2026-10-23):

  (a) the script: snapshot.fetch, with tls.py's certificate-chain fix;
  (b) the same address with curl on the operator's Mac (this session's shell
      runs there): a browser User-Agent and Accept headers, a cookie jar, -L
      to follow redirects, asked twice so a cookie set by the first answer is
      sent with the second;
  (c) open-access locations, from identifiers taken from the cited address
      only (find_access.ids_from_url; nothing is typed or searched): Europe
      PMC's free full text and Unpaywall's oa_locations, published or
      accepted version first, then submitted (preprint). Each location is
      tried by (a), then (b). The version held is recorded;
  (d) the Claude desktop app's built-in browser, for free pages only: not
      available in this session, so recorded as not tried.

Never a paywall bypass, never a sign-in, never a shadow library. WHU's own
source store is not used for any snapshot: a source WHU cites goes through the
same route as any other.

A retrieval is held only if snapshot.extent() calls it full text or abstract
only, as for a first fetch. Each row gains "retrieval": every attempt with its
result, the route that worked, the address it came from, and the version. The
snapshot stays keyed by the cited address (its source_id is unchanged).

Still unreachable after every route: listed in m1/operator_fetch.json by
prepare_scoring.py snapshot-report, with "blocks_automation" (the last answers
were a refusal, a challenge page or an empty script shell) and "free_to_read"
(an open-access record says so, or the page is not an article record).
Free: no model is called.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
import snapshot as SN  # noqa: E402
import find_access as FA  # noqa: E402

RUN = Path.home() / "Projects" / "whu-study-private" / "scoring" / "m1"
CURL_HEADERS = ["-H", "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf;q=0.9,*/*;q=0.8",
                "-H", "Accept-Language: en-US,en;q=0.9"]
VERSION_ORDER = {"publishedVersion": 0, "acceptedVersion": 1, "submittedVersion": 2}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def judge_bytes(url: str, data: bytes, ctype: str) -> tuple[str, str, str]:
    text = SN.text_of(data)
    ext, why = SN.extent(url, data, text, ctype)
    return ext, why, text


def by_script(url: str):
    try:
        data, got = SN.fetch(url)
    except Exception as e:
        return None, {"result": str(e)[:160]}
    ext, why, text = judge_bytes(url, data, got.get("content_type", ""))
    return ((data, text, got.get("content_type", ""), got.get("final_url")) if ext != "unreachable" else None,
            {"result": ext, "why": why, "status": got.get("status")})


def by_curl(url: str):
    with tempfile.TemporaryDirectory() as d:
        jar, body = Path(d) / "jar", Path(d) / "body"
        last = {}
        for attempt in (1, 2):
            p = subprocess.run(["/usr/bin/curl", "-sS", "-L", "--max-time", "60", "--compressed", "-A", SN.UA,
                                *CURL_HEADERS, "-c", str(jar), "-b", str(jar), "-o", str(body),
                                "-w", "%{http_code}\t%{url_effective}\t%{content_type}", url],
                               capture_output=True, text=True, close_fds=False)    # spawned, not forked
            if p.returncode != 0:
                last = {"result": "curl exit %d: %s" % (p.returncode, p.stderr.strip()[:120]), "attempt": attempt}
                continue
            code, final, ctype = (p.stdout.split("\t") + ["", "", ""])[:3]
            data = body.read_bytes() if body.exists() else b""
            if not code.isdigit() or int(code) >= 400:
                last = {"result": "HTTP %s" % code, "attempt": attempt}
                continue
            ext, why, text = judge_bytes(url, data, ctype)
            last = {"result": ext, "why": why, "status": int(code), "attempt": attempt}
            if ext != "unreachable":
                return (data, text, ctype, final), last
        return None, last


def oa_locations(url: str) -> tuple[list[dict], dict]:
    """Open-access copies of the cited work, from identifiers in its address."""
    ids = FA.ids_from_url(url)
    locs, evidence = [], {"ids": ids, "is_oa": None, "epmc_free": False}
    rec = None
    for field, key in (("PMCID", "pmcid"), ("EXT_ID", "pmid"), ("DOI", "doi")):
        if key in ids:
            rec = FA.epmc(ids[key], field)
            time.sleep(1)
            if rec:
                break
    if rec:
        version = "acceptedVersion" if rec.get("authMan") == "Y" else "publishedVersion"
        if rec.get("pmcid") and rec.get("inEPMC") == "Y":
            evidence["epmc_free"] = True
            locs.append({"source": "Europe PMC full text (%s)" % rec["pmcid"], "version": version,
                         "url": "https://www.ebi.ac.uk/europepmc/webservices/rest/%s/fullTextXML" % rec["pmcid"]})
        for u in ((rec.get("fullTextUrlList") or {}).get("fullTextUrl") or []):
            if (u.get("availability") or "").lower() in ("free", "open access") and u.get("url"):
                evidence["epmc_free"] = True
                locs.append({"source": "Europe PMC link: %s" % u.get("site"), "version": version, "url": u["url"]})
    doi = ids.get("doi") or (rec or {}).get("doi")
    if doi:
        up = FA.unpaywall(doi)
        time.sleep(1)
        if up:
            evidence["is_oa"] = bool(up.get("is_oa"))
            for loc in up.get("oa_locations") or []:
                for u in (loc.get("url_for_pdf"), loc.get("url")):
                    if u:
                        locs.append({"source": "Unpaywall: %s" % loc.get("host_type"),
                                     "version": loc.get("version") or "unknown", "url": u})
    seen, out = set(), []
    for l in sorted(locs, key=lambda l: VERSION_ORDER.get(l["version"], 3)):
        if l["url"] not in seen and l["url"].split("#")[0] != url:
            seen.add(l["url"]); out.append(l)
    return out, evidence


def retrieve(row: dict) -> dict:
    url = row["url"]
    tried = []
    got, r = by_script(url)
    tried.append({"route": "a", "url": url, **r})
    if not got:
        got, r = by_curl(url)
        tried.append({"route": "b", "url": url, **r})
    route, origin, version, evidence = ("a" if got and len(tried) == 1 else "b") if got else None, url, "as cited", {}
    if not got:
        locs, evidence = oa_locations(url)
        if not locs:
            tried.append({"route": "c", "url": None, "result": "no open-access location for identifiers %s"
                          % (json.dumps(evidence["ids"]) if evidence["ids"] else "none in the address")})
        for l in locs:
            g, r = by_script(l["url"])
            tried.append({"route": "c(a)", "url": l["url"], "source": l["source"], "version": l["version"], **r})
            if not g:
                g, r = by_curl(l["url"])
                tried.append({"route": "c(b)", "url": l["url"], "source": l["source"], "version": l["version"], **r})
            if g:
                got, route, origin, version = g, "c", l["url"], l["version"]
                break
    if not got:
        tried.append({"route": "d", "url": None, "result": "not tried: the desktop app's built-in browser is not "
                      "available in this session"})
    rec = {"at": now(), "tried": tried, "route": route, "retrieved_from": origin if got else None,
           "version": version if got else None, "oa_evidence": evidence}
    if got:
        data, text, ctype, final = got
        ext, why = SN.extent(url, data, text, ctype)
        sid = row["source_id"]
        (RUN / "sources" / (sid + ".raw")).write_bytes(data)
        (RUN / "sources" / (sid + ".txt")).write_text(text, encoding="utf-8")
        row.update(fetched="retrieved", final_url=final, content_type=ctype,
                   raw_sha256=hashlib.sha256(data).hexdigest(), raw_bytes=len(data),
                   text_sha256=hashlib.sha256(text.encode()).hexdigest(), text_chars=len(text),
                   extent=ext, extent_why=why, abstract_only=(ext == "abstract only"))
    if row.get("retrieval"):
        # An earlier pass is kept, not overwritten (2026-10-23: the first pass's
        # curl exited on signal 11 every time, so route (b) had not run).
        rec["earlier_passes"] = (row["retrieval"].pop("earlier_passes", []) + [row["retrieval"]])
    row["retrieval"] = rec
    return row


def reextract(rows: list[dict]) -> int:
    """Decide text and extent again from every stored .raw, in a process whose
    children are not broken (see snapshot.py, macOS). A row whose extent
    changes records what it was."""
    changed = 0
    for r in rows:
        raw = RUN / "sources" / (r["source_id"] + ".raw")
        if not raw.exists():
            continue
        data = raw.read_bytes()
        ext, why, text = judge_bytes(r["url"], data, r.get("content_type", ""))
        if (ext, len(text)) != (r.get("extent"), r.get("text_chars")):
            changed += 1
            r.setdefault("reextracted", []).append({"at": now(), "was": {"extent": r.get("extent"),
                                                    "text_chars": r.get("text_chars"), "why": r.get("extent_why")}})
            (RUN / "sources" / (r["source_id"] + ".txt")).write_text(text, encoding="utf-8")
            r.update(text_sha256=hashlib.sha256(text.encode()).hexdigest(), text_chars=len(text),
                     extent=ext, extent_why=why, abstract_only=(ext == "abstract only"))
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--reextract", action="store_true",
                    help="first decide text and extent again from every stored .raw")
    a = ap.parse_args()
    mf = RUN / "sources" / "manifest.json"
    rows = json.loads(mf.read_text())
    if a.reextract:
        n = reextract(rows)
        mf.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
        print("re-extracted from stored bytes: %d row(s) changed" % n, flush=True)
    only = set(a.only.split(",")) if a.only else None
    for i, row in enumerate(rows):
        if row["extent"] != "unreachable" or (only and row["source_id"] not in only):
            continue
        rows[i] = retrieve(row)
        r = rows[i]["retrieval"]
        print("%s  %-13s route %-4s version %-16s tries %d" % (row["source_id"], rows[i]["extent"], r["route"] or "-",
                                                            r["version"] or "-", len(r["tried"])), flush=True)
        mf.write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
