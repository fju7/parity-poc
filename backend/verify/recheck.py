"""recheck_topic: re-run exactly the bindings a publication record holds and
classify what changed. Bindings, not bytes (Phase 3 design §2).

Two kinds of run:
  status    the fifth check only -- one metadata query per surviving source,
            compared with the status frozen at publication. Weekly.
  bindings  re-resolve, re-fetch, re-run every recorded binding for every
            surviving source and every claim. Monthly.

Outcomes per source (and rolled up per claim):
  unchanged     same bytes, same bindings
  rerendered    different bytes, every recorded binding returns what it did -- silent
  binding_lost  a binding that was ok at publication is not ok now
  status_changed the fifth check's verdict moved (retracted, corrected, superseded,
                withdrawn, trial_status_changed, amended, reissued)
  unreachable   resolve UNCHECKED or fetch got nothing -- an ACCESS fact; the
                reader marker appears only after two consecutive misses

A re-check never edits the publication record and never flips status.
"""
from __future__ import annotations

import datetime as dt
import gzip
import json
from pathlib import Path

from . import __version__, literature, law
from .bind import bind_figure, bind_heading, bind_span
from .status import check as status_check
from .types import Document, Exists, Identifier, Provenance

BACKEND = Path(__file__).resolve().parents[1]
PUBLISHED = BACKEND / "data" / "verify" / "published"
RECHECKS = BACKEND / "data" / "verify" / "rechecks"

ALERTING_STATUS = {"retracted", "withdrawn", "concern", "corrected", "superseded",
                   "trial_status_changed", "amended", "reissued"}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _ident(d: dict) -> Identifier:
    return Identifier(d["system"], d["value"], "", Provenance(d.get("provenance", "TYPED")))


def _frozen_doc(src: dict) -> Document | None:
    d = src.get("document")
    if not d or not d.get("path"):
        return None
    p = BACKEND / d["path"]
    if not p.exists():
        return None
    with gzip.open(p, "rt", encoding="utf-8") as f:
        text = f.read()
    return Document(_ident(src["identifier"]), d["sha256"], text, kind=d.get("kind", ""), text_layer=d.get("text_layer", "DECLARED_SOUND"))


def _previous_runs(slug: str, kind: str) -> list[dict]:
    d = RECHECKS / slug
    if not d.exists():
        return []
    runs = []
    for p in sorted(d.glob("*.json")):
        try:
            r = json.loads(p.read_text())
            if r.get("kind") == kind:
                runs.append(r)
        except Exception:
            pass
    return runs


def recheck(slug: str, kind: str = "bindings") -> dict:
    rec = json.loads((PUBLISHED / slug / "latest.json").read_text())
    prev = _previous_runs(slug, kind)
    last_miss = {}
    if prev:
        for s in prev[-1].get("sources", []):
            last_miss[s["source_id"]] = s.get("outcome") == "unreachable"
    run_id = _now().replace(":", "").replace("-", "")
    out = {"slug": slug, "kind": kind, "run_id": run_id, "run_at": _now(), "publish_id": rec["publish_id"],
           "gate_version": {"package": __version__}, "sources": [], "claims": [], "flags": []}
    survivors = {s["source_id"]: s for s in rec["sources"] if s.get("survives")}
    live_docs: dict[str, Document | None] = {}
    registry_text: dict[str, str] = {}

    for sid, src in survivors.items():
        ident = _ident(src["identifier"])
        entry = {"source_id": sid, "title": src.get("title"), "outcome": "unchanged", "detail": "", "status": None}
        # ---- status (both kinds run it: it is cheap and it is the fifth check)
        frozen_status = (src.get("status") or {})
        st = status_check(ident, frozen_status.get("frozen") or {})
        entry["status"] = {"verdict": st.verdict, "detail": st.detail, "registry": st.registry,
                           "events": st.events, "frozen_verdict": frozen_status.get("verdict")}
        if st.verdict == "unknown":
            pass  # not a status change; recorded as unknown
        elif st.verdict in ALERTING_STATUS and st.verdict != frozen_status.get("verdict"):
            entry["outcome"] = "status_changed"; entry["detail"] = f"{frozen_status.get('verdict')} -> {st.verdict}: {st.detail}"
            out["flags"].append({"scope": "source", "source_id": sid, "outcome": "status_changed",
                                 "verdict": st.verdict, "detail": st.detail, "events": st.events[:5],
                                 "observed_at": out["run_at"], "published_at": rec["published_at"]})
        if kind == "status":
            out["sources"].append(entry); continue

        # ---- bindings: re-resolve, re-fetch, re-run
        mod = literature if ident.registry == "literature" else law
        res = mod.resolve(ident)
        if res.exists != Exists.EXISTS:
            entry["outcome"] = "unreachable" if res.exists == Exists.UNCHECKED else "binding_lost"
            entry["detail"] = f"resolve: {res.exists.value}"
            live_docs[sid] = None
        else:
            doc = mod.fetch(res)
            live_docs[sid] = doc
            registry_text[sid] = " ".join(str(x) for x in ((res.heading or ""), res.extra.get("year") or "") if x)
            if doc is None:
                entry["outcome"] = "unreachable"; entry["detail"] = "fetch: nothing retrieved"
            else:
                head = bind_heading(src.get("title") or "", res)
                was_ok = any(b["kind"] == "HEADING" and (b["ok"] or b["abstained"]) for b in src.get("bindings", []))
                if was_ok and not (head.ok or head.abstained):
                    entry["outcome"] = "binding_lost"; entry["detail"] = "HEADING: " + head.reason
                elif doc.sha256 != src["document"]["sha256"] and entry["outcome"] == "unchanged":
                    entry["outcome"] = "rerendered"; entry["detail"] = f"bytes changed ({src['document']['chars']} -> {len(doc.text)} chars); heading holds"
        if entry["outcome"] == "unreachable":
            entry["consecutive_misses"] = 2 if last_miss.get(sid) else 1
            out["flags"].append({"scope": "source", "source_id": sid, "outcome": "unreachable",
                                 "consecutive_misses": entry["consecutive_misses"], "detail": entry["detail"],
                                 "observed_at": out["run_at"], "published_at": rec["published_at"],
                                 "reader_marker": entry["consecutive_misses"] >= 2})
        elif entry["outcome"] == "binding_lost":
            out["flags"].append({"scope": "source", "source_id": sid, "outcome": "binding_lost", "detail": entry["detail"],
                                 "observed_at": out["run_at"], "published_at": rec["published_at"]})
        out["sources"].append(entry)

    if kind == "bindings":
        for c in rec["claims"]:
            if c["support"] == "UNSUPPORTED":
                continue
            centry = {"claim_id": c["claim_id"], "outcome": "unchanged", "lost": []}
            for ps in c["per_source"]:
                sid = ps["source_id"]
                if sid not in survivors or ps.get("level") in (None, "UNSUPPORTED"):
                    continue
                doc = live_docs.get(sid)
                if doc is None:
                    continue  # the source outcome (unreachable) already says it
                for b in ps["bindings"]:
                    if not b["ok"]:
                        continue
                    if b["kind"] == "FIGURE":
                        now = bind_figure(c["claim_text"], doc, registry_text.get(sid, ""))
                    elif b["kind"] == "SPAN":
                        now = bind_span(c["claim_text"], doc)
                    else:
                        continue
                    if not now.ok:
                        centry["lost"].append({"source_id": sid, "kind": b["kind"], "was": b["evidence"], "now": now.reason})
            if centry["lost"]:
                centry["outcome"] = "binding_lost"
                out["flags"].append({"scope": "claim", "claim_id": c["claim_id"], "outcome": "binding_lost",
                                     "figures": c.get("figures", []), "lost": centry["lost"],
                                     "observed_at": out["run_at"], "published_at": rec["published_at"]})
            # a status change on any supporting source marks the claim too
            for ps in c["per_source"]:
                f = next((f for f in out["flags"] if f["scope"] == "source" and f["source_id"] == ps["source_id"]
                          and f["outcome"] == "status_changed"), None)
                if f and ps.get("level") not in (None, "UNSUPPORTED"):
                    out["flags"].append({"scope": "claim", "claim_id": c["claim_id"], "outcome": "status_changed",
                                         "source_id": ps["source_id"], "verdict": f["verdict"],
                                         "observed_at": out["run_at"], "published_at": rec["published_at"]})
            out["claims"].append(centry)

    from collections import Counter
    out["summary"] = {"sources": dict(Counter(s["outcome"] for s in out["sources"])),
                      "claims": dict(Counter(c["outcome"] for c in out["claims"])) if kind == "bindings" else {},
                      "flags": len(out["flags"])}
    out["exit_ok"] = not any(f["outcome"] in ("binding_lost", "status_changed") for f in out["flags"])
    d = RECHECKS / slug; d.mkdir(parents=True, exist_ok=True)
    (d / f"{run_id}-{kind}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
    return out
