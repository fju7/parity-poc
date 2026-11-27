"""The text-assembly sweep (advisor's ruling 1 on P162, 2026-11-26). $0: no model, no network.

WHU-OT1-01c stopped at coverage: S005's registry title ends with a full stop, so the readers'-list line built from
its label ("... appointments. [5]") split into two sentences, the line builder shortened its quotation to "..." and
the line could not be bound. This sweep builds every label and every readers'-list line the orchestrated runs record
-- and constructed hard cases -- and checks, with the shared sentence splitter (source_ledger.sentences, lean mode) and
the binding rule (bindings.bind_declaration_lines: the quotation found inside its own unit), that each line is exactly
one sentence and bindable.

Classes:
  title      every source title recorded in the orchestrated cases' sources.json: its label (coverage_check._label
             + lean_coverage.cite_label) in a readers'-list line, and lean_sentences.cite
  page_line  every readers'-list line on a recorded page (each line must be one sentence, with a quotation)
  unit       every headline unit of every relied-on held source (needs the run's held texts; local only): the line
             built from it, bound inside its unit
  constructed the hard cases below

`python3 text_sweep.py` (from a shell with WHU_LEAN=1) prints the counts per class; the unit class needs each run's
library (orch/run_env.py), so `text_sweep.py unit <slug>` runs one case's units under its recorded environment.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

CASES = ("WHU-OT1-02z-", "WHU-OT1-02za-", "WHU-OT1-02zb-", "WHU-OT1-02zc-", "WHU-OT1-02zd-", "WHU-OT1-01-",
         "WHU-OT1-01b-", "WHU-OT1-01c-", "WHU-OT1-04-")
STATES = ("out_of_scope", "not_material", "not_added_cap", "not_added_no_place", "not_added_anchor_removed",
          "not_stated_removed")

# Constructed hard cases (ruling 1): titles, and spans, with what breaks sentence splitters.
HARD_TITLES = (
    "Mobile phone messaging reminders for attendance at healthcare appointments.",
    "Does text messaging improve adherence?",
    "Mobile health works!",
    "Digital tracking and decision support in primary care…",
    "Digital tracking and decision support in primary care...",
    "“Targeted client communication” via mobile devices",
    "Reminders (SMS) for vaccination [a systematic review]",
    "A. B. Smith and the evidence on reminders",
    "Smith et al. on mobile reminders",
    "Reminders, e.g. SMS, i.e. text messages, vs. usual care",
    "Effect sizes of 1.5 and 2.0 in 3.4 million people",
    "Decision‐support tools – a review — of mobile‑health",
    "Part one. Part two of a title",
    "What works? A review of mobile reminders",
    "Dr. Jones reports: no effect",
    "No. 12 of the series",
)
HARD_SPANS = (
    "TCC mobile telephone reminders may increase use of antenatal care slightly (MD 1.5, 95% CI –0.36 to 3.36).",
    "Reminders, e.g. text messages, may help.",
    "Smith et al. found that reminders work (RR 1.13, 95% CI 1.00 to 1.28).",
    "Does it work? The review could not say.",
    "“It may help”, the authors wrote.",
    "A. B. Smith reported 2.5% higher attendance.",
    "Fig. 2 shows the effect.",
    "Attendance rose… then fell.",
)


def _lean():
    os.environ["WHU_LEAN"] = "1"


def line_problems(line: str, unit_text: str | None = None) -> list[str]:
    """Why LINE is not exactly one sentence and bindable ([] when it is). UNIT_TEXT: the unit's own text (the
    quotation must be found inside it, as bindings.bind_declaration_lines requires)."""
    import audit_stage as A
    import source_ledger as L
    out = []
    ss = L.sentences(line)
    if len(ss) != 1:
        out.append("splits into %d sentences" % len(ss))
    m = re.match(r"^[^“]*“(.*?)”", " ".join(line.split()))
    q = (m.group(1) if m else "").strip()
    q = q[:-1].rstrip() if q.endswith("…") else q
    if not q:
        out.append("no quotation")
    elif unit_text is not None and not A.locate(q, unit_text):
        out.append("quotation not inside its unit")
    return out


def _sources(case: Path) -> list[dict]:
    try:
        d = json.loads((case / "sources.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [s for s in (d.get("sources") or []) if isinstance(s, dict)]


def cases() -> list[Path]:
    out = []
    for p in sorted((ROOT / "issues").iterdir()):
        if p.is_dir() and any(p.name.startswith(c) for c in CASES):
            out.append(p)
    return out


def label_line(state: str, span: str, sources: list[dict], sid: str) -> str:
    import coverage_check as C
    import lean_coverage as LC
    label = LC.cite_label(C._label(sources, sid), sources, sid)
    return C.declaration_sentence(state, C.short_span(span), label, None)


def check_titles(case_list=None) -> tuple[int, list]:
    """Every recorded source title, as a label, in every readers'-list state, and in lean_sentences.cite."""
    import lean_sentences as LS
    _lean()
    n, bad = 0, []
    for case in case_list or cases():
        srcs = _sources(case)
        for s in srcs:
            for st in STATES:
                n += 1
                line = label_line(st, "a finding the source reports", srcs, s["id"])
                p = line_problems(line, "a finding the source reports")
                if p:
                    bad.append((case.name, s["id"], s.get("title"), st, line, p))
            n += 1
            c = LS.cite(srcs, s["id"])
            if not LS._one_sentence(LS.STATE_FRAMES["blocked"] % c):
                bad.append((case.name, s["id"], s.get("title"), "cite", c, ["cite splits"]))
    return n, bad


def page_lines(case: Path) -> list[str]:
    import coverage_check as C
    import source_ledger as L
    slug = case.name.split("-", 3)[-1]
    page = case / "draft" / ("%s.html" % slug)
    if not page.exists():
        return []
    leads = tuple(set(C.LEAD.values()))
    out = []
    for s in L.sentences(L.plain(page.read_text(encoding="utf-8"))):
        t = " ".join(s.split())
        if t.startswith(leads) or t.startswith(("[", "(")) and t.endswith(")."):
            out.append(t)
    return out


def check_page_lines(case_list=None) -> tuple[int, list]:
    """Every readers'-list line on a recorded page is one sentence with a quotation (a fragment such as "[5])." --
    the tail of a line split in two -- is itself a failure)."""
    _lean()
    n, bad = 0, []
    for case in case_list or cases():
        for t in page_lines(case):
            n += 1
            p = line_problems(t) if not t.startswith(("[", "(")) else ["a fragment of a split line"]
            if p:
                bad.append((case.name, t[:160], p))
    return n, bad


def check_constructed() -> tuple[int, list]:
    _lean()
    n, bad = 0, []
    for i, title in enumerate(HARD_TITLES):
        srcs = [{"id": "S001", "title": "first"}, {"id": "S002", "title": title}]
        for span in HARD_SPANS + ("a finding the source reports",):
            for st in STATES:
                n += 1
                line = label_line(st, span, srcs, "S002")
                p = line_problems(line, span)
                if p:
                    bad.append((title, span, st, line, p))
    return n, bad


def check_units(slug: str) -> tuple[int, list]:
    """Every headline unit of every relied-on held source of SLUG, under the run's environment (orch/run_env.py)."""
    _lean()
    import bindings as B
    import coverage_check as C
    import lean_coverage as LC
    import premise as PM
    import ruling as R
    rows = B.load(slug).get("bindings") or {}
    held = R.held_texts(slug)
    srcs = C._sources(slug)
    by = {s["id"]: s for s in srcs}
    spans = C.bound_ranges(rows, held)
    n, bad = 0, []
    for sid in C.relied_on(slug, rows, PM.load(slug) or {}):
        if sid not in held:
            continue
        for u in LC.split_units(C.units_of(by.get(sid) or {"id": sid}, held[sid], spans.get(sid)))[0]:
            for st in ("out_of_scope", "not_material"):
                n += 1
                line = label_line(st, u["text"], srcs, sid)
                p = line_problems(line, u["text"])
                if p:
                    bad.append((slug, C.unit_key(u), st, line[:200], p))
    return n, bad


def main(argv=None) -> int:
    a = list(argv if argv is not None else sys.argv[1:])
    if a[:1] == ["unit"]:
        n, bad = check_units(a[1])
        print(json.dumps({"class": "unit", "slug": a[1], "checked": n, "failed": len(bad), "failures": bad},
                         ensure_ascii=False, indent=1))
        return 1 if bad else 0
    rc = 0
    for name, fn in (("title", check_titles), ("page_line", check_page_lines), ("constructed", check_constructed)):
        n, bad = fn()
        print(json.dumps({"class": name, "checked": n, "failed": len(bad), "failures": bad[:40]},
                         ensure_ascii=False, indent=1))
        rc = rc or (1 if bad else 0)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
