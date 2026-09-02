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
          u"–": "-", u"—": "-", u" ": " ", u"…": "...",
          # PDF LIGATURES. pdftotext returns "prespecified" and "stratified"
          # with a single fi glyph, so a transcription typed with two letters
          # never matches the bytes. Fourth character class to defeat a
          # comparison here, after The Lancet's middle dot, a Greek alpha and a
          # space before a full stop -- and the first caught by a check rather
          # than by somebody wondering why a true quotation would not match.
          u"ﬀ": "ff", u"ﬁ": "fi", u"ﬂ": "fl",
          u"ﬃ": "ffi", u"ﬄ": "ffl", u"ﬅ": "st", u"ﬆ": "st"}

# The states source_ledger.py treats as "somebody opened this". Kept as a
# literal rather than imported so this module has no load-order dependency on
# the ledger; the ledger owns the definition and this list must track it.
READ_STATES = ("full_text_held", "human_read")   # see source_ledger: machine_read is gone


def norm(text: str) -> str:
    """Comparison form. Punctuation is not identity.

    Same reasoning as counterexample._key: a curly apostrophe on the page and a
    straight one in the source are the same character to a reader, and two of
    nine claims on issue three were once unmatchable for exactly that.
    """
    for a, b in _SMART.items():
        text = text.replace(a, b)
    text = " ".join(text.lower().split())
    # A SPACE BEFORE A FULL STOP IS TYPESETTING, NOT IDENTITY.
    #
    # Extraction puts one there: S009 comes back as "...the 1,137-patient
    # result ." and the page prints "result." Those are the same words, and on
    # 2026-09-02 this check called the quotation altered because of the gap.
    #
    # Third character-level false alarm in two days -- The Lancet's middle dot,
    # a Greek alpha that extracts as "a", and now whitespace. None was about a
    # fact. A comparison form that is defeated by typography reports absence
    # where there is none, which is the failure this repository has recorded
    # more than any other.
    return re.sub(r"\s+([.,;:!?])", r"\1", text)


def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob(f"WHU-*-{slug}"))
    if not hits:
        raise SystemExit(f"no case directory for {slug!r}")
    return hits[0]


def path(slug: str) -> Path:
    return case_dir(slug) / "quotations.json"


def load(slug: str) -> dict | None:
    """The record, or None. An unreadable file is treated as absent.

    An empty or half-written quotations.json used to raise JSONDecodeError out
    of here and take the whole gate down with it. A malformed record is a
    reason to block a publish, which is what None does; it is not a reason for
    the board to stop working.
    """
    p = path(slug)
    if not p.exists():
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None
    return d if isinstance(d, dict) else None


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
    # AND THE CHANGE LOG, WHICH QUOTES THIS PAGE'S OWN WITHDRAWN SENTENCES.
    #
    # On 2026-09-01 three figures were corrected, and the log entry recording
    # the correction quoted each wrong sentence so a reader could see what it
    # had said. This check then demanded a source record for all three -- for
    # wording we had just established appears in no source, because we made it
    # up. Satisfying it was impossible and the only way to clear it would have
    # been to stop quoting our own errors.
    #
    # A quotation in the change log is a quotation of THIS PAGE, and the record
    # of what it said is the correction entry around it. Quotations of sources
    # live in the body, which is what this check reads.
    page_text = re.sub(r"<footer[^>]*id=[\"']updates[\"'][^>]*>.*?</footer>",
                       " ", page_text, flags=re.I | re.S)

    marked = re.findall(r"<q[^>]*>(.*?)</q>", page_text, re.I | re.S)
    marked += re.findall(r"<blockquote[^>]*>(.*?)</blockquote>", page_text, re.I | re.S)
    marked = [" ".join(html.unescape(re.sub(r"<[^>]+>", " ", m)).split()) for m in marked]

    t = html.unescape(re.sub(r"<[^>]+>", " ", page_text))
    t = " ".join(t.split())
    # CURLY QUOTES ARE DIRECTIONAL and pair themselves. Straight ones do not,
    # and pairing them with a length floor in the pattern DESYNCHRONISES the
    # whole page: "is it better?" is fourteen characters, below the floor, so
    # the pattern skipped it and paired ITS closing mark with the next opening
    # one. Everything after ran inverted, and the check pulled out four
    # "quotations" that were the page's own prose lying between real ones --
    # including one that put words in a press release's mouth that the page
    # never attributed to it.
    #
    # So: pair the marks first, sequentially, then apply the floor. Splitting
    # on the character is exactly that pairing -- odd segments are inside.
    literal = re.findall(r"\u201c([^\u201d]{%d,400})\u201d" % MIN_QUOTE, t)
    parts = t.split('"')
    inside = [parts[i] for i in range(1, len(parts), 2)]
    if len(parts) % 2 == 0:
        # An unbalanced straight quote makes every pairing after it a guess.
        # Say so rather than emit the guesses.
        inside = [q for q in inside if MIN_QUOTE <= len(q) <= 400]
        sys.stderr.write(
            "quotations: the page has an odd number of straight quotation "
            "marks, so straight-quoted passages after the unbalanced one may "
            "be paired wrongly\n")
    literal += [q for q in inside if MIN_QUOTE <= len(q) <= 400]

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


# ---------------------------------------------------------------------------
# attestations already on file
# ---------------------------------------------------------------------------

def attestations_on_file(slug: str, page: Path | None = None) -> list[dict]:
    """Every wording of a source this issue has ALREADY recorded, and where.

    WHY THIS EXISTS
    ---------------
    On 2026-08-31 this check reported six quotations resting on a source nobody
    had opened, four of them from NCCN v6.2026 -- a document whose licence
    forbids putting it through any AI tool, so clearing them meant asking the
    operator to read a guideline again.

    He had already read it. On 29 August he answered ten advocate questions from
    that document, by name and with locators, and the wording of every one of
    those four quotations was sitting in the repository:

        Q-02  inherited.json, IC-002 their_wording, checked_by fred
        Q-06  advocate/2026-08-29-adjudication.md, S001-04 ANSWER
        Q-10  advocate/2026-08-29-adjudication.md, S001-10 ANSWER
        Q-11  the same sentence as Q-06

    The other two had been read by the gate and recorded in its own report:

        Q-07  cdk46.html.gate.json, verdict c73, VERIFIED
        Q-12  cdk46.html.gate.json, verdict c41, VERIFIED

    Seven attestations, in three files, and a check written in a fourth asked
    for all of them again -- because it was built from the page and never looked
    at the record. That is not a missing attestation. It is a check that cannot
    read its own repository, and the cost of it falls on the one participant
    whose time cannot be bought back with a faster model.

    IT DOES NOT AUTO-FILL. A check that satisfies itself from its own fuzzy
    match is worth nothing; the whole value of `verbatim` is that a person or a
    named run put it there. What this does is make the BLOCK say WHERE THE
    ANSWER ALREADY IS, so nobody is ever again sent to re-read a licensed
    document for a sentence we transcribed two days ago.
    """
    out: list[dict] = []
    case = case_dir(slug)

    ip = case / "inherited.json"
    if ip.exists():
        try:
            for c in (json.loads(ip.read_text(encoding="utf-8")).get("claims") or []):
                if (c.get("their_wording") or "").strip():
                    out.append({"text": c["their_wording"],
                                "by": c.get("checked_by") or "?",
                                "on": c.get("checked_on") or "?",
                                "where": "inherited.json, %s their_wording" % c.get("id", "?")})
        except Exception:
            pass

    # ANSWER: blocks in the advocate adjudications -- the operator's own words,
    # from a source only a person is permitted to read.
    for adj in sorted((case / "advocate").glob("*-adjudication.md")):
        if "TEST" in adj.name:
            continue
        head, who, when = None, "?", "?"
        for line in adj.read_text(encoding="utf-8").splitlines():
            if line.startswith("### "):
                head, who, when = line[4:].strip(), "?", "?"
            elif line.startswith("ANSWERED BY:"):
                who = line.split(":", 1)[1].strip()
            elif line.startswith("ON:"):
                when = line.split(":", 1)[1].strip()
            elif line.startswith("ANSWER:"):
                out.append({"text": line.split(":", 1)[1].strip(), "by": who, "on": when,
                            "where": "%s, %s ANSWER" % (adj.name, head or "?")})

    # VERIFIED verdicts in the gate's own report carry the source's wording in
    # found_value. The gate reaches routes this environment does not.
    if page is not None:
        rp = page.with_suffix(page.suffix + ".gate.json")
        if rp.exists():
            try:
                rep = json.loads(rp.read_text(encoding="utf-8"))
            except Exception:
                rep = {}
            for vid, v in (rep.get("verdicts") or {}).items():
                if isinstance(v, dict) and v.get("verdict") == "VERIFIED" and v.get("found_value"):
                    out.append({"text": v["found_value"], "by": "the fact-check gate",
                                "on": "", "where": "%s, verdict %s" % (rp.name, vid)})
    return out


def _held_ids(slug: str) -> set:
    try:
        import source_store as _store
        return set(_store.held(slug))
    except Exception:
        return set()


def already_recorded(quote: str, on_file: list[dict]) -> dict | None:
    """The attestation that already contains this quotation, if there is one."""
    q = norm(quote)
    if not q:
        return None
    for a in on_file:
        if q in norm(a["text"]):
            return a
    return None


def preflight_rows(slug: str, page_text: str,
                   page: Path | None = None) -> list[tuple[str, str, str]]:
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
    # Before saying nobody has this wording, look. Seven attestations were
    # already on file when this check first ran and it asked for all of them
    # again -- four of them from a document only the operator is licensed to
    # read. See attestations_on_file.
    try:
        on_file = attestations_on_file(slug, page)
    except Exception:
        on_file = []
    found_already = []
    for q in on_page:
        r = by_key.get(norm(q))
        if not r:
            continue
        if r.get("kind") == "rhetorical":
            rhetorical += 1
            continue
        verbatim = norm(r.get("verbatim", ""))
        if not verbatim:
            a = already_recorded(q, on_file)
            if a:
                found_already.append(
                    "%s: THE WORDING IS ALREADY ON FILE — %s, recorded by %s%s. Copy it "
                    "into quotations.json; do not go and read the source again."
                    % (r.get("id") or q[:40], a["where"], a["by"],
                       " on %s" % a["on"] if a["on"] else ""))
            else:
                unattested.append("%s: nothing recorded as the source's wording"
                                  % (r.get("id") or q[:40]))
            continue
        if norm(q) not in verbatim:
            altered.append("%s: page has %r; source has %r"
                           % (r.get("id") or "?", q[:60], r.get("verbatim", "")[:60]))
            continue
        # AND THE TRANSCRIPTION AGAINST THE BYTES.
        #
        # Until 2026-09-02 the row above was the whole of "quotations match the
        # source": it compared the page's quotation against the `verbatim` field
        # -- WHICH A PERSON OR A MODEL TYPED. The document was never opened. A
        # mistyped transcription that matched the page passed, and a page
        # quotation that had drifted from the document passed with it, so long
        # as both drifted together. The check guarding the most damaging error
        # this publication can make had never read a source.
        #
        # Found by B15, which had to compare a quotation to the bytes for a
        # different reason and turned up two that do not survive it -- including
        # one where the page ends a sentence the source continues with a comma.
        import spancheck as _SC
        sid_now = r.get("source_id")
        if sid_now and sid_now in _held_ids(slug):
            body = norm(_SC._norm(_SC._text(slug, sid_now) or ""))
            if norm(r.get("verbatim", "")) not in body:
                altered.append(
                    "%s: the recorded wording is not in %s as printed — the "
                    "transcription is wrong, or the source is not what it was"
                    % (r.get("id") or "?", sid_now))
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
                 OK if not (unattested or found_already) else BAD,
                 "every quoted source has been read"
                 + (", %d passage(s) declared as our own phrasing" % rhetorical if rhetorical else "")
                 if not (unattested or found_already) else
                 "%d quotation(s) rest on a source nobody opened or recorded: %s"
                 % (len(unattested) + len(found_already),
                    " || ".join((found_already + unattested)[:2]))))
    # A separate row, because these two are not the same problem and must not
    # read as one. "Nobody has this wording" is work to be done. "The wording is
    # in the repository and this check did not look" is an hour of someone's
    # life about to be spent for nothing.
    if found_already:
        rows.append(("wording already in the record", BAD,
                     "%d quotation(s) can be closed from what is ALREADY on file, "
                     "without opening any source: %s"
                     % (len(found_already), " || ".join(found_already[:3]))))
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
    # Ids must be unique across the file. The first version numbered new
    # entries by position while reusing prior entries' own ids, so a re-init
    # produced two Q-02s, two Q-03s and so on -- in a record whose whole
    # purpose is to be looked up by id.
    taken = {r.get("id") for r in existing.values() if r.get("id")}
    out = []
    n = 0
    for q in extract(page.read_text(encoding="utf-8")):
        prior = existing.get(norm(q))
        if prior:
            out.append(prior)
            continue
        n += 1
        while ("Q-%02d" % n) in taken:
            n += 1
        taken.add("Q-%02d" % n)
        out.append({
            "id": "Q-%02d" % n,
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
