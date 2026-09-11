#!/usr/bin/env python3
"""Label a fact-check finding that disputes a figure we hold the bytes for.

WHY THIS EXISTS
---------------
On 2026-09-11 the fact-check gate produced FIVE SERIOUS findings across two paid
runs. Every one was refuted by two documents in our own library:

  S004  10.1200/JCO-26-00835, full text, held 1 September
        "the OS HR (95% CI) was 0.471 (0.165 to 1.345)"
  S007  10.1200/OA-25-00008, full text, held 1 September
        the 0.425 row, under the heading OS, on nine deaths

`factcheck_draft.py` reads the web and nothing else -- its only evidence channel
is the `web_search_20250305` server tool, and in 2,555 lines it does not mention
the library once. So it found adjacent figures in reachable material, and
reported the mismatch as our error. **A fact-check gate with no access to the
held sources, in a publication whose method is holding sources.**

WHAT THIS DOES, AND WHY IT IS NOT SUBJECT RESOLUTION
-----------------------------------------------------
It does NOT try to work out which held document bears on which claim. That is
the problem the epistemic check could not solve, it has no test set, and it is
deliberately deferred.

It asks a narrower question that needs no such mapping:

    **The finding disputes a figure. Do we hold bytes containing that figure?**

If we do, the finding is about a document the checker could not open, and it
arrives as a **LEAD** rather than a FINDING -- carrying the sentence from the
held document, so whoever adjudicates it has the settling quotation in hand
instead of re-deriving it.

THE ASYMMETRY IS WHAT MAKES A WEAK MATCHER SAFE
------------------------------------------------
Matching figures is crude and will sometimes fire on a coincidence. That is
tolerable here and would not be tolerable in a verifier, because this can only
ever **downgrade**:

    false positive -> a real finding is labelled a lead, and a human still reads it
    false negative -> the finding is left exactly as the gate wrote it

It never marks anything verified, never silences a finding, and never raises a
severity. A matcher that can only lower confidence cannot manufacture any.

CORRECTION, 11 September 2026 (failure 32). The paragraph above bounds FALSE
BLOCKS and nothing else. A downgrade on a coincidental token is a FALSE
REASSURANCE -- "we hold the settling bytes" said of bytes we do not hold -- and
the direction does not bound that. Measured on run 3: 3 of 16 leads rested on
coincidences (`34.9` in six documents, resolved by sort order to a PALOMA paper;
`0.051` matching a `0.0519` substring and a registry ciUpperLimit, for a figure
no held document contains). `check()` also stops at the FIRST document in sort
order, so any token shared across issues points at `cdk46:` before `melanoma:`.
Behaviour deliberately unchanged in that pass; the fix is decomposed in
docs/whatholdsup-open-gaps.md (document frequency per token, all tokens of one
finding landing in the same document, spelled-out counts as a separate signal).

    python3 reachability.py <issue-slug> --report <gate.json>
    python3 reachability.py melanoma --text "0.471 appears in no published source"
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as S                                    # noqa: E402

# Four or more significant digits is a figure worth checking; bare integers and
# one-decimal numbers ("5 years", "1.5") match far too much prose to be useful.
# One decimal is enough when the integer part is two digits or more -- "34.9"
# months of follow-up, "25.1" to "51.0" -- which the original two-decimal rule
# missed and which run 3 blocked on. A bare "1.5" or "0.5" matches far too much
# prose to carry any identifying power, so single-digit one-decimal numbers stay
# out.
FIGURE = re.compile(r"\b(?:\d+\.\d{2,}|\d{2,}\.\d)\b")

# Figures that carry no identifying power, however many decimals they have.
COMMON = {"0.05", "95.0", "100.0"}

# A finding often disputes a QUOTATION rather than a figure -- "this quote cannot
# be verified from the paper's abstract or any indexed source" -- and a
# figure-only match is blind to it. Run 3 produced two such findings about
# documents we hold in full. Six words is long enough that an accidental match
# in a million characters is not worth worrying about.
PHRASE = re.compile(r"[\"\u201c\u2018']([^\"\u201c\u201d\u2018\u2019']{40,300})[\"\u201d\u2019']")


def _norm(t: str) -> str:
    t = re.sub(r"[\u2018\u2019]", "'", re.sub(r"[\u201c\u201d]", '"', t or ""))
    t = re.sub(r"[\u2010-\u2015]", "-", t)
    return re.sub(r"[^a-z0-9 ]+", " ", " ".join(t.lower().split()))


def held_text(slug: str, cache: bool = True) -> dict[str, str]:
    """{source id: extracted text} for every document held for this issue."""
    root = S.case_dir(slug).parent if False else None       # noqa: F841
    lib = Path(S.issue_index_path(slug)).resolve().parent.parent
    cpath = lib / f"_reachability_{slug}.json"
    if cache and cpath.exists():
        try:
            cached = json.loads(cpath.read_text(encoding="utf-8"))
            # An EMPTY cache is a cached failure, and a cached failure is
            # permanent. The first run of this against a correction email
            # resolved no issue index, extracted nothing, wrote {} here, and
            # every later run read the {} back and reported "no held sources"
            # without ever touching the library again. Never trust an empty.
            if cached:
                return cached
        except Exception:
            pass
    # A correction email is not an issue. `issue_slug_for` resolves a draft by
    # the case directories, and a draft whose stem matches none of them falls
    # back to the stem -- so this arrives as "2026-09-10-corrections", which
    # indexes nothing. That is not a bug to route around: a correction email
    # spans issues by construction, and the sources that settle a claim in it
    # may be held under any of them. When the slug names no index, read them
    # all. Ids are namespaced by issue so two S004s cannot collide.
    indices = {}
    if (ix := S.load_issue_index(slug)).get("sources"):
        indices[slug] = ix
    else:
        idir = Path(S.issue_index_path(slug)).resolve().parent
        for q in sorted(idir.glob("*.json")):
            other = S.load_issue_index(q.stem)
            if other.get("sources"):
                indices[q.stem] = other

    out: dict[str, str] = {}
    pairs = [(f"{iss}:{sid}", src)
             for iss, ix2 in indices.items()
             for sid, src in (ix2.get("sources") or {}).items()]
    for sid, src in pairs:
        p = lib / src["file"]
        if not p.exists():
            continue
        try:
            if p.suffix == ".pdf":
                exe = S.pdftotext_path()
                if not exe:
                    continue
                t = subprocess.run([exe, "-layout", str(p), "-"],
                                   capture_output=True, text=True, timeout=120).stdout
            else:
                raw = p.read_text(encoding="utf-8", errors="replace")
                raw = re.sub(r"(?is)<(script|style).*?</\1>", " ", raw)
                t = re.sub(r"(?s)<[^>]+>", " ", raw)
        except Exception:
            continue
        out[sid] = re.sub(r"[ \t\xa0\n]+", " ", t)
    if cache and out:            # never write an empty: see the read above
        try:
            cpath.write_text(json.dumps(out), encoding="utf-8")
        except Exception:
            pass
    return out


def _what(hit: dict) -> str:
    """A hit is either a figure or a quoted phrase; name whichever it is."""
    return hit.get("figure") or ('"%s…"' % hit.get("phrase", "")[:60])


def sentence_around(text: str, figure: str) -> str:
    i = text.find(figure)
    if i < 0:
        return ""
    a = max(0, i - 240)
    return text[a:i + len(figure) + 240].strip()


def check(slug: str, finding_text: str, corpus: dict[str, str] | None = None
          ) -> list[dict]:
    """Which held sources contain the figures this finding disputes."""
    corpus = held_text(slug) if corpus is None else corpus
    figs = {f for f in FIGURE.findall(finding_text or "") if f not in COMMON}
    hits = []
    for fig in sorted(figs):
        for sid, text in sorted(corpus.items()):
            if fig in text:
                hits.append({"source": sid, "figure": fig,
                             "quote": sentence_around(text, fig)})
                break

    # Then the quotations. A finding that says a quoted sentence cannot be
    # verified is answered by the sentence sitting in a document we hold.
    normed = None
    for phrase in {m.group(1).strip() for m in PHRASE.finditer(finding_text or "")}:
        if len(phrase.split()) < 6:
            continue
        want = _norm(phrase)
        if not want:
            continue
        if normed is None:
            normed = {sid: _norm(t) for sid, t in corpus.items()}
        for sid in sorted(normed):
            if want in normed[sid]:
                hits.append({"source": sid, "phrase": phrase[:120],
                             "quote": sentence_around(corpus[sid], phrase[:40])
                                      or phrase})
                break
    return hits


def label(hits: list[dict], severity: str) -> str:
    """SERIOUS about a figure we hold is a LEAD. Everything else is unchanged."""
    if hits and str(severity).upper() in ("SERIOUS", "WRONG_VALUE", "NOT_FOUND"):
        return "LEAD"
    return str(severity or "")


def findings_of(report: dict) -> list[tuple[str, dict]]:
    for key in ("objections", "inferences", "verdicts", "coverage", "recency"):
        for item in (report.get(key) or []):
            if isinstance(item, dict):
                yield key, item


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--report", help="a gate report JSON to annotate")
    ap.add_argument("--text", help="a single finding's text, for a spot check")
    a = ap.parse_args()

    corpus = held_text(a.slug)
    print("  held for %s: %d document(s), %s characters\n"
          % (a.slug, len(corpus), format(sum(len(v) for v in corpus.values()), ",")))

    if a.text:
        hits = check(a.slug, a.text, corpus)
        print("  %s" % ("LEAD — disputes a figure we hold" if hits else "no held figure"))
        for h in hits:
            print("    %s carries %s: %s" % (h["source"], _what(h), h["quote"][:300]))
        return 0

    if not a.report:
        ap.error("give --report or --text")
    rep = json.loads(Path(a.report).read_text(encoding="utf-8"))
    leads = 0
    for key, item in findings_of(rep):
        sev = item.get("severity") or item.get("verdict") or ""
        blob = " ".join(str(item.get(k) or "") for k in
                        ("quote", "problem", "objection", "note", "correct_reading"))
        hits = check(a.slug, blob, corpus)
        if label(hits, sev) == "LEAD":
            leads += 1
            print("  LEAD  (%s, was %s)" % (key, sev))
            print("    %s" % (item.get("quote") or "")[:160])
            for h in hits[:3]:
                print("      %s carries %s — %s" % (h["source"], _what(h), h["quote"][:220]))
            print()
    print("  %d finding(s) downgraded to LEAD." % leads)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
