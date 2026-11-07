#!/usr/bin/env python3
"""Generated protected sentences (lean WHU item 3).

Under lean WHU two kinds of protected sentence are no longer written by hand:

  * the question restatement: issue.json's `question`, verbatim, in the fixed
    frame  The question is: “<question>”
  * what we held, read and did not read, one sentence per fact, from
    sources.json: each source's access `state`, its `sections` read and its
    `not_read` entries (FRAMES below). Each names its source with the numbered
    citation the readers' list uses ([n], the source's place in sources.json).

Code checks them against the records, and that check replaces a person's read
for THESE sentences only: the audit settles a page sentence that is word for
word a generated sentence as "holds_by_record_check" (no model, no person),
and the preflight row "generated sentences match the records" STOPs if a
sentence in a generated frame is on the page but is not what the records
generate now, or if the question restatement is missing. Every other protected
sentence (the readers' list, a "we did not search" sentence written by hand)
stays as it is: a person reads it.

MACHINE SCOPE NOTES (process doc §4.6.1, advisor's ruling of 4-5 November
2026). Two more kinds are generated, so that no protected sentence goes to a
person under lean:

  * the readers' list: its heading and one line per declared finding, from
    coverage_check.declarations (the records; the span copied from the held
    text by code; no reason clause, so no model-written prose);
  * what we searched, from sources.json's top-level
    "search": {"searched": [...], "not_searched": [...]}, in SEARCH_FRAMES.

A protected sentence (bindings.protected_kind) on the page that is not word for
word a generated one is HAND-WRITTEN: the check row STOPs on it, and the audit
marks it must_leave_page, never HUMAN_READ_REQUIRED.

    python3 lean_sentences.py <slug> render   the HTML paragraphs to paste
    python3 lean_sentences.py <slug> check    the preflight row
"""
from __future__ import annotations

import html as _html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

OK, BAD, WARN = "ok", "BLOCKED", "warn"
ROW = "generated sentences match the records"
RECORD_CHECK = "holds_by_record_check"
QUESTION_FRAME = "The question is: “%s”"
STATE_FRAMES = {
    "full_text_held": "We hold the full text of %s.",
    "abstract_held": "We hold the abstract of %s, not the full text.",
    "fragment_only": "We hold only a fragment of %s, not the full text.",
    "blocked": "We could not obtain %s.",
    "human_read": "No model read %s; a person read it.",
    "not_opened": "We have not opened %s.",
}
SEARCH_FRAMES = {"searched": "We searched: %s.", "not_searched": "We did not search: %s."}
# Orchestrated runs (advisor's rulings (a) and (b), 2026-11-07): a source found but not held, or of no type we can
# check, is named by its title and nothing on the page draws on it.
NOT_HELD_FRAME = "We found %s but could not hold it, so nothing on this page draws on it."
NO_TYPE_FRAME = "We found %s but it is not of a type we can check, so nothing on this page draws on it."
# Corrections and retractions (advisor's ruling 2026-11-07).
RETRACTED_FRAME = "We found %s but it has been retracted, so nothing on this page draws on it."
CORRECTION_NOT_HELD_FRAME = ("We found %s but it has a published correction we could not hold, so nothing on this "
                             "page draws on it.")
CONCERN_FRAME = ("We found %s but its journal has issued an expression of concern, so nothing on this page draws "
                 "on it.")
CORRECTION_UNREAD_FRAME = ("We found %s but it has a published correction we could not read, so nothing on this "
                           "page draws on it.")
NOT_HELD_FRAMES = {"could_not_hold": NOT_HELD_FRAME, "retracted": RETRACTED_FRAME, "concern": CONCERN_FRAME,
                   "correction_unread": CORRECTION_UNREAD_FRAME,
                   "correction_not_held": CORRECTION_NOT_HELD_FRAME}
SECTIONS_FRAME = "Of %s, we read: %s."
NOT_READ_FRAME = "Of %s, we did not read: %s."
# Fix 6 (process doc §4.6.1, "What 'we read' means"; advisor, 5 November 2026):
# a full_text_held section is "read" only if a checking stage received it in
# full (lean_received.py); the rest is said in this code-written frame.
SEARCHED_FULL_FRAME = ("We searched the full text of %s and checked the passages relevant to each sentence; "
                       "we did not read %s in full.")
# What a sentence in a generated frame starts with (the check's net).
LEADS = ("The question is: “", "We hold the full text of ", "We hold the abstract of ",
         "We hold only a fragment of ", "We could not obtain ", "No model read ", "We have not opened ",
         "We searched: ", "We did not search: ", "We searched the full text of ", "A newer edition exists of ",
         "We could not establish whether ", "Our recency check ", "We found ")
HAND_WRITTEN = "lean: hand-written protected sentence; replace it with the generated one"


def words(s: str) -> str:
    import protected
    return protected.words(s)


def _one_sentence(s: str) -> bool:
    import source_ledger as ledger
    return len(ledger.sentences(s)) == 1


def number(sources: list[dict], sid: str) -> int:
    """A source's citation number: its place in sources.json, from 1."""
    for i, s in enumerate(sources, 1):
        if s.get("id") == sid:
            return i
    raise KeyError(sid)


def cite(sources: list[dict], sid: str) -> str:
    """"<label> [n]", the label coverage_check uses; "source [n]" if the label
    would split the sentence (a full stop in a title)."""
    import coverage_check as C
    n = number(sources, sid)
    label = "%s [%d]" % (C._label(sources, sid), n)
    return label if _one_sentence(STATE_FRAMES["blocked"] % label) else "source [%d]" % n


def _clean(item) -> str:
    s = " ".join(str(item).split()).rstrip(" .;")
    return s.replace(";", ",")


def question_sentence(issue: dict) -> str | None:
    q = " ".join((issue.get("question") or "").split())
    return QUESTION_FRAME % q if q else None


def found_label(sources: list[dict], title: str | None, sid: str | None = None) -> str:
    """A found source's title, as one sentence; its citation label if the title would split the sentence."""
    t = _clean(title or "")
    if t and _one_sentence(NOT_HELD_FRAME % t):
        return t
    return cite(sources, sid) if sid else "a source whose title would split this sentence"


def generate(issue: dict, sources: list[dict], search: dict | None = None,
             declared: list[dict] | None = None, measured: dict | None = None,
             editions: list[dict] | None = None, not_of_a_type: list[dict] | None = None) -> list[dict]:
    """[{kind, source, field, sentence}] in page order: the question, then each
    source's held state, sections read and not read, then what we searched and
    did not search (SEARCH), then the newer-edition lines (EDITIONS, rule 3b),
    then the readers' list (DECLARED: the sentences coverage_check.declarations
    gives, heading first).

    MEASURED (fix 6): {sid: [lean_received.section_report]} for the
    full_text_held sources. When given, a full_text_held source's sections are
    split by it: received in full -> SECTIONS_FRAME; the rest (and a source
    with none in full) -> SEARCHED_FULL_FRAME. A source missing from MEASURED
    has nothing received. None (a direct call with no measurement): the
    records' sections as listed, as before."""
    out = []
    q = question_sentence(issue)
    if q:
        out.append({"kind": "question", "source": None, "field": "issue.json question", "sentence": q})
    for s in sources:
        sid, acc = s.get("id"), s.get("access") or {}
        if sid and acc.get("not_held"):
            frame = NOT_HELD_FRAMES.get(acc["not_held"].get("line"), NOT_HELD_FRAME)
            out.append({"kind": "reading", "source": sid, "field": "access.not_held",
                        "sentence": frame % found_label(sources, s.get("title"), sid)})
            continue
        frame = STATE_FRAMES.get(acc.get("state"))
        if not sid or not frame:
            continue
        c = cite(sources, sid)
        out.append({"kind": "reading", "source": sid, "field": "access.state", "sentence": frame % c})
        secs = [_clean(x) for x in acc.get("sections") or [] if _clean(x)]
        if measured is not None and acc.get("state") == "full_text_held":
            rep = {_clean(r["name"]): r for r in measured.get(sid) or []}
            full = [x for x in secs if (rep.get(x) or {}).get("full")]
            rest = [x for x in secs if x not in full]
            if full:
                out.append({"kind": "reading", "source": sid, "field": "access.sections (received in full)",
                            "sentence": SECTIONS_FRAME % (c, "; ".join(full))})
            if rest or not full:
                out.append({"kind": "reading", "source": sid, "field": "access.sections (not received in full)",
                            "sentence": SEARCHED_FULL_FRAME % (c, "; ".join(rest) if rest else "it")})
        elif secs:
            out.append({"kind": "reading", "source": sid, "field": "access.sections",
                        "sentence": SECTIONS_FRAME % (c, "; ".join(secs))})
        nr = [_clean(x) for x in acc.get("not_read") or [] if _clean(x)]
        if nr:
            out.append({"kind": "reading", "source": sid, "field": "access.not_read",
                        "sentence": NOT_READ_FRAME % (c, "; ".join(nr))})
    for x in not_of_a_type or []:
        out.append({"kind": "reading", "source": None, "field": "sources.json not_of_a_type",
                    "sentence": NO_TYPE_FRAME % found_label(sources, x.get("title"))})
    for field, frame in SEARCH_FRAMES.items():
        items = [_clean(x) for x in (search or {}).get(field) or [] if _clean(x)]
        if items:
            out.append({"kind": "reading", "source": None, "field": "sources.json search.%s" % field,
                        "sentence": frame % "; ".join(items)})
    for e in editions or []:
        out.append({"kind": "reading", "source": None, "field": "lean_editions %s" % e["key"],
                    "sentence": e["sentence"]})
    if declared:
        import coverage_check as C
        out.append({"kind": "scope", "source": None, "field": "coverage_check.HEADING", "sentence": C.HEADING})
        for d in declared:
            out.append({"kind": "scope", "source": d["source"], "field": "declaration %s (%s)" % (d["key"], d["state"]),
                        "sentence": d["sentence"]})
    for g in out:
        if not _one_sentence(g["sentence"]):
            g["splits"] = True              # the page splitter would cut it; the check reports it
    return out


def load(slug: str) -> tuple:
    """(issue.json, sources.json's sources, its search record, the declared
    findings, the measurement (fix 6), the newer-edition lines (rule 3b));
    empty for an issue with no records."""
    import source_store as store
    try:
        case = store.case_dir(slug)
    except (Exception, SystemExit):          # case_dir exits for an unknown slug
        return {}, [], {}, []
    if not (case / "issue.json").exists():
        return {}, [], {}, [], {}, [], []
    issue = json.loads((case / "issue.json").read_text(encoding="utf-8"))
    sp = case / "sources.json"
    doc = json.loads(sp.read_text(encoding="utf-8")) if sp.exists() else {}
    srcs = doc.get("sources") or []
    import lean_editions as LE
    return (issue, srcs, doc.get("search") or {}, declared_of(slug), measured_of(slug, srcs),
            LE.lines(case), doc.get("not_of_a_type") or [])


def measured_of(slug: str, sources: list[dict]) -> dict:
    """{sid: [section_report]} (lean_received.measure); {} -- nothing received --
    when it cannot run, so a failure never reads as "read"."""
    import lean_received as LR
    try:
        return {sid: v["sections"] for sid, v in LR.measure(slug, sources=sources).items()}
    except (Exception, SystemExit):
        return {}


def declared_of(slug: str) -> list[dict]:
    """coverage_check.declarations for SLUG (lean's lines: no reason clause), or
    [] when it has no declarations or its held texts cannot be read."""
    import coverage_check as C
    import ruling as R
    try:
        return C.declarations(slug, R.held_texts(slug))
    except (Exception, SystemExit):
        return []


def generated(slug: str, keep_removed: bool = False) -> list[dict]:
    """The generated sentences for SLUG, less those lean's fail-safe removed
    (lean_failsafe.py: a finding left unresolved on them). The readers'-list
    heading leaves with the last line under it. KEEP_REMOVED: all of them."""
    gen = generate(*load(slug))
    if keep_removed:
        return gen
    import lean_failsafe as LF
    gone = LF.removed_words(slug)
    if not gone:
        return gen
    live = [g for g in gen if not LF.is_removed(g["sentence"], gone)]
    if not any(g["kind"] == "scope" and g["field"] != "coverage_check.HEADING" for g in live):
        live = [g for g in live if g["field"] != "coverage_check.HEADING"]
    return live


def is_framed(sentence: str) -> bool:
    import coverage_check as C
    w = words(sentence)
    # Both sides folded (words): LEADS carry typographic quotes, which words() folds
    # (found 2026-11-05: the question frame was never recognised as framed).
    leads = tuple(words(x) for x in LEADS + tuple(C.LEAD.values()))
    import lean_editions as LE
    return (w.startswith(leads) or bool(LE.COUNT_RE.match(w))
            or (w.startswith("Of ") and (", we read: " in w or ", we did not read: " in w))
            or w == words(C.HEADING))


def hand_written(sentence: str, gen: list[dict], row: dict | None = None) -> bool:
    """A protected sentence (bindings.protected_kind) that is not word for word a
    generated one: lean has no person to read it, so it must leave the page."""
    import bindings as B
    return bool(B.protected_kind(sentence, row)) and matches(sentence, gen) is None


def matches(sentence: str, gen: list[dict]) -> dict | None:
    """The generated sentence SENTENCE is, word for word, or None."""
    w = words(sentence)
    return next((g for g in gen if words(g["sentence"]) == w), None)


def render(gen: list[dict]) -> str:
    return "".join("  <p>%s</p>\n" % _html.escape(g["sentence"], quote=False) for g in gen)


def check(page_sentences: list[str], gen: list[dict], gone: set | None = None,
          required: list[dict] | None = None, stops: list[dict] | None = None) -> tuple[str, str, str]:
    """GONE: the words() of every sentence lean's fail-safe removed; REQUIRED:
    the removed ones that are required page elements (lean_failsafe.required_removed)."""
    import lean_failsafe as LF
    gone = gone or set()
    still = [s for s in page_sentences if LF.is_removed(s, gone)]
    stale = [s for s in page_sentences if s not in still and is_framed(s) and not matches(s, gen)]
    hand = [s for s in page_sentences if s not in stale and s not in still and hand_written(s, gen)]
    q = next((g for g in gen if g["kind"] == "question"), None)
    split = [g for g in gen if g.get("splits")]
    on = [s for s in page_sentences if matches(s, gen)]
    bits = []
    if stops:
        import lean_failsafe as LF
        bits.append("%s: %d (e.g. %s on %r); the line stays and the page is Not Ready (process doc §4.6.1, "
                    "the ruling paths)" % (LF.STOP, len(stops), stops[0].get("path"), (stops[0].get("sentence") or "")[:90]))
    if required:
        import lean_failsafe as LF
        bits.append("%s: %d (e.g. %r); the page is Not Ready (process doc §4.6.1, the ruling paths)"
                    % (LF.REQUIRED, len(required), required[0]["sentence"][:90]))
    if still:
        bits.append("%d sentence(s) removed by the lean fail-safe (removed: unresolved finding) are still on "
                    "the page (e.g. %r); take each off: lean_sentences.py <slug> render and coverage_check.py "
                    "<slug> render" % (len(still), still[0][:90]))
    if q is None:
        bits.append("issue.json has no question to restate")
    elif not any(words(s) == words(q["sentence"]) for s in page_sentences) and not required:
        bits.append("the question restatement is not on the page word for word (%r)" % q["sentence"][:90])
    if stale:
        bits.append("%d sentence(s) in a generated frame do not match the records now (e.g. %r); "
                    "lean_sentences.py <slug> render" % (len(stale), stale[0][:90]))
    if hand:
        bits.append("%d hand-written protected sentence(s) on the page; under lean every question, reading, "
                    "search and readers'-list sentence is generated (e.g. %r); lean_sentences.py <slug> render "
                    "and coverage_check.py <slug> render" % (len(hand), hand[0][:90]))
    if split:
        bits.append("%d generated sentence(s) would be split by the page's sentence splitter (e.g. %r)"
                    % (len(split), split[0]["sentence"][:90]))
    if bits:
        return (ROW, BAD, "; ".join(bits))
    return (ROW, OK, "%d generated sentence(s) on the page, each matching issue.json and sources.json "
                     "(%d generated)%s" % (len(on), len(gen),
                                           "; %d removed by the lean fail-safe (removed: unresolved finding), "
                                           "none of them a required page element" % len(gone) if gone else ""))


def preflight_rows(slug: str, page_sentences: list[str] | None = None) -> list[tuple[str, str, str]]:
    import bindings as B
    import lean_failsafe as LF
    ps = page_sentences if page_sentences is not None else B.page_sentences(slug)
    gone = LF.removed_words(slug)
    required = LF.required_removed(generated(slug, keep_removed=True), gone) if gone else []
    return [check(ps, generated(slug), gone, required, LF.stops(slug))]


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2 or argv[1] not in ("render", "check"):
        print(__doc__)
        return 2
    slug, cmd = argv
    if cmd == "render":
        print(render(generated(slug)), end="")
        return 0
    for row in preflight_rows(slug):
        print("  %-6s %-40s %s" % (row[1], row[0], row[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
