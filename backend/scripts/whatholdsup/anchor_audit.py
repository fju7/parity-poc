"""What Holds Up: how much of a page is anchored to a source?

WHY THIS EXISTS
---------------
Every control built so far answers a question about a PARTICULAR KIND of
sentence: is this figure right, is this quotation verbatim, is this universal
negative false, was this trial really double-blind. None of them answers the
question underneath: WHAT FRACTION OF THIS PAGE IS ANCHORED TO ANYTHING AT ALL?

That question matters more than any single control, because the failure mode
established on 2026-08-31 is not a check that fails. It is a sentence no check
ever looked at. Signal published 381 sources whose text nobody had fetched, and
every downstream control ran happily on top of it. A gate can be green and a
page can still be mostly unexamined prose.

This measures it, and it is deliberately unflattering: a sentence counts as
anchored only if a record ties it to something outside the page -- a checked
figure, a verified quotation, a registry-confirmed design claim, an attributed
inherited claim. The page's own reasoning is counted separately, not as a
failure and not as an anchor, because reasoning is anchored to the evidence
above it rather than to a source.

WHAT A GOOD NUMBER LOOKS LIKE
-----------------------------
Not 100%. A piece that is nothing but sourced assertions is a bibliography.
The number worth watching is the EMPIRICAL UNANCHORED count: sentences that
assert something about the world, carry the marks of an empirical claim -- a
figure, a trial name, a comparison, a characterisation of evidence -- and are
tied to no record at all. Those are the sentences that can be wrong in a way a
reader would catch and we would not.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

OK, BAD, WARN = "ok", "BLOCKED", "warn"

_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(“\"])")

# Marks of a sentence that asserts something about the world, as opposed to
# introducing, structuring or reasoning about what is already on the page.
EMPIRICAL = re.compile(
    r"(\d+(\.\d+)?\s?%|\bHR\b|\bp\s?=|\bCI\b|\bn\s?=|\b\d{2,4}\s+patients?\b|"
    r"\bmonths?\b|\btrial\b|\bstudy\b|\bstudies\b|\bguideline\b|\bapprov|"
    r"\bcategory [12]\b|\brandomi[sz]ed\b|\bphase\b|\bsurvival\b|\bhazard\b)", re.I)

BOILERPLATE = re.compile(
    r"^(what holds up|share|subscribe|corrections|about|contents|read more|"
    r"published|updated|by |menu|skip to)", re.I)


def norm(t: str) -> str:
    return " ".join(t.split())


def sentences(page_text: str) -> list[str]:
    t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", page_text, flags=re.I | re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    blocks = re.split(r"</(?:p|li|h[1-6]|td|div|blockquote|figcaption)\s*>", t, flags=re.I)
    out = []
    for b in blocks:
        txt = norm(html.unescape(re.sub(r"<[^>]+>", " ", b)))
        if not txt or BOILERPLATE.match(txt):
            continue
        for s in _SENT.split(txt):
            s = norm(s)
            if len(s.split()) >= 5:
                out.append(s)
    seen, uniq = set(), []
    for s in out:
        if s.lower() not in seen:
            seen.add(s.lower())
            uniq.append(s)
    return uniq


def _overlap(a: str, b: str) -> float:
    wa = {w for w in re.findall(r"[a-z0-9.]+", a.lower()) if len(w) > 3}
    wb = {w for w in re.findall(r"[a-z0-9.]+", b.lower()) if len(w) > 3}
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / min(len(wa), len(wb))


def anchors(slug: str, page: Path) -> dict:
    """Everything that ties a sentence to something outside the page."""
    out = {"claims": [], "quotations": [], "design": [], "inherited": []}
    gate = page.with_suffix(page.suffix + ".gate.json")
    if gate.exists():
        r = json.loads(gate.read_text())
        for c in (r.get("claims") or []):
            if isinstance(c, dict) and c.get("claim"):
                out["claims"].append({"text": c["claim"], "figure": c.get("figure") or ""})
    case = next(iter(sorted((ROOT / "issues").glob(f"WHU-*-{slug}"))), None)
    if case:
        q = case / "quotations.json"
        if q.exists():
            for rec in (json.loads(q.read_text()).get("quotations") or []):
                if rec.get("quote"):
                    out["quotations"].append(rec["quote"])
        i = case / "inherited.json"
        if i.exists():
            for rec in (json.loads(i.read_text()).get("claims") or []):
                if rec.get("we_wrote"):
                    out["inherited"].append(rec["we_wrote"])
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import study_design as sd
        out["design"] = [f["context"] for f in sd.findings(slug, page.read_text(encoding="utf-8"))]
    except Exception:
        pass
    return out


def classify(slug: str, page: Path) -> list[dict]:
    sents = sentences(page.read_text(encoding="utf-8"))
    a = anchors(slug, page)
    rows = []
    for s in sents:
        why = None
        for c in a["claims"]:
            if (c["figure"] and c["figure"].lower() in s.lower()) or _overlap(s, c["text"]) >= 0.55:
                why = "checked figure"
                break
        if not why:
            for qt in a["quotations"]:
                if norm(qt).lower()[:60] in s.lower():
                    why = "verified quotation"
                    break
        if not why:
            for d in a["design"]:
                if _overlap(s, d) >= 0.7:
                    why = "registry-checked design"
                    break
        if not why:
            for it in a["inherited"]:
                if _overlap(s, it) >= 0.6:
                    why = "attributed inherited claim"
                    break
        rows.append({"sentence": s, "anchor": why,
                     "empirical": bool(EMPIRICAL.search(s))})
    return rows


def report(slug: str, page: Path) -> int:
    rows = classify(slug, page)
    n = len(rows)
    anchored = [r for r in rows if r["anchor"]]
    emp = [r for r in rows if r["empirical"]]
    emp_un = [r for r in emp if not r["anchor"]]
    reasoning = [r for r in rows if not r["empirical"] and not r["anchor"]]

    print(f"\n{'=' * 72}\nANCHOR COVERAGE — {slug}\n{'=' * 72}")
    print(f"  sentences on the page          {n:4d}")
    print(f"  anchored to a record           {len(anchored):4d}   {len(anchored)/n:5.0%}")
    print(f"  empirical                      {len(emp):4d}   {len(emp)/n:5.0%}")
    print(f"  EMPIRICAL AND UNANCHORED       {len(emp_un):4d}   {len(emp_un)/n:5.0%}   <- the number that matters")
    print(f"  reasoning about what is above  {len(reasoning):4d}   {len(reasoning)/n:5.0%}")

    by = {}
    for r in anchored:
        by[r["anchor"]] = by.get(r["anchor"], 0) + 1
    if by:
        print("\n  what does the anchoring:")
        for k, v in sorted(by.items(), key=lambda x: -x[1]):
            print(f"    {k:28s} {v:4d}")

    if emp_un:
        print(f"\n  first {min(8, len(emp_un))} empirical sentences tied to nothing:")
        for r in emp_un[:8]:
            print(f"    • {r['sentence'][:120]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--page", required=True)
    args = ap.parse_args()
    page = ROOT / args.page
    if not page.exists():
        sys.exit(f"no such page: {page}")
    return report(args.slug, page)


if __name__ == "__main__":
    sys.exit(main())
