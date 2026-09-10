#!/usr/bin/env python3
"""What remains open, derived from the checks rather than remembered.

WHY THIS EXISTS
---------------
Rule 13 makes an acceptance require two things the operator can genuinely
supply: knowing what remains open, and choosing to publish anyway. **Nothing in
this apparatus produced or checked the first one.** It has been assembled by
hand, from memory, by whoever was writing the acceptance block.

On 2026-09-09 that list said "the S029 erratum". It did not say that 212 of
melanoma's 343 body sentences had never been examined by rule 1 or rule 2,
because nobody knew — the row reporting it did not exist until the next day. So
the first of rule 13's two requirements was not supplied, not BY the operator,
TO him.

Every failure this week has been a hand-maintained representation drifting from
the thing it represents: the index dates, the family instance count, the
correction log, the four-commit figure, the locator count. **The open list is one
of those, and it is the one a publication decision rests on.**

The fix is the one already applied to the index and to the record's start date:
derive it. Then "what remains open" is a measurement and the requirement can
actually be met.

WHAT IT DOES NOT DO
-------------------
It does not decide whether any item should block. That is the operator's, and
collapsing "here is what is open" into "here is what stops you" would take the
second of rule 13's requirements away from him as well.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

OK, WARN, BAD = "ok", "warn", "STOP"


def _rows(slug):
    """Every preflight row we can obtain without spending a gate run."""
    out = []
    import bindings as B
    for src, fn in (("bindings", lambda: B.rule_rows(slug)),):
        try:
            out += [(src,) + r for r in fn()]
        except BaseException as exc:
            out.append((src, "could not be read", WARN,
                        "%s: %s. Unknown, not clean." % (type(exc).__name__, exc)))
    for name in ("errata", "b13", "coverage", "canary", "negatives",
                 "corrections_check", "unjudged", "watch"):
        try:
            m = __import__(name)
            if not hasattr(m, "preflight_rows"):
                continue
            try:
                rows = m.preflight_rows(slug)
            except TypeError:
                continue
            out += [(name,) + tuple(r) for r in rows]
        except BaseException as exc:
            out.append((name, "did not run", WARN,
                        "%s: %s. Unknown, not clean." % (type(exc).__name__, exc)))
    return out


def derive(slug: str) -> dict:
    """The open list, as data. Nothing here is typed by a person."""
    items, unknown = [], []
    # Rows already reported under Coverage are not repeated here. A list whose
    # purpose is accuracy cannot count one item twice, and "212 of 343 not
    # examined" appearing as a heading AND as one of seven open checks reads as
    # two findings. Named explicitly rather than matched loosely, so a new row
    # is never silently swallowed.
    COVERAGE_ROWS = {"sentences neither rule examined",
                     "claims about what we hold"}
    for row in _rows(slug):
        src, name, state, detail = row[0], row[1], row[2], row[3]
        if state == OK or name in COVERAGE_ROWS:
            continue
        item = {"source": src, "check": name, "state": state, "detail": detail}
        (unknown if "Unknown, not clean" in detail else items).append(item)

    # Coverage is not a failing row and belongs on the list anyway: it is the
    # part of the page nothing looked at, which is precisely what an operator
    # signing an acceptance needs to know and cannot see from a green gate.
    cov = {}
    try:
        import bindings as B
        ne = B.not_examined(slug)
        rowed = len([v for v in (B.load(slug).get("bindings") or {}).values()
                     if v.get("on_page")])
        cov["rules"] = {"examined": rowed, "not_examined": len(ne),
                        "body_sentences": rowed + len(ne)}
    except BaseException as exc:
        unknown.append({"source": "bindings", "check": "rule coverage",
                        "state": WARN, "detail": "could not be computed: %s" % exc})
    try:
        import epistemic as E
        r = E.scan(slug)
        cov["epistemic"] = {"evaluated": r["evaluated"],
                            "sentences": r["epistemic_sentences"]}
    except BaseException as exc:
        unknown.append({"source": "epistemic", "check": "epistemic coverage",
                        "state": WARN, "detail": "could not be computed: %s" % exc})

    # A waive is an operator ruling that a named check may be passed. It is by
    # definition open: somebody decided to publish over it.
    waived = []
    try:
        import json
        import publish as P
        for r in json.loads(P.RECORD.read_text(encoding="utf-8"))["published"]:
            if r.get("issue") == slug and r.get("waived"):
                waived.append({"at": r["at"], "waived": r["waived"]})
    except BaseException:
        pass

    return {"slug": slug, "items": items, "unknown": unknown,
            "coverage": cov, "waived": waived}


def render(slug: str) -> str:
    """The open list as the acceptance block should carry it."""
    d = derive(slug)
    L = ["### What remains open, at the moment of this acceptance",
         "",
         "*Derived from the checks' own outputs. Not assembled from memory — see "
         "`open_list.py` for why that distinction is the whole point.*",
         ""]
    c = d["coverage"].get("rules")
    if c:
        L += ["**Coverage.** Rules 1 and 2 examined **%d** of this page's **%d** "
              "body sentences. **%d were not examined** — a binding row is created "
              "only where an anchor is detectable, so a claim carrying no figure, "
              "quotation, named trial or registry identifier never enters either "
              "rule. **Not examined is not failing:** nothing in those %d has been "
              "shown wrong, and they may be entirely sound."
              % (c["examined"], c["body_sentences"], c["not_examined"],
                 c["not_examined"]), ""]
    e = d["coverage"].get("epistemic")
    if e:
        L += ["**Claims about what we know.** %d of %d sentences saying what we "
              "hold or have read could be tied to a single source and checked "
              "against the store; the rest are reported as not evaluated rather "
              "than passed." % (e["evaluated"], e["sentences"]), ""]
    if d["items"]:
        L += ["**Checks not returning ok (%d):**" % len(d["items"]), ""]
        L += ["- **%s** — %s: %s" % (i["check"], i["state"], i["detail"][:400])
              for i in d["items"]]
        L.append("")
    if d["unknown"]:
        L += ["**Checks that could not be run (%d) — unknown, not clean:**"
              % len(d["unknown"]), ""]
        L += ["- **%s** — %s" % (i["check"], i["detail"][:300]) for i in d["unknown"]]
        L.append("")
    if d["waived"]:
        L += ["**Waived at a previous publication (%d):**" % len(d["waived"]), ""]
        L += ["- %s — %s" % (w["at"][:19], w["waived"]) for w in d["waived"]]
        L.append("")
    if not (d["items"] or d["unknown"] or d["waived"]):
        L += ["No check is reporting anything other than ok.", ""]
    return "\n".join(L)


def main() -> int:
    import publish as P
    slug = sys.argv[1] if len(sys.argv) > 1 else None
    for s in ([slug] if slug else sorted(P.ISSUES)):
        print("\n" + "=" * 72)
        print(s)
        print("=" * 72)
        print(render(s))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
