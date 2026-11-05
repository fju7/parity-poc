#!/usr/bin/env python3
"""What the checking stages received of each held text (lean WHU; process doc
§4.6.1, "What 'we read' means"; advisor's rulings of 5 November 2026 after
Q1-04). Offline, $0.

"We read" means WHU as a system. A section counts as read only if ONE checking
stage received it in full; the page's reading statement is built from this
measurement (fix 6, lean_sentences.py), and every bound sentence must rest on
received text (fix 5).

WHAT EACH STAGE RECEIVED, from its own logs (the method of session LT's
system_read.py):
  audit     every audit/*/retrieval.jsonl: the bound and retrieved passages,
            exact offsets (lean_audit.ranges_for, as delivered);
  rulings   the `inputs` of every call in rulings/rulings.jsonl, matched back to
            the held text K characters at a time, both sides folded
            (non-ASCII to a space, whitespace runs to one space);
  advocate  each re-quote's `delivered` passages in
            advocate/runs/*/quote_checks.jsonl, and each omission re-ask's in
            rulings/advocate_reasks.jsonl, exact offsets. The advocate's
            first call is sent no held text. A record with no `delivered` (one
            written before this module) counts as nothing received.

RECEIVED IN FULL: one stage received at least FULL of the section's non-space
characters (the 1% is the text matching's edge). Stages are never added
together for that; for "rests on received text" (fix 5) they are.

    python3 lean_received.py <slug>           per source and section, as JSON
"""
from __future__ import annotations

import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

STAGES = ("audit", "rulings", "advocate")
FULL = 0.99
K = 40


def _fold_map(text: str) -> tuple[str, list[int]]:
    """TEXT folded (non-ASCII to a space, whitespace runs to one space) and,
    for each folded character, its offset in TEXT."""
    out, offs, prev_space = [], [], True
    for i, ch in enumerate(text):
        c = ch if ord(ch) < 128 else " "
        if c.isspace():
            if prev_space:
                continue
            out.append(" "); offs.append(i); prev_space = True
        else:
            out.append(c); offs.append(i); prev_space = False
    return "".join(out), offs


def fold(text: str) -> str:
    return _fold_map(text)[0].strip()


def _mask(n: int, ranges) -> bytearray:
    m = bytearray(n)
    for a, b in ranges:
        a, b = max(0, int(a)), min(n, int(b))
        if b > a:
            m[a:b] = b"\x01" * (b - a)
    return m


def text_mask(held: str, texts: list[str]) -> bytearray:
    """The characters of HELD that occur, K folded characters at a time, in TEXTS."""
    n = len(held)
    m = bytearray(n)
    grams = set()
    for t in texts:
        f = fold(t)
        for i in range(0, len(f) - K + 1):
            grams.add(f[i:i + K])
    if not grams:
        return m
    fh, offs = _fold_map(held)
    for j in range(0, len(fh) - K + 1):
        if fh[j:j + K] in grams:
            a, b = offs[j], offs[j + K - 1] + 1
            m[a:b] = b"\x01" * (b - a)
    return m


def _jsonl(p: Path) -> list[dict]:
    out = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def audit_ranges(case: Path, sid: str) -> list[tuple[int, int]]:
    out = []
    for f in sorted(glob.glob(str(case / "audit" / "*" / "retrieval.jsonl"))):
        for r in _jsonl(Path(f)):
            if r.get("source") != sid:
                continue
            out += [(x[0], x[1]) for x in r.get("bound") or []]
            out += [(x[0], x[1]) for x in r.get("retrieved") or []]
    return out


def ruling_texts(case: Path) -> list[str]:
    out = []
    for r in _jsonl(case / "rulings" / "rulings.jsonl"):
        if r.get("carried_from"):
            continue                    # fix 7: a carried ruling made no call
        for v in (r.get("inputs") or {}).values():
            if isinstance(v, str):
                out.append(v)
    return out


def advocate_ranges(case: Path, sid: str) -> list[tuple[int, int]]:
    out = []
    files = sorted(glob.glob(str(case / "advocate" / "runs" / "*" / "quote_checks.jsonl")))
    files.append(str(case / "rulings" / "advocate_reasks.jsonl"))      # omission re-asks (ruling.py)
    for f in files:
        for r in _jsonl(Path(f)):
            if r.get("source") != sid:
                continue
            out += [(x[0], x[1]) for x in r.get("delivered") or []]
    return out


def masks(case: Path, sid: str, held: str, texts: list[str] | None = None) -> dict[str, bytearray]:
    """{stage: mask over HELD} for one source."""
    n = len(held)
    return {"audit": _mask(n, audit_ranges(case, sid)),
            "rulings": text_mask(held, ruling_texts(case) if texts is None else texts),
            "advocate": _mask(n, advocate_ranges(case, sid))}


def union(ms: dict[str, bytearray]) -> bytearray:
    out = bytearray(len(next(iter(ms.values())))) if ms else bytearray()
    for m in ms.values():
        for i, v in enumerate(m):
            if v:
                out[i] = 1
    return out


def share(held: str, m: bytearray, a: int, b: int) -> float:
    """Share of the non-space characters of HELD[a:b] that M marks."""
    a, b = max(0, a), min(len(held), b)
    tot = got = 0
    for i in range(a, b):
        if not held[i].isspace():
            tot += 1
            got += 1 if m[i] else 0
    return got / tot if tot else 0.0


def section_report(held: str, ms: dict[str, bytearray], name: str, at) -> dict:
    """{name, at, shares {stage: share}, full: bool, by: [stages]} for one section;
    a section with no offsets is not measured (full False)."""
    if not at or len(at) != 2 or not (0 <= int(at[0]) < int(at[1]) <= len(held)):
        return {"name": name, "at": at, "shares": {}, "full": False, "by": [],
                "why": "no valid offsets in access.section_offsets"}
    a, b = int(at[0]), int(at[1])
    sh = {k: round(share(held, m, a, b), 4) for k, m in ms.items()}
    by = [k for k in STAGES if sh.get(k, 0) >= FULL]
    return {"name": name, "at": [a, b], "shares": sh, "full": bool(by), "by": by}


def measure(slug: str, held: dict[str, str] | None = None, sources: list[dict] | None = None,
            case: Path | None = None) -> dict[str, dict]:
    """{sid: {"sections": [section_report], "masks": {...}}} for every
    full_text_held source of SLUG."""
    import ruling as R
    import source_store as store
    case = case or store.case_dir(slug)
    if sources is None:
        doc = json.loads((case / "sources.json").read_text(encoding="utf-8"))
        sources = doc.get("sources") or []
    held = held if held is not None else R.held_texts(slug)
    texts = ruling_texts(case)
    out = {}
    for s in sources:
        acc = s.get("access") or {}
        sid = s.get("id")
        if acc.get("state") != "full_text_held" or sid not in held:
            continue
        ms = masks(case, sid, held[sid], texts)
        offs = acc.get("section_offsets") or {}
        secs = [section_report(held[sid], ms, name, offs.get(name))
                for name in (acc.get("sections") or []) if isinstance(name, str) and name.strip()]
        out[sid] = {"sections": secs, "masks": ms}
    return out


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print(__doc__)
        return 2
    m = measure(argv[0])
    print(json.dumps({sid: v["sections"] for sid, v in m.items()}, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
