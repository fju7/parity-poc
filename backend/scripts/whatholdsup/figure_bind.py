"""One contiguous passage for a sentence's figures (advisor's ruling 3 on P171-P176, 2026-11-27). $0, code only.

When a bound sentence carries a figure no span it is bound to contains, the binder searches the sentence's cited
source(s) for ONE contiguous passage holding ALL of the sentence's figures:

  - one sentence of the held text,
  - two adjacent sentences, or
  - one table row (one line of the held text),

and binds the sentence to it as well (also_rests_on, by "code (figure passage)"). Figures from separate places are
never combined: the passage holds every figure or it is not used, and the sentence stays stopped by rule 1, which is
unchanged (bindings.rule_rows). The shortest such passage wins, then the earliest; each cited source is searched on
its own.

    python3 figure_bind.py <slug>     report, for every rule-1 row of a case, the passage this would bind, and rule 1's
                                      rows with those passages attached in memory (nothing is written)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

BY = "code (figure passage: every figure of the sentence in one contiguous passage; ruling 3 on P171-P176)"
MAX_PASSAGE = 1200            # a passage longer than this is not one sentence, a pair or a row; never used
_SENT_END = re.compile(r"(?<=[.!?;])\s+(?=[\"'(\[]?[A-Z0-9])")


def has(fig: str, text: str) -> bool:
    """Is FIG in TEXT, read as rule 1 reads a span (bindings.rule_rows): as a number among the text's figures, read
    also comma-grouped; written as a bare integer; split by extraction ("1, 222"); or a span figure correctly
    rounded. A '0.92' inside '10.92' or '0.925' is not 0.92."""
    import bindings as B
    import figure_text as FT
    import modelbind as MB
    import spancheck as SC
    t = SC._norm(text or "")
    figs = MB.figures(t) | MB.figures(FT.comma_grouped(t))
    return bool(B._as_numbers([fig]) <= B._as_numbers(figs) or B._bare_integer_in(fig, t)
                or FT.split_grouped(fig, t) or any(FT.rounds_to(h, fig) for h in figs))


def figures_of(sentence: str) -> list[str]:
    """The sentence's weighted claim figures, read as rule 1 reads them."""
    import bindings as B
    import figure_text as FT
    import modelbind as MB
    return sorted(f for f in B._claim_figures(FT.comma_grouped(sentence or "")) if MB._weight(f))


def missing(row: dict) -> list[str]:
    """The sentence's figures that no span it is bound to contains."""
    import bindings as B
    spans = " ".join(s for _sid, s in B.covering_spans(row))
    return [f for f in figures_of(row.get("sentence") or "") if not has(f, spans)]


def _sentences(text: str) -> list[tuple[int, int]]:
    out, i = [], 0
    for m in _SENT_END.finditer(text):
        if text[i:m.start()].strip():
            out.append((i, m.start()))
        i = m.end()
    if text[i:].strip():
        out.append((i, len(text)))
    return out


def _rows(text: str) -> list[tuple[int, int]]:
    """Table rows: lines of the held text with no sentence boundary inside them. A line that holds more than one
    sentence is prose (a paragraph, or a whole document extracted onto one line), never a row: reading it as one
    would combine figures from separate sentences (found by the constructed test, 2026-11-27)."""
    out, i = [], 0
    for line in text.split("\n"):
        j = i + len(line)
        if line.strip() and len(_sentences(line)) == 1:
            out.append((i, j))
        i = j + 1
    return out


def candidates(text: str) -> list[tuple[int, int, str]]:
    """Every sentence, adjacent sentence pair and table row of TEXT: (start, end, kind)."""
    ss = _sentences(text)
    out = [(a, b, "sentence") for a, b in ss]
    out += [(ss[i][0], ss[i + 1][1], "adjacent sentence pair") for i in range(len(ss) - 1)]
    out += [(a, b, "table row") for a, b in _rows(text)]
    return [(a, b, k) for a, b, k in out if 0 < b - a <= MAX_PASSAGE]


def find(figs: list[str], text: str) -> tuple[int, int, str] | None:
    """The shortest, then earliest, single candidate passage of TEXT holding every figure in FIGS."""
    if not figs or not text:
        return None
    best = None
    for a, b, kind in candidates(text):
        seg = text[a:b]
        if all(has(f, seg) for f in figs):
            key = (b - a, a)
            if best is None or key < best[0]:
                best = (key, (a, b, kind))
    return best[1] if best else None


def passage_for(row: dict, held: dict[str, str]) -> dict | None:
    """The passage to bind ROW to, or None (nothing missing, or no single passage holds every figure)."""
    import audit_stage as A
    if not missing(row):
        return None
    figs = figures_of(row.get("sentence") or "")
    for sid in A.sources_of(row):
        text = held.get(sid) or ""
        got = find(figs, text)
        if got:
            a, b, kind = got
            return {"source_id": sid, "span": text[a:b].strip(), "offsets": [a, b], "kind": kind,
                    "figures": figs, "by": BY}
    return None


def attach(row: dict, held: dict[str, str]) -> dict | None:
    """Bind ROW to its figure passage (also_rests_on), if one exists. Returns the passage added, or None."""
    p = passage_for(row, held)
    if not p:
        return None
    text = held[p["source_id"]]
    a, b = p["offsets"]
    lead = len(text[a:b]) - len(text[a:b].lstrip())
    p["offsets"] = [a + lead, a + lead + len(p["span"])]
    extra = list(row.get("also_rests_on") or [])
    if any(x.get("source_id") == p["source_id"] and x.get("span") == p["span"] for x in extra):
        return None
    extra.append({"source_id": p["source_id"], "span": p["span"], "offsets": p["offsets"],
                  "figure_passage": p["kind"], "by": BY})
    row["also_rests_on"] = extra
    return p


def rule1_loose(slug: str, doc: dict | None = None) -> list[str]:
    """Rule 1's 'in no span it is bound to' items, on DOC (default: the case's bindings as committed)."""
    import bindings as B
    if doc is None:
        rows = B.rule_rows(slug)
    else:
        real = B.load
        B.load = lambda s, _d=doc: _d if s == slug else real(s)
        try:
            rows = B.rule_rows(slug)
        finally:
            B.load = real
    return [m.group(0) for _n, st, det in rows if st != "ok"
            for m in re.finditer(r"[0-9a-f]{8}: [^|]+? in no span it is bound to", det or "")]


def report(slug: str) -> dict:
    import copy
    import bindings as B
    import ruling as R
    doc = B.load(slug)
    rows = doc.get("bindings") or {}
    held = R.held_texts(slug)
    before = rule1_loose(slug)
    flagged = {x[:8] for x in before}
    # a check that cannot see fails (P176): a rule-1 row whose cited source has no held text here
    blind = [k[:8] for k, r in rows.items() if k[:8] in flagged
             and any(not (held.get(s) or "").strip() for s in __import__("audit_stage").sources_of(r))]
    if blind:
        raise RuntimeError("%s: no held text for the cited source of %s; run under orch/run_env.py" % (slug, blind))
    out = []
    after = copy.deepcopy(doc)
    for k, r in rows.items():
        if not r.get("on_page") or k[:8] not in flagged or not missing(r):
            continue
        p = passage_for(r, held)
        attach(after["bindings"][k], held)
        out.append({"row": k[:8], "missing": missing(r), "figures": figures_of(r.get("sentence") or ""),
                    "bound": bool(p), "passage": p})
    return {"slug": slug, "rows": len(out), "bound": sum(1 for x in out if x["bound"]), "detail": out,
            "rule1_before": before, "rule1_after": rule1_loose(slug, after)}


def main(argv=None) -> int:
    a = list(argv if argv is not None else sys.argv[1:])
    print(json.dumps(report(a[0]), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
