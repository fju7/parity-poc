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
SECTIONS_FRAME = "Of %s, we read: %s."
NOT_READ_FRAME = "Of %s, we did not read: %s."
# What a sentence in a generated frame starts with (the check's net).
LEADS = ("The question is: “", "We hold the full text of ", "We hold the abstract of ",
         "We hold only a fragment of ", "We could not obtain ", "No model read ", "We have not opened ")


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


def generate(issue: dict, sources: list[dict]) -> list[dict]:
    """[{kind, source, field, sentence}] in page order: the question, then each
    source's held state, sections read and not read."""
    out = []
    q = question_sentence(issue)
    if q:
        out.append({"kind": "question", "source": None, "field": "issue.json question", "sentence": q})
    for s in sources:
        sid, acc = s.get("id"), s.get("access") or {}
        frame = STATE_FRAMES.get(acc.get("state"))
        if not sid or not frame:
            continue
        c = cite(sources, sid)
        out.append({"kind": "reading", "source": sid, "field": "access.state", "sentence": frame % c})
        secs = [_clean(x) for x in acc.get("sections") or [] if _clean(x)]
        if secs:
            out.append({"kind": "reading", "source": sid, "field": "access.sections",
                        "sentence": SECTIONS_FRAME % (c, "; ".join(secs))})
        nr = [_clean(x) for x in acc.get("not_read") or [] if _clean(x)]
        if nr:
            out.append({"kind": "reading", "source": sid, "field": "access.not_read",
                        "sentence": NOT_READ_FRAME % (c, "; ".join(nr))})
    for g in out:
        if not _one_sentence(g["sentence"]):
            g["splits"] = True              # the page splitter would cut it; the check reports it
    return out


def load(slug: str) -> tuple[dict, list[dict]]:
    """(issue.json, sources.json's sources); empty for an issue with no records."""
    import source_store as store
    try:
        case = store.case_dir(slug)
    except (Exception, SystemExit):          # case_dir exits for an unknown slug
        return {}, []
    if not (case / "issue.json").exists():
        return {}, []
    issue = json.loads((case / "issue.json").read_text(encoding="utf-8"))
    sp = case / "sources.json"
    sources = json.loads(sp.read_text(encoding="utf-8")).get("sources") or [] if sp.exists() else []
    return issue, sources


def generated(slug: str) -> list[dict]:
    return generate(*load(slug))


def is_framed(sentence: str) -> bool:
    w = words(sentence)
    return w.startswith(LEADS) or (w.startswith("Of ") and (", we read: " in w or ", we did not read: " in w))


def matches(sentence: str, gen: list[dict]) -> dict | None:
    """The generated sentence SENTENCE is, word for word, or None."""
    w = words(sentence)
    return next((g for g in gen if words(g["sentence"]) == w), None)


def render(gen: list[dict]) -> str:
    return "".join("  <p>%s</p>\n" % _html.escape(g["sentence"], quote=False) for g in gen)


def check(page_sentences: list[str], gen: list[dict]) -> tuple[str, str, str]:
    stale = [s for s in page_sentences if is_framed(s) and not matches(s, gen)]
    q = next((g for g in gen if g["kind"] == "question"), None)
    split = [g for g in gen if g.get("splits")]
    on = [s for s in page_sentences if matches(s, gen)]
    bits = []
    if q is None:
        bits.append("issue.json has no question to restate")
    elif not any(words(s) == words(q["sentence"]) for s in page_sentences):
        bits.append("the question restatement is not on the page word for word (%r)" % q["sentence"][:90])
    if stale:
        bits.append("%d sentence(s) in a generated frame do not match the records now (e.g. %r); "
                    "lean_sentences.py <slug> render" % (len(stale), stale[0][:90]))
    if split:
        bits.append("%d generated sentence(s) would be split by the page's sentence splitter (e.g. %r)"
                    % (len(split), split[0]["sentence"][:90]))
    if bits:
        return (ROW, BAD, "; ".join(bits))
    return (ROW, OK, "%d generated sentence(s) on the page, each matching issue.json and sources.json "
                     "(%d generated)" % (len(on), len(gen)))


def preflight_rows(slug: str, page_sentences: list[str] | None = None) -> list[tuple[str, str, str]]:
    import bindings as B
    ps = page_sentences if page_sentences is not None else B.page_sentences(slug)
    return [check(ps, generated(slug))]


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
