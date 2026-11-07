"""Record ownership: the chain (docs/whu-orchestrator.md §2.5).

Before and after each step the orchestrator hashes every file in the case
folder and the issue's library record. After the step, a path created, changed
or deleted that the step does not own is a STOP. Each step's hashes are
appended to orchestrator/chain.jsonl; the preflight row "records match the
orchestrator's chain" compares the current files with the last hashes written.

FROZEN FIELDS. Some records are shared by several steps (sources.json is
written by `discover` and by `acquire`'s fetch fields), so a path rule alone
cannot protect what matters inside them. Three things are frozen once their
step has run, by a fingerprint of exactly those fields:
  - the source list (ids, URLs, identifiers, types, titles, editions): after `discover` (E5, E6);
  - every source's reading record (`access.sections`, `access.not_read`, `access.state`): after `acquire` (E1);
  - the premise (the whole of premise.json): after `premise` (ruling C).
A later change to a frozen fingerprint is a STOP, whichever step made it.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LIBRARY = ROOT / "backend" / "data" / "whatholdsup" / "library" / "issues"
CHAIN = "orchestrator/chain.jsonl"
# Written by the orchestrator itself at every step.
ALWAYS_OWNED = ("orchestrator/*", "study_log.md")
STOP = "record changed outside the step that owns it"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def snapshot(case: Path, slug: str) -> dict:
    """{relative path: sha256} for every file in the case folder, plus "library:<slug>.json"."""
    out = {}
    for p in sorted(case.rglob("*")):
        if p.is_file():
            rel = p.relative_to(case).as_posix()
            if rel == CHAIN:
                continue
            out[rel] = _sha(p)
    lib = LIBRARY / ("%s.json" % slug)
    if lib.exists():
        out["library:%s.json" % slug] = _sha(lib)
    return out


def diff(before: dict, after: dict) -> dict:
    return {"created": sorted(set(after) - set(before)),
            "deleted": sorted(set(before) - set(after)),
            "changed": sorted(k for k in set(before) & set(after) if before[k] != after[k])}


def owned(path: str, owns) -> bool:
    from orch.steps import NEVER_WRITTEN       # a person's record is owned by no step, whatever a glob says
    if path.rsplit("/", 1)[-1] in NEVER_WRITTEN:
        return False
    return any(fnmatch.fnmatch(path, pat) for pat in tuple(owns) + ALWAYS_OWNED)


def violations(d: dict, owns) -> list[str]:
    return ["%s %s" % (kind, p) for kind in ("created", "changed", "deleted") for p in d[kind]
            if not owned(p, owns)]


# ---- frozen fields ---------------------------------------------------------------------------------------------

SOURCE_LIST_FIELDS = ("id", "url", "type", "title", "edition", "container", "year")
# Identifiers are frozen separately: a registry may ADD one after `discover` (sweep_sources.py records a PMID it
# confirms from the PMCID in the URL; found before trial 1's attempt 4), but none may change or go.
IDENT_FIELDS = ("doi", "pmid", "pmcid")
READING_FIELDS = ("state", "sections", "not_read")


def _load(case: Path, name: str):
    p = case / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"_unparseable": _sha(p)}


def _fp(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _sources(doc) -> list:
    if not isinstance(doc, dict):
        return []
    return [s for s in (doc.get("sources") or []) if isinstance(s, dict)]


def source_list_fp(case: Path) -> str:
    return _fp([{k: s.get(k) for k in SOURCE_LIST_FIELDS} for s in _sources(_load(case, "sources.json"))])


def identifiers_now(case: Path) -> str:
    return json.dumps({s.get("id"): {k: s.get(k) for k in IDENT_FIELDS if s.get(k)}
                       for s in _sources(_load(case, "sources.json"))}, sort_keys=True)


def identifiers_broken(before: str, now: str) -> bool:
    """True when an identifier held at the freeze changed or went; an added one is not a break."""
    a, b = json.loads(before or "{}"), json.loads(now or "{}")
    return any(k not in b or any(b[k].get(f) != v for f, v in ids.items()) for k, ids in a.items())


def reading_fp(case: Path) -> str:
    return _fp([{"id": s.get("id"), **{k: (s.get("access") or {}).get(k) for k in READING_FIELDS}}
                for s in _sources(_load(case, "sources.json"))])


# The premise rows fixed before any source is opened (ruling C): written by `premise`, never changed.
# The rows filled after looking (what the sources show, direction, the kill-condition test, the public
# record check) are written by a later step and are not frozen here.
PREMISE_FIXED = ("belief.statement", "kill_condition", "reader_with_a_decision", "scope", "evidence_standard")


def forms_fp(case: Path) -> str:
    return _fp([{"id": s.get("id"), "form": s.get("form")} for s in _sources(_load(case, "sources.json"))])


def premise_fp(case: Path) -> str:
    d = _load(case, "premise.json")
    if not isinstance(d, dict):
        return _fp(d)
    out = {}
    for k in PREMISE_FIXED:
        v = d
        for part in k.split("."):
            v = v.get(part) if isinstance(v, dict) else None
        out[k] = v
    return _fp(out)


FROZEN = {  # fingerprint name -> (function, the step after which it is frozen, why)
    "source_list": (source_list_fp, "discover", "the source list is fixed by `discover` (no new source, "
                                                "edition or type afterwards)"),
    "reading": (reading_fp, "acquire", "reading records are written by code at `acquire` only"),
    "forms": (forms_fp, "acquire", "a source's form is derived from its type by code at `acquire` (E6)"),
    "premise": (premise_fp, "premise", "the premise's fixed rows are written before any source and never changed"),
    "identifiers": (identifiers_now, "discover", "a source's registry identifiers may be added to, never changed"),
}


def frozen_now(case: Path) -> dict:
    return {k: f(case) for k, (f, _s, _w) in FROZEN.items()}


def frozen_breaks(case: Path, frozen: dict) -> list[str]:
    """Frozen fingerprints (name -> value) that the case no longer matches."""
    now = frozen_now(case)
    return ["%s (%s)" % (k, FROZEN[k][2]) for k, v in frozen.items()
            if (identifiers_broken(v, now.get(k)) if k == "identifiers" else now.get(k) != v)]


# ---- the chain file ---------------------------------------------------------------------------------------------

def append(case: Path, step: str, hashes: dict, frozen: dict, extra: dict | None = None) -> dict:
    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "step": step,
           "hashes": hashes, "frozen": frozen, **(extra or {})}
    p = case / CHAIN
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def rows(case: Path) -> list[dict]:
    p = case / CHAIN
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def check(case: Path, slug: str) -> list[str]:
    """Mismatches between the case now and the chain's last row ([] when they agree).
    A case with no chain is itself a mismatch (an orchestrated issue always has one)."""
    rs = rows(case)
    if not rs:
        return ["no orchestrator chain (orchestrator/chain.jsonl)"]
    last = rs[-1]
    d = diff(last.get("hashes") or {}, snapshot(case, slug))
    out = ["%s %s" % (kind, p) for kind in ("created", "changed", "deleted") for p in d[kind]
           if not any(fnmatch.fnmatch(p, pat) for pat in ALWAYS_OWNED)]
    out += ["frozen field changed: %s" % b for b in frozen_breaks(case, last.get("frozen") or {})]
    return out
