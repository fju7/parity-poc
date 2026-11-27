"""Figures in no bound span: where each one is (advisor's ruling 4 on P169, 2026-11-27). $0: no model, no network.

Rule 1 (bindings.rule_rows) STOPs a sentence carrying a figure that no span it is bound to contains. It is not
loosened here. This sweep only says, for each such figure, where it is:

  in_cited_source      in the held text of a source the sentence is bound to (the span is too narrow: a binding gap)
  in_other_source_only in another held source of the case, not in any source the sentence cites
  in_no_held_source    in no held text of the case (the model computed it, or it is unsupported)

Figures are matched as numbers bounded by non-digits (a "0.92" inside "10.92" does not count), on the held text
after the same comma-grouping rule 1 reads (figure_text.comma_grouped). Rule 1 prints at most four figures per
sentence; the sweep reads the sentence's own weighted figures (bindings._claim_figures, modelbind._weight, as rule 1
does) and keeps those its bound spans lack.

    python3 figure_sweep.py <slug>      under the run's environment (orch/run_env.py <slug> -- ...)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LOOSE = re.compile(r"([0-9a-f]{8}): ([^|]+?) in no span it is bound to")


def _has(fig: str, text: str) -> bool:
    import figure_text as FT
    pat = r"(?<![\d.])%s(?!\d)" % re.escape(fig)
    return bool(re.search(pat, text) or re.search(pat, FT.comma_grouped(text)))


def sweep_case(slug: str) -> dict:
    import audit_stage as A
    import bindings as B
    import figure_text as FT
    import modelbind as MB
    import ruling as R
    rows = B.load(slug).get("bindings") or {}
    held = R.held_texts(slug)
    out, n = [], 0
    for _name, status, detail in B.rule_rows(slug):
        if status == "ok":
            continue
        for m in LOOSE.finditer(detail or ""):
            key = next((k for k in rows if k.startswith(m.group(1))), None)
            if not key:
                continue
            r = rows[key]
            cited = A.sources_of(r)
            spans = " ".join(q for _s, q in R.quotations(r, held))
            figs = sorted(f for f in B._claim_figures(FT.comma_grouped(r.get("sentence") or ""))
                          if MB._weight(f) and not _has(f, spans))
            for f in figs:
                n += 1
                where_cited = [s for s in cited if _has(f, held.get(s) or "")]
                where_other = [s for s in sorted(held) if s not in cited and _has(f, held[s])]
                cls = ("in_cited_source" if where_cited else "in_other_source_only" if where_other
                       else "in_no_held_source")
                out.append({"row": key[:8], "figure": f, "class": cls, "cited": cited,
                            "in": where_cited or where_other})
    by = {}
    for x in out:
        by[x["class"]] = by.get(x["class"], 0) + 1
    return {"slug": slug, "figures": n, "by_class": by, "rows": out}


def main(argv=None) -> int:
    a = list(argv if argv is not None else sys.argv[1:])
    got = sweep_case(a[0])
    print(json.dumps(got, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
