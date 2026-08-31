"""What Holds Up: the quotation matcher.

WHY THIS EXISTS
---------------
QUOTATION is one of the six fatal claim classes, and until today it was one of
three with no control at all. fatal_recall.py said so in its own source:

    "QUOTATION": control_missing,   # "no quotation matcher exists"

An altered quotation is the most damaging error this publication can make.
Every other class is a mistake about evidence; this one puts words inside
quotation marks that the person or document did not say. A reader who checks
one quotation and finds it wrong has no reason to trust any other sentence, and
they are right not to.

The neighbouring modules were each written after a specific failure. This one is
written before it, because the class is known, the cost is total, and waiting
for the incident is the habit we are trying to break.

THE RULE, AND WHY IT FAILS CLOSED
---------------------------------
    A QUOTATION NOBODY HAS CHECKED AGAINST THE SOURCE IS NOT A QUOTATION.

Extracting quoted passages is deterministic. Deciding whether a passage is a
quotation FROM A SOURCE or the author's own phrasing in scare quotes is not --
issue two carries both, "statistical comparison was made by 1-sided stratified
log-rank test" beside "palbociclib does not work". Guessing between them is how
a check starts crying wolf and gets switched off.

So it does not guess. Every quoted passage on the page must appear in the
issue's quotations.json, either with the source's own wording to match against
or declared as the page's own voice with a reason. An unrecorded quotation
blocks. That makes the record an INPUT rather than documentation, which is the
lesson the counterexample hunter was built on: a checklist nobody has to act on
is not a control.

WHAT THIS DOES NOT DO
---------------------
It does not judge whether a quotation is fair, in context, or well chosen. It
decides whether the words between the quotation marks are the words in the
source. Only the second question is mechanical, which is why there is no model
in this file.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "issues"

OK, BAD, WARN = "ok", "BLOCKED", "warn"

# Below this length a quoted fragment is a word or a phrase being used, not a
# quotation being made: "preferred", "debated". Set from the published pages --
# the shortest real source quotation across the three issues is 29 characters.
MIN_QUOTE = 25

_SMART = {u"‘": "'", u"’": "'", u"“": '"', u"”": '"',
          u"–": "-", u"—": "-", u" ": " ", u"…": "..."}

# The states source_ledger.py treats as "somebody opened this". Kept as a
# literal rather than imported so this module has no load-order dependency on
# the ledger; the ledger owns the definition and this list must track it.
READ_STATES = ("machine_read", "human_read")


def norm(text: str) -> str:
    """Comparison form. Punctuation is not identity.

    Same reasoning as counterexample._key: a curly apostrophe on the page and a
    straight one in the source are the same character to a reader, and two of
    nine claims on issue three were once unmatchable for exactly that.
    """
    for a, b in _SMART.items():
        text = text.replace(a, b)
    return " ".join(text.lower().split())


def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob(f"WHU-*-{slug}"))
    if not hits:
        raise SystemExit(f"no case directory for {slug!r}")
    return hits[0]


def path(slug: str) -> Path:
    return case_dir(slug) / "quotations.json"


def load(slug: str) -> dict | None:
    p = path(slug)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def extract(page_text: str) -> list[str]:
    """Every quoted passage on the page, longest first, de-duplicated.

    THREE forms, and the first was missed in the first version of this file.
    <q> and <blockquote> are the semantically correct markup for a quotation
    and the page uses them heavily -- 15 on issue two, 45 on issue three. An
    extractor that strips tags before looking for quotation marks deletes the
    marks along with the tag, so every one of those quotations was invisible.
    The check reported "no quoted passages" on a page carrying dozens.

    That is the same shape as the counterexample hunter passing every gate by
    having no input, and it is why fatal_recall.py scores whether a defect
    REACHES a control separately from whether the control catches it.
    """
    # Strip style, script and comments FIRST. A CSS font stack is written
    # "SF Mono", monospace -- literal quotation marks around a 25+ character
    # string, indistinguishable from a quotation once the tags are gone. The
    # first version pulled 23 "quotations" out of the test fixture, most of
    # them font declarations, which would have buried every real one.
    page_text = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", page_text, flags=re.I | re.S)
    page_text = re.sub(r"<!--.*?-->", " ", page_text, flags=re.S)

    marked = re.findall(r"<q[^>]*>(.*?)</q>", page_text, re.I | re.S)
    marked += re.findall(r"<blockquote[^>]*>(.*?)</blockquote>", page_text, re.I | re.S)
    marked = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", m)).split()) for m in marked]

    t = html.unescape(re.sub(r"<[^>]+>", " ", page_text))
    t = " ".join(t.split())
    literal = []
    for pat in (r"\u201c([^\u201d]{%d,400})\u201d" % MIN_QUOTE,
                r'"([^"]{%d,400})"' % MIN_QUOTE):
        literal += re.findall(pat, t)

    seen, out = set(), []
    for q in sorted(marked + literal, key=len, reverse=True):
        q = q.strip().strip('"\u201c\u201d')
        if len(q) < MIN_QUOTE:
            continue
        k = norm(q)
        if k and k not in seen:
            seen.add(k)
            out.append(q)
    return out


def _records(d: dict) -> list[dict]:
    return [r for r in (d.get("quotations") or []) if isinstance(r, dict)]


def _sources(slug: str) -> dict:
    p = case_dir(slug) / "sources.json"
    if not p.exists():
        return {}
    raw = json.loads(p.read_text(encoding="utf-8"))
    items = raw.get("sources", raw) if isinstance(raw, dict) else raw
    if isinstance(items, dict):
        items = list(items.values())
    return {s.get("id"): s for s in items if isinstance(s, dict)}


def preflight_rows(slug: str, page_text: str) -> list[tuple[str, str, str]]:
    on_page = extract(page_text)
    if not on_page:
        return [("quotation matcher", OK, "no quoted passages on the page")]

    d = load(slug)
    if d is None:
        return [("quotation matcher", BAD,
                 "%d quoted passage(s) on the page and no quotations.json. Nothing "
                 "records what the sources actually say, so nothing can tell an "
                 "accurate quotation from an altered one. "
                 "publish.py quotations init %s" % (len(on_page), slug))]

    recs = _records(d)
    by_key = {norm(r.get("quote", "")): r for r in recs if r.get("quote")}

    unrecorded = [q for q in on_page if norm(q) not in by_key]
    rows = [("every quotation is recorded",
             OK if not unrecorded else BAD,
             "%d quoted passage(s), all recorded" % len(on_page) if not unrecorded
             else "%d quoted passage(s) with no record of what the source says: %s"
                  % (len(unrecorded), " || ".join(q[:70] for q in unrecorded[:3])))]

    # A record whose page quote is not what the source says.
    altered, unattested, rhetorical = [], [], 0
    srcs = _sources(slug)
    for q in on_page:
        r = by_key.get(norm(q))
        if not r:
            continue
        if r.get("kind") == "rhetorical":
            rhetorical += 1
            continue
        verbatim = norm(r.get("verbatim", ""))
        if not verbatim:
            unattested.append("%s: nothing recorded as the source's wording" % (r.get("id") or q[:40]))
            continue
        if norm(q) not in verbatim:
            altered.append("%s: page has %r; source has %r"
                           % (r.get("id") or "?", q[:60], r.get("verbatim", "")[:60]))
            continue
        sid = r.get("source_id")
        s = srcs.get(sid)
        state = ((s or {}).get("access") or {}).get("state")
        if not s:
            unattested.append("%s cites source %r, which is not in sources.json"
                              % (r.get("id") or "?", sid))
        elif state not in READ_STATES:
            unattested.append("%s quotes %s, whose access state is %r — nobody opened it"
                              % (r.get("id") or "?", sid, state))

    rows.append(("quotations match the source",
                 OK if not altered else BAD,
                 "every recorded quotation appears verbatim in its source"
                 if not altered else
                 "%d quotation(s) differ from the source: %s"
                 % (len(altered), " || ".join(altered[:2]))))

    rows.append(("quotation sources were opened",
                 OK if not unattested else BAD,
                 "every quoted source has been read"
                 + (", %d passage(s) declared as our own phrasing" % rhetorical if rhetorical else "")
                 if not unattested else
                 "%d quotation(s) rest on a source nobody opened or recorded: %s"
                 % (len(unattested), " || ".join(unattested[:2]))))
    return rows


TEMPLATE_NOTE = (
    "One entry per quoted passage on the page. Two kinds, and the difference "
    "matters: a quotation FROM A SOURCE carries source_id and verbatim -- the "
    "source's own wording, copied, so the check can compare rather than trust "
    "-- while a passage in the page's own voice carries kind: rhetorical and a "
    "reason. An entry with neither blocks, and so does a quoted passage on the "
    "page with no entry at all."
)


def init(slug: str, page: Path) -> Path:
    p = path(slug)
    existing = {norm(r.get("quote", "")): r for r in _records(load(slug) or {})}
    out = []
    for i, q in enumerate(extract(page.read_text(encoding="utf-8")), 1):
        prior = existing.get(norm(q))
        if prior:
            out.append(prior)
            continue
        out.append({
            "id": "Q-%02d" % i,
            "quote": q,
            "source_id": "",
            "verbatim": "",
            "kind": "",
            "why": "",
            "attested": {"by": "", "on": ""},
        })
    p.write_text(json.dumps(
        {"what_this_is": "What Holds Up: quotations on %s and what the sources actually say." % slug,
         "how_to_use_it": TEMPLATE_NOTE,
         "quotations": out}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    ap.add_argument("--page", help="Path to the page, relative to the repo root")
    ap.add_argument("--init", action="store_true",
                    help="Write or extend quotations.json from the page's quoted passages")
    args = ap.parse_args()

    page = ROOT / args.page if args.page else None
    if args.init:
        if not page or not page.exists():
            sys.exit("--init needs --page pointing at the page")
        p = init(args.slug, page)
        print(f"wrote {p.relative_to(ROOT)}")
        print("Fill in source_id and verbatim for each quotation from a source,")
        print("or kind: rhetorical with a reason for the page's own phrasing.")
        return 0

    if not page or not page.exists():
        sys.exit("give --page")
    bad = 0
    for name, state, detail in preflight_rows(args.slug, page.read_text(encoding="utf-8")):
        print(f"  {state:8s} {name}\n           {detail}")
        bad += state == BAD
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
