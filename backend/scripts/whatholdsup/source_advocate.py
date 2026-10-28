#!/usr/bin/env python3
"""
What Holds Up: the source advocate.

WHY THE OLD ROLE DID NOT WORK
-----------------------------
The fact-check gate has had an ADVOCATE role since issue one. Its system prompt
opens: "You are the head of communications for the organisation this draft is
about." It ran on issue two eighteen times and never asked the question that
mattered.

Two structural reasons, both fixable:

  1. IT HAD NO CLIENT. "The organisation this draft is about" is ambiguous on a
     page about three drugs from three companies assessed against one
     guideline. NCCN? Novartis? Lilly? Pfizer? An advocate without a named
     principal argues for nobody and produces balanced commentary, which is
     what every other role already produces.

  2. IT WAS GIVEN THE DRAFT AND NOT THE SOURCE. It could object to how our
     sentences read. It could not go into NCCN v6.2026 and find the paragraph
     that answered us, because it had never been pointed at the document. The
     omission that broke issue two -- that the guideline lists all three drugs
     as preferred and grades only the evidence differently -- was sitting in the
     source the whole time.

WHAT REPLACES IT
----------------
One call per source, with a named principal, given the source and every
sentence on the page that characterises it, and told plainly that it is counsel
rather than a referee. Its job is retrieval inside the document, not taste.

Per objection it must return either:

  - what the source says back, quoted, with a locator; or
  - an explicit statement that it looked and the source contains no answer,
    naming what it searched.

The second is as valuable as the first. A role that can return nothing without
saying so is indistinguishable from a role that found nothing, and the gate
already holds that an unrun check is not a pass.

THE ADJUDICATION IS THE LOAD-BEARING HALF
-----------------------------------------
The failure mode of an adversarial role is forty objections, a wave of the
hand, and a process that feels rigorous. So every brief must carry a written
verdict before the issue can publish:

    MERIT   yes / partly / no      -- and why, citing what we read
    EFFECT  changes / narrows / sharpens / corrects / none
                                  -- what it does to the conclusion
    DID     what we actually changed

Recorded whether or not we act. A "no merit" verdict with a bad reason is
visible afterwards; silence is not.

WHAT IT CANNOT DO
-----------------
It cannot read a source nobody can open, and it must not pretend to. Sources
the ledger marks `blocked` get no advocate. Sources marked `human_read` --
NCCN's licence forbids putting the guideline through any AI tool -- get an
advocate that produces QUESTIONS FOR THE PERSON WHO READ IT rather than
answers, because the alternative is a model guessing at a document it is not
allowed to open, which is precisely how "two-sided" reached the page five
times.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GATE = ROOT / "backend" / "scripts" / "signal" / "factcheck_draft.py"
LEDGER = Path(__file__).resolve().parent / "source_ledger.py"

_s = importlib.util.spec_from_file_location("factcheck_draft", GATE)
fc = importlib.util.module_from_spec(_s); _s.loader.exec_module(fc)
_l = importlib.util.spec_from_file_location("source_ledger", LEDGER)
sl = importlib.util.module_from_spec(_l); _l.loader.exec_module(sl)

OK, BAD, WARN = "ok", "BLOCKED", "warn"


# ---------------------------------------------------------------------------
# who speaks for a source
# ---------------------------------------------------------------------------

def principal(src: dict) -> str:
    """The party whose case the advocate argues.

    Named per source, because "the subject of this draft" is not a party and
    cannot have a position. A guideline panel defends differently from a trial's
    investigators, and both differ from a regulator approving a label.
    """
    t = (src.get("title") or "").lower()
    kind = src.get("type", "")
    if "nccn" in t:
        return ("the NCCN Breast Cancer Panel, authors of the guideline version "
                "this page cites")
    if kind == "label":
        return ("the regulatory affairs lead for the manufacturer whose approved "
                "prescribing information this is")
    if kind == "primary":
        return f"the investigators and statisticians who published {src.get('title','this trial')}"
    if kind == "comparison":
        return f"the authors of {src.get('title','this study')}"
    return f"the authors of {src.get('title','this source')}"


ADVOCATE_SYSTEM = """You are {principal}.

A publication called What Holds Up is about to publish an assessment that
characterises your work. You have been sent the sentences that refer to it. You
are counsel for your own document, not a referee: nobody here needs another
balanced summary, and a balanced summary is what this role produced for eighteen
consecutive runs while missing the thing that mattered.

Your job is RETRIEVAL, not taste. For each sentence, go into your own document
and find what it says back. The strongest objection is almost never "that is
unfair" — it is "you did not read section 4, which answers you."

The failure this role exists to prevent, stated plainly so you can look for its
shape: a page criticised a guideline for grading three drugs differently, and
never mentioned that the same guideline lists all three as *preferred* and grades
only the strength of the evidence. Every figure on the page was right. The
omission was the fact in the source that answered the question the page had
posed. That is what you are hunting for.

RETURN ONLY a JSON array. One object per objection:

{{
  "type":          "MISSTATES" | "LEAVES_OUT",
  "claim_quoted":  "MISSTATES: the exact sentence or phrase from the page you
                    object to. LEAVES_OUT: the page sentence nearest to where
                    the missing finding belongs",
  "objection":     "your objection, in one sentence",
  "source_says":   "what your document actually says, QUOTED, with a locator
                    (section, table, page). For LEAVES_OUT this is the omitted
                    finding itself, never a passage the page already uses.
                    Empty string if you could not find anything.",
  "locator":       "where in your document — section name, table number, page",
  "could_not_find":"if source_says is empty: what you searched and did not find.
                    Name the sections you looked in. An empty finding you can
                    describe is worth more than one you cannot.",
  "severity":      "SERIOUS" | "MINOR",
  "changes_conclusion": "CHANGES" | "NARROWS" | "NONE",
  "why":           "why this matters to what the page concludes"
}}

SERIOUS means you would ask for a correction and expect to get one.
CHANGES means the page's conclusion does not survive your objection as written.
NARROWS means the conclusion survives in a smaller form.
NONE means you object to the framing and the conclusion stands.

RULES.

1. Quote your own document or say you could not. A characterisation of what
   your document "generally holds" is exactly the error you are here to catch,
   and producing one yourself makes this role worthless.
2. Do not manufacture grievances. A page that is hard on you and accurate is
   not objectionable, and saying so is more useful than a list nobody will act
   on. Returning an empty array is a real answer.
3. Do not object to a figure being wrong unless you can quote the right one.
   Other checks handle figures; you are here for what the page left out. If the
   page leaves out a finding of your document that answers its question, say
   LEAVES_OUT and quote that finding; do not quote the passage the page already
   uses. MISSTATES is for a page sentence your document contradicts or
   qualifies.
4. Report every instance. If the same omission affects three sentences, return
   three objections. A fault fixed in one place and published in another is how
   the count in issue two went stale.
"""

QUESTIONS_SYSTEM = """You are {principal}.

A publication is about to publish an assessment characterising your work, and
you have been sent the sentences that refer to it. There is a constraint you
must respect absolutely:

  YOU CANNOT READ THE SOURCE DOCUMENT. {why_not}

So do not answer. Do not reason about what such a document probably says, do
not search the web for a summary of it, and do not produce a quotation. A model
guessing at the contents of a document it cannot open is precisely how this
publication printed a false characterisation of a statistical section five
times over.

Instead, write the QUESTIONS that the person who *has* read the document should
be asked before this publishes. Good questions are specific, answerable by
opening the document to one place, and aimed at what would most change the
page's conclusion if the answer went the other way.

RETURN ONLY a JSON array:

{{
  "claim_quoted": "the sentence from the page this question tests",
  "question":     "the question, answerable by opening the document",
  "where_to_look":"the section, table or heading to open",
  "why_it_matters":"what changes if the answer is not what the page assumes",
  "severity":     "SERIOUS" | "MINOR"
}}

The single most useful question you can ask is some form of: *does this document
say anything, anywhere, that answers the criticism this page is making of it?*
Ask it, and make it specific to what the page actually claims.
"""


REQUOTE_SYSTEM = """You are {principal}. Earlier you raised an objection to a
publication's page and quoted your own document in support of it. That
quotation is not in your document as the publication holds it, word for word.

Below is the objection and your document's text as held. Quote the passage
that supports your objection EXACTLY as it appears in that text, character for
character, with no quote marks of your own. If the held text contains no such
passage, return source_says empty and say in could_not_find what you looked
for. Do not paraphrase and do not search the web.

RETURN ONLY a JSON object:
{{"source_says": "...", "locator": "...", "could_not_find": "..."}}
"""

QUOTE_NOTE = "the quotation is not in the held text"

# OBJECTION TYPES (post-study fix 2, step 1, 2026-10-27). The schema had one
# shape, an objection TO a page sentence, so an omission had to be pinned to an
# accurate sentence and the ruling model, asked whether the source supports that
# sentence, rejected it (WHU-S07 rulings.jsonl:12, item S003-13).
# docs/whu-fix2-omission-rulings-design.md, section 1.
MISSTATES, LEAVES_OUT = "MISSTATES", "LEAVES_OUT"
OBJECTION_TYPES = (MISSTATES, LEAVES_OUT)
# A brief written before the type existed: an omission is SUSPECTED from its
# wording. The flag only routes the objection to a re-ask; it decides nothing.
OMISSION_WORDING = re.compile(
    r"\b(?:omit(?:s|ted)?|omission|leaves?\s+out|left\s+out|does\s+not\s+mention|doesn't\s+mention"
    r"|never\s+mentions?|fails\s+to\s+(?:mention|note|report)|not\s+mention(?:ed)?|missing)\b", re.I)


def omission_kind(o: dict) -> tuple[str, str]:
    """(MISSTATES or LEAVES_OUT, "declared" | "suspected" | "default")."""
    t = (o.get("type") or "").strip().upper()
    if t in OBJECTION_TYPES:
        return t, "declared"
    if OMISSION_WORDING.search("%s %s" % (o.get("objection") or "", o.get("why") or "")):
        return LEAVES_OUT, "suspected"
    return MISSTATES, "default"


def needs_reask(o: dict, held_text: str, bound_spans: list[str]) -> bool:
    """An omission whose quotation is empty, or is a passage the page already
    binds, has not quoted the omitted finding: it is asked once more for it."""
    import audit_stage as A
    if omission_kind(o)[0] != LEAVES_OUT:
        return False
    says = (o.get("source_says") or "").strip()
    if not says:
        return True
    at = A.locate(says, held_text or "")
    if at is None:
        return False          # not in the held text: NOT_IN_SOURCE, decided by code later
    for sp in bound_spans or []:
        b = A.locate(sp, held_text or "")
        if b and b[0] < at[1] and at[0] < b[1]:
            return True
    return False


REASK_OMISSION_SYSTEM = """You are {principal}. Earlier you objected that a
publication's page leaves out a finding of your document, but the passage you
quoted is one the page already uses, or you quoted nothing.

Below are your objection, the page sentences already bound to your document,
and your document's text as held. Quote the OMITTED FINDING itself, EXACTLY as
it appears in that text, character for character, with no quote marks of your
own: the sentence or clause the page leaves out. If there is none, return
source_says empty and say in could_not_find what you looked for. Do not
paraphrase and do not search the web.

RETURN ONLY a JSON object:
{{"source_says": "...", "locator": "...", "could_not_find": "..."}}
"""


def reask_omission(b: dict, o: dict, text: str, bound: list[str], ask=None) -> dict:
    """One re-ask for the omitted finding itself. Returns the objection
    updated (type LEAVES_OUT, the new quotation, the first one kept as
    source_says_first) when the new quotation is in the held text; otherwise
    the objection unchanged with reask_note set. `ask(system, user)` returns
    the parsed reply; by default a metered call (fc.call, search off)."""
    import audit_stage as A
    doc, _cut = A.trim(text, [w for w in re.findall(r"[A-Za-z][A-Za-z'-]{6,}|\d[\d.,]*%?",
                                                    (o.get("objection") or "") + " " + (o.get("why") or ""))])
    system = REASK_OMISSION_SYSTEM.format(principal=b.get("principal") or "the source's author")
    user = json.dumps({"objection": {k: o.get(k) for k in ("claim_quoted", "objection", "why", "source_says")},
                       "already_on_the_page": bound, "your_document_as_held": doc}, ensure_ascii=False)
    if ask is None:
        got = fc.call(system, user, search=False, label="advocate-reask-omission:%s" % b.get("source"))
    else:
        got = ask(system, user)
    got = got if isinstance(got, dict) else {}
    again = (got.get("source_says") or "").strip()
    out = dict(o)
    if again and A.quoted_in(again, text):
        out.update(type=LEAVES_OUT, source_says=again, source_says_first=o.get("source_says") or "",
                   locator=got.get("locator") or o.get("locator"),
                   quotation_check={"in_held_text": True, "asked": "omission re-ask"})
    else:
        out["reask_note"] = ("the re-ask did not quote an omitted finding in the held text"
                             + (": %s" % got.get("could_not_find") if got.get("could_not_find") else ""))
    return out


QUOTE_FIELDS = ("source_says", "source_says_first", "locator", "quotation_check")


def quote_key(b: dict, i: int) -> str:
    """One objection's identity within a run: its source and its position."""
    return "%s#%d" % (b.get("source"), i)


def check_quotations(slug: str, briefs: list[dict], held: dict[str, str], ask=None,
                     log=None, done: dict | None = None) -> list[dict]:
    """Check every advocate quotation against the held text of its source
    (reading order; audit_stage.quoted_in), when it is written (GAP-018).

    A failing quotation gets ONE re-ask of the advocate, for that objection
    only, with the held text it must quote from. If it still fails, the
    objection keeps the true note QUOTE_NOTE for the ruling model, and the
    advocate's own words stay on the record. Every quotation checked is logged
    raw through `log` (advocate/quote_checks.jsonl: source text, never
    committed). `ask(brief, objection, text)` returns the advocate's reply; by
    default it is a metered call.

    RESUMABLE (2026-10-20). Each result is handed to `log` as soon as it is
    known, with its key (quote_key) and the objection's quotation fields after
    the check. `done` maps a key to such a record from an earlier, stopped run:
    that objection takes the saved fields and is neither checked nor re-asked
    again."""
    import audit_stage as A
    ask = ask or _requote
    out = []
    for b in briefs:
        if b.get("mode") != "objections":
            continue
        text = held.get(b["source"]) or ""
        for i, o in enumerate(b.get("objections") or []):
            key = quote_key(b, i)
            if done and key in done:
                o.update(done[key].get("objection_after") or {})
                out.append(done[key])
                continue
            says = (o.get("source_says") or "").strip()
            if not says:
                continue
            rec = {"key": key, "source": b["source"], "claim_quoted": o.get("claim_quoted"), "first": says}
            if A.quoted_in(says, text):
                o["quotation_check"] = {"in_held_text": True, "asked": 1}
                rec["result"] = "in the held text"
            else:
                got = ask(b, o, text) or {}
                again = (got.get("source_says") or "").strip()
                rec["re_ask"] = again
                if again and A.quoted_in(again, text):
                    o["source_says_first"] = says
                    o["source_says"] = again
                    if got.get("locator"):
                        o["locator"] = got["locator"]
                    o["quotation_check"] = {"in_held_text": True, "asked": 2}
                    rec["result"] = "in the held text after one re-ask"
                else:
                    o["quotation_check"] = {"in_held_text": False, "asked": 2, "note": QUOTE_NOTE}
                    rec["result"] = QUOTE_NOTE
            rec["objection_after"] = {k: o[k] for k in QUOTE_FIELDS if k in o}
            if log:
                log(rec)
            out.append(rec)
    return out


def _requote(b: dict, o: dict, text: str) -> dict:
    import audit_stage as A
    doc, _cut = A.trim(text, [w for w in re.findall(r"[A-Za-z][A-Za-z'-]{6,}|\d[\d.,]*%?",
                                                    (o.get("source_says") or "") + " " + (o.get("objection") or ""))])
    user = json.dumps({"objection": {k: o.get(k) for k in ("claim_quoted", "objection", "source_says")},
                       "your_document_as_held": doc}, ensure_ascii=False)
    got = fc.call(REQUOTE_SYSTEM.format(principal=b.get("principal") or "the source's author"), user,
                  search=False, label="advocate-requote:%s" % b["source"])
    return got if isinstance(got, dict) else {}


# ---------------------------------------------------------------------------
# which sentences reach which source: the binding, never the wording (GAP-020)
# ---------------------------------------------------------------------------
#
# The advocate used to hand a source every page sentence containing one of the
# source's "identifiers" (words from its title, as sources.json spells it). On
# WHU-P04 that misrouted silently: a sentence bound to one document but naming
# another's publisher went to the wrong counsel, and a sentence bound to a
# source whose title words it never used reached nobody. Now a sentence goes to
# the sources its binding row rests on -- the span's source, also_rests_on and
# premises (audit_stage.sources_of) -- and to no other. A sentence with no row,
# or a row that rests on no source, reaches no source, and the run says so.

NO_ROW = "no binding row"
NO_SOURCE = "its binding row rests on no source"


def binding_rows(slug: str) -> dict:
    import bindings as B
    return B.load(slug).get("bindings") or {}


def route(page_text: str, rows: dict) -> tuple[dict[str, list[str]], list[dict]]:
    """({source id: [sentences]}, [unrouted]) for every sentence of the page.
    A row is found by the sentence's fingerprint (bindings.fingerprint), or by
    the fingerprint of the sentence the row records."""
    import audit_stage as A
    fp = A.fingerprint
    by_fp = dict(rows)
    for k, v in rows.items():
        if isinstance(v, dict) and v.get("sentence"):
            by_fp.setdefault(fp(v["sentence"]), v)
    routed: dict[str, list[str]] = {}
    unrouted = []
    for s in sl.sentences(page_text):
        s = " ".join(s.split())
        if not s:
            continue
        row = by_fp.get(fp(s))
        ids = A.sources_of(row)
        if not ids:
            unrouted.append({"sentence": s, "why": NO_ROW if row is None else NO_SOURCE})
            continue
        for i in ids:
            if s not in routed.setdefault(i, []):
                routed[i].append(s)
    return routed, unrouted


def brief_for(slug: str, src: dict, sents: list[str]) -> dict | None:
    """SENTS: the page sentences bound to this source (route())."""
    acc = sl.access_of(src)
    state = acc.get("state")
    if not sents:
        return None

    if state == sl.BLOCKED:
        return {"source": src["id"], "title": src.get("title"),
                "mode": "skipped", "state": state,
                "note": ("nobody can open this source, so no advocate runs on it. "
                         "The ledger blocks new characterisation of it instead — "
                         "which is the correct control, because an advocate here "
                         "would be guessing."),
                "objections": []}

    who = principal(src)
    ctx = json.dumps({
        "source": {k: src.get(k) for k in ("id", "title", "url", "type", "used_for")},
        "sentences_about_you": sents[:60],
    }, indent=1, ensure_ascii=False)

    if state == sl.HUMAN_READ:
        why = acc.get("note") or "It is not available to any automated tool here."
        out = fc.call(QUESTIONS_SYSTEM.format(principal=who, why_not=why),
                      ctx, search=False, label=f"advocate-questions:{src['id']}")
        mode = "questions"
    else:
        out = fc.call(ADVOCATE_SYSTEM.format(principal=who),
                      ctx, search=True, label=f"advocate:{src['id']}")
        mode = "objections"

    if out is None:
        # An unrun role must not look like a role that found nothing.
        return {"source": src["id"], "title": src.get("title"), "mode": mode,
                "state": state, "principal": who, "failed": True,
                "note": "the call returned nothing usable — this is an UNRUN check, not a clean one",
                "objections": []}
    if isinstance(out, dict):
        out = out.get("objections") or out.get("questions") or out.get("results") or []
    return {"source": src["id"], "title": src.get("title"), "mode": mode,
            "state": state, "principal": who, "objections": out}


# ---------------------------------------------------------------------------
# adjudication
# ---------------------------------------------------------------------------

# OUTPUT FILES ARE NAMED BY RUN ID (2026-10-21): <run id>-briefs.json and
# <run id>-adjudication.md, the run ID being the run directory's UTC stamp
# (advocate/runs/<run id>/). They were named by date.today(), the LOCAL date:
# WHU-P02's run of 2026-10-21 00:02Z wrote advocate/2026-10-20-briefs.json,
# the name of the run before it, whose briefs number their objections
# differently. Two runs never share a name now. Files written before keep
# their date names; every reader globs "*-briefs.json" / "*-adjudication.md"
# and pairs the two by the whole name before the suffix.

def adjudication_path(slug: str, name: str) -> Path:
    d = sl.case_dir(slug) / "advocate"
    d.mkdir(exist_ok=True)
    return d / f"{name}-adjudication.md"


def briefs_path(slug: str, name: str) -> Path:
    d = sl.case_dir(slug) / "advocate"
    d.mkdir(exist_ok=True)
    return d / f"{name}-briefs.json"


VERDICT = re.compile(r"^\s*MERIT:\s*(yes|partly|no|not_ruled_protected)\b", re.I | re.M)
# NOT RULED: A PROTECTED SENTENCE (post-study, mid-rerun tool fix, 2026-10-28).
# An objection (or omission objection) aimed at a protected sentence is never put
# to a ruling (ruling.split_protected) and waits for a person. "MERIT:
# not_ruled_protected" is how the person closes it, and it is accepted ONLY when
# the sentence the item targets is protected (bindings.protected_kind, or the
# binding row's "protected" marker): see protected_check. It is not a merit
# verdict, so the readers' list never shows it; not_ruled_protected() lists the
# items for the study log.
NOT_RULED_PROTECTED = "not_ruled_protected"
TARGET_LINE = re.compile(r"^\*\*(?:We say|Nearest page sentence)\.\*\*[ \t]*(.*)$", re.M)
# The EFFECT line is read in two steps, and the split is the point. Whether a
# person ANSWERED is settled by the fields being present; which WORD they used
# is a vocabulary question and is reported as one. Until 11 September 2026 the
# two were one regex, so three questions about the NCCN guideline -- answered
# by name, quoted, with locators, on 3 September -- were reported for eight
# days as "no person has answered" because the answers said "sharpens" and
# "corrects". A complete answer is never reported as unanswered.
EFFECT_LINE = re.compile(r"^\s*EFFECT:\s*(\S+)", re.I | re.M)
EFFECT_WORDS = ("changes", "narrows", "sharpens", "corrects", "none")
EFFECT = re.compile(r"^\s*EFFECT:\s*(%s)\b" % "|".join(EFFECT_WORDS), re.I | re.M)
# An omission objection (LEAVES_OUT) is closed by the omission ruling's outcome
# and what was done, not by MERIT/EFFECT (fix 2, step 1).
# not_added_cap (mid-rerun tool fix, 2026-10-28): not added because a budget was
# full; closed only when the OMISSION or DID line names which cap ("additions" or
# "declarations", omissions.cap_of).
OMISSION_WORDS = ("add", "out_of_scope", "not_material", "not_in_source", "not_added_cap")
OMISSION_LINE = re.compile(r"^\s*OMISSION:\s*(%s)\b(.*)$" % "|".join(OMISSION_WORDS), re.I | re.M)
DID_LINE = re.compile(r"^\s*DID:\s*(\S.*)$", re.M)

# A question put to the human reader is only closed when a person has opened the
# document and written down what it says. Not when someone has read the question
# and formed a view about it.
#
# This is the loop that was missing. Issue two's guideline could not be read by
# any automated check -- NCCN's licence forbids it -- and that one document held
# the fact that decided the piece. Every other source could be machine-checked,
# so the pipeline behaved as though the whole page had been checked. It had not.
# Where a source can only be read by a person, the person is the check, and a
# check nobody ran must not look like a check that passed.
ANSWERED_BY = re.compile(r"^\s*ANSWERED BY:\s*(\S.*)$", re.M)
ANSWER = re.compile(r"^\s*ANSWER:\s*(\S.*)$", re.M)
LOCATOR = re.compile(r"^\s*LOCATOR:\s*(\S.*)$", re.M)

# A WITHDRAWAL IS NOT AN ANSWER, AND IT IS NOT A FAILURE TO ANSWER EITHER.
# S001-14 was withdrawn by claude on 3 September -- the record already held
# the fact it asked for -- and until 11 September preflight listed it under
# "no person has answered", which is false: nobody failed to answer it. The
# editor's ruling, same principle as the EFFECT ruling: a question closed by
# withdrawal is closed, provided the withdrawal says WHO withdrew it and WHY,
# and it is reported in its own row, never among the unanswered.
WITHDRAWN_BY = re.compile(r"^\s*WITHDRAWN BY:\s*(\S.*)$", re.M)
WITHDRAWN_WHY = re.compile(r"^\s*WHY:\s*(\S.*)$", re.M)


def _withdrawal(chunk: str) -> tuple[str, str] | None:
    """(who, why) when both are on the record; ("", why) or (who, "") when the
    withdrawal is attempted but incomplete; None when nothing was withdrawn."""
    who = WITHDRAWN_BY.search(chunk)
    why = WITHDRAWN_WHY.search(chunk)
    if not who and not why:
        return None
    return ((who.group(1).strip() if who else ""), (why.group(1).strip() if why else ""))


def protected_check(slug: str):
    """sentence -> True when it is protected on SLUG's page (bindings.protected_kind,
    with the binding row's marker when the sentence has a row)."""
    import bindings as B
    rows = []

    def check(s: str) -> bool:
        if not rows:                 # read once, and only when an item asks
            try:
                rows.append(B.load(slug).get("bindings") or {})
            except (Exception, SystemExit):
                rows.append({})
        return bool(s) and B.protected_kind(s, rows[0].get(B.fingerprint(s))) is not None
    return check


def _closed(chunk: str, mode: str, is_protected=None) -> bool:
    """Has a person written the verdict? Presence of the fields decides this;
    the EFFECT word's spelling does not (see unrecognised_effect). A complete
    withdrawal -- who, and why -- closes a question too (see _withdrawal).
    MERIT: not_ruled_protected closes an item only when IS_PROTECTED (see
    protected_check) says the sentence it targets is protected; with no
    checker it does not."""
    if mode == "questions":
        w = _withdrawal(chunk)
        if w is not None:
            return bool(w[0] and w[1])
        return bool(ANSWERED_BY.search(chunk) and ANSWER.search(chunk)
                    and LOCATOR.search(chunk) and EFFECT_LINE.search(chunk))
    om, did = OMISSION_LINE.search(chunk), DID_LINE.search(chunk)
    if om and did:
        if om.group(1).lower() != "not_added_cap":
            return True
        import omissions as O
        return O.cap_of("%s %s" % (om.group(2), did.group(1))) is not None
    v = VERDICT.search(chunk)
    if v and v.group(1).lower() == NOT_RULED_PROTECTED:
        t = TARGET_LINE.search(chunk)
        return bool(is_protected and t and is_protected(t.group(1).strip()))
    return bool(v and EFFECT_LINE.search(chunk))


def unrecognised_effect(chunk: str) -> str | None:
    """The EFFECT word if it is outside the vocabulary, else None."""
    m = EFFECT_LINE.search(chunk)
    if not m:
        return None
    word = m.group(1).strip().rstrip(".,;:")
    return None if word.lower() in EFFECT_WORDS else word


def write_template(slug: str, day: str, briefs: list[dict], name: str | None = None) -> Path:
    """The adjudication file, named NAME (the run ID; the day for a caller
    that gives none)."""
    p = adjudication_path(slug, name or day)
    lines = [f"# {slug} — source advocate, {day}" + (f", run {name}" if name else ""), "",
             "One section per item. Each must be closed before this issue can",
             "publish. An open item blocks; an item closed \"no merit\", with the",
             "reason on the record, does not.", "",
             "For an OBJECTION, from a source a machine could read:", "",
             "    MERIT:  yes | partly | no   — and why, citing what you read",
             "            (or not_ruled_protected, only on a protected sentence)",
             "    EFFECT: changes | narrows | sharpens | corrects | none",
             "    DID:    what actually changed, or nothing and why", "",
             "For an OMISSION (type LEAVES_OUT), closed by the omission ruling:", "",
             "    OMISSION: add | out_of_scope | not_material | not_in_source | not_added_cap",
             "    DID:      what was added, or why nothing was", "",
             "For a QUESTION, from a source only a person is permitted to read:", "",
             "    ANSWERED BY: a person's name. Not \"the team\", not a role.",
             "    ON:          the date they opened the document",
             "    ANSWER:      what it says, quoted",
             "    LOCATOR:     section, table or page",
             "    EFFECT:      changes | narrows | sharpens | corrects | none",
             "    DID:         what changed", "",
             "Or, for a QUESTION the record already answers, a withdrawal:", "",
             "    WITHDRAWN BY: a person's name, or the role that withdrew it",
             "    ON:           the date",
             "    WHY:          what on the record already settles it",
             "    DID:          what was done instead", "",
             "The second form exists because of NCCN v6.2026: one document, readable",
             "by no automated check here, holding the fact that decided the piece.",
             "Everything else on the page could be machine-checked, so the pipeline",
             "behaved as though the page had been checked. Where only a person can",
             "read the source, the person is the check.", ""]
    n = 0
    for b in briefs:
        lines += ["", "---", "",
                  f"## {b['source']} — {b.get('title','')}",
                  f"*Advocate: {b.get('principal','—')}*  ",
                  f"*Ledger state: {b.get('state')}*  "]
        if b.get("failed"):
            lines += ["", "**THE CALL FAILED. This is an unrun check, not a clean one.**", ""]
        if b.get("note"):
            lines += ["", f"> {b['note']}", ""]
        for o in b.get("objections", []):
            n += 1
            lines += ["", f"### {b['source']}-{n:02d} — {o.get('severity','?')}"
                          f" / {o.get('changes_conclusion', o.get('severity','?'))}", ""]
            if b["mode"] == "questions":
                lines += [f"**Question.** {o.get('question','')}", "",
                          f"**Where to look.** {o.get('where_to_look','')}", "",
                          f"**On this claim.** {o.get('claim_quoted','')}", "",
                          f"**Why it matters.** {o.get('why_it_matters','')}", ""]
            else:
                kind, how = omission_kind(o)
                lines += [f"**Type.** {kind}" + ("" if how == "declared" else f" ({how})"), "",
                          f"**{'Nearest page sentence' if kind == LEAVES_OUT else 'We say'}.** "
                          f"{o.get('claim_quoted','')}", "",
                          f"**They object.** {o.get('objection','')}", ""]
                if o.get("source_says"):
                    lines += [f"**Their document says.** {o.get('source_says','')}",
                              f"  — *{o.get('locator','no locator given')}*", ""]
                else:
                    lines += [f"**They looked and found nothing.** "
                              f"{o.get('could_not_find','(not stated — treat as unrun)')}", ""]
                lines += [f"**Why it matters.** {o.get('why','')}", ""]
            if b["mode"] == "questions":
                lines += ["ANSWERED BY: ", "ON:          ", "ANSWER:      ",
                          "LOCATOR:     ", "EFFECT:      ", "DID:         ", ""]
            elif omission_kind(o)[0] == LEAVES_OUT:
                lines += ["OMISSION: ", "DID:      ", ""]
            else:
                lines += ["MERIT:  ", "EFFECT: ", "DID:    ", ""]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _modes(slug: str) -> dict[str, str]:
    """source id -> mode, from the most recent briefs file."""
    d = sl.case_dir(slug) / "advocate"
    out = {}
    for f in sorted(d.glob("*-briefs.json")) if d.exists() else []:
        for b in json.loads(f.read_text(encoding="utf-8")):
            out[b["source"]] = b.get("mode", "objections")
    return out


def _chunks(slug: str):
    """(file name, item heading, chunk text, mode) for every adjudicated item."""
    d = sl.case_dir(slug) / "advocate"
    if not d.exists():
        return
    modes = _modes(slug)
    for f in sorted(d.glob("*-adjudication.md")):
        if "TEST" in f.name:
            continue
        text = f.read_text(encoding="utf-8")
        for chunk in re.split(r"(?=^### )", text, flags=re.M)[1:]:
            head = chunk.splitlines()[0][4:].strip()
            sid = head.split("-")[0]
            yield f.name, head, chunk, modes.get(sid, "objections")


def open_items(slug: str) -> tuple[list[str], list[str]]:
    """(open objections, open questions for a human). Both block. A question
    with an incomplete withdrawal is neither: see withdrawals()."""
    objs, qs = [], []
    is_protected = protected_check(slug)
    for fname, head, chunk, mode in _chunks(slug):
        if _closed(chunk, mode, is_protected):
            continue
        if mode == "questions" and _withdrawal(chunk) is not None:
            continue          # reported by withdrawals(), not as unanswered
        (qs if mode == "questions" else objs).append(f"{fname}: {head}")
    return objs, qs


def withdrawals(slug: str) -> tuple[list[str], list[str]]:
    """(complete withdrawals, incomplete ones). A complete one names who and
    why; an incomplete one is a closure nobody signed."""
    done, incomplete = [], []
    for fname, head, chunk, mode in _chunks(slug):
        if mode != "questions":
            continue
        w = _withdrawal(chunk)
        if w is None:
            continue
        who, why = w
        if who and why:
            done.append(f"{head} — withdrawn by {who}: {why[:80]}")
        else:
            incomplete.append(f"{head} — withdrawal lacks {'WHO' if not who else 'WHY'}")
    return done, incomplete


def vocabulary_problems(slug: str) -> list[str]:
    """Closed items whose EFFECT word is outside the vocabulary. Reported by
    word, as a vocabulary problem -- never as an item nobody answered."""
    out = []
    for fname, head, chunk, mode in _chunks(slug):
        w = unrecognised_effect(chunk)
        if w is not None:
            out.append(f"{head}: EFFECT \"{w}\"")
    return out


def not_ruled_protected(slug: str) -> list[str]:
    """Items closed "MERIT: not_ruled_protected" on a protected sentence: for the
    study log, never the readers' list."""
    is_protected = protected_check(slug)
    return ["%s: %s" % (fname, head) for fname, head, chunk, mode in _chunks(slug)
            if mode != "questions" and (VERDICT.search(chunk) or [None, ""])[1].lower() == NOT_RULED_PROTECTED
            and _closed(chunk, mode, is_protected)]


def unadjudicated(slug: str) -> list[str]:
    o, q = open_items(slug)
    return o + q


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    d = sl.case_dir(slug) / "advocate"
    briefs = [f for f in (sorted(d.glob("*-briefs.json")) if d.exists() else [])
              if "TEST" not in f.name]
    if not briefs:
        return [("source advocate", BAD,
                 "never run on this issue — no advocate has argued for any source "
                 "this page characterises")]
    objs, qs = open_items(slug)
    rows = [("source advocate", OK,
             f"{len(briefs)} run(s), latest {briefs[-1].name[:-len('-briefs.json')]}")]
    rows.append(("advocate objections closed", OK if not objs else BAD,
                 "every objection carries a written verdict and effect"
                 if not objs else
                 f"{len(objs)} with no MERIT/EFFECT (or OMISSION/DID) recorded: " + "; ".join(objs[:3])))
    rows.append(("questions answered by a reader", OK if not qs else BAD,
                 "every question about a source only a person can read has been "
                 "answered, by name, from the document"
                 if not qs else
                 f"{len(qs)} question(s) about a licence- or paywall-restricted source "
                 f"that no person has answered. Nothing here can answer them: "
                 + "; ".join(qs[:3])))
    done, incomplete = withdrawals(slug)
    if done:
        rows.append(("questions withdrawn, with who and why", WARN,
                     f"{len(done)} question(s) closed by withdrawal rather than by an "
                     f"answer; each names who withdrew it and why: " + "; ".join(done[:3])))
    if incomplete:
        rows.append(("withdrawals name who and why", BAD,
                     f"{len(incomplete)} withdrawal(s) missing the person or the reason -- "
                     f"a closure nobody signed is not a closure: " + "; ".join(incomplete[:3])))
    nrp = not_ruled_protected(slug)
    if nrp:
        rows.append(("objections not ruled: protected sentence", OK,
                     f"INFO, for the study log (not the readers' list): {len(nrp)} item(s) on a "
                     f"protected sentence, closed not_ruled_protected: " + "; ".join(nrp[:4])))
    vocab = vocabulary_problems(slug)
    if vocab:
        rows.append(("effect vocabulary recognised", WARN,
                     f"{len(vocab)} answered item(s) record an EFFECT word outside "
                     f"{' / '.join(EFFECT_WORDS)}. The answer stands; the word is "
                     f"unrecognised: " + "; ".join(vocab[:4])))
    return rows


# ---------------------------------------------------------------------------
# a run that can stop and carry on (2026-10-20)
# ---------------------------------------------------------------------------
#
# On 2026-10-20 the WHU-P02 advocate read 17 sources, drafted 27 objections and
# spent $4.28, then the day cap stopped a re-ask in the quotation check; the run
# exited before writing anything, so all of it would have been bought again.
# Now every run has a directory, advocate/runs/<UTC stamp>/, and saves as it
# goes: each source's brief (its objections) to briefs.jsonl when the call that
# drafted it returns, and each quotation check to quote_checks.jsonl when it is
# decided. A cap stop marks the run "stopped" in state.json and exits 3; `run
# SLUG --resume RUN_DIR` carries on, refusing if any input has changed, and
# never repeats a saved brief or a saved check. A brief whose call returned
# nothing usable ("failed") is not saved, so a resumed run asks again.

def runs_dir(slug: str) -> Path:
    return sl.case_dir(slug) / "advocate" / "runs"


def _sha(s: str) -> str:
    import hashlib
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()


def run_inputs(args, text: str, srcs: list[dict], held: dict[str, str], day: str, only,
               rows: dict | None = None) -> dict:
    """Everything a run's output depends on. A resume refuses if any of it
    (the day aside) differs from the stopped run's."""
    return {"slug": args.slug, "page": args.page, "page_body_sha256": _sha(text),
            "sources_sha256": _sha(json.dumps(srcs, sort_keys=True, ensure_ascii=False)),
            "held_sha256": {s["id"]: _sha(held.get(s["id"]) or "") for s in srcs},
            "bindings_sha256": _sha(json.dumps(rows or {}, sort_keys=True, ensure_ascii=False)),
            "only": sorted(only) if only else None,
            "prompts_sha256": {"advocate": _sha(ADVOCATE_SYSTEM), "questions": _sha(QUESTIONS_SYSTEM),
                               "requote": _sha(REQUOTE_SYSTEM)},
            "model": getattr(fc, "SIGNAL_MODEL", None), "day": day}


def _jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _append(p: Path, rec: dict) -> None:
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        f.flush()


def _state(rd: Path, **kw) -> None:
    (rd / "state.json").write_text(json.dumps(dict(kw, at=datetime.now(timezone.utc).isoformat(
        timespec="seconds")), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def is_cap_stop(exc: BaseException) -> bool:
    """A spend cap stopped the call (spend_ledger.OverCap or OverIssueCap, from
    whichever copy of the module raised it)."""
    return any(c.__name__ in ("OverCap", "OverIssueCap") for c in type(exc).__mro__)


def would_call(s: dict, routed: dict[str, list[str]]) -> bool:
    st = sl.access_of(s).get("state")
    return st not in (sl.NOT_OPENED, sl.BLOCKED) and bool(routed.get(s["id"]))


def cmd_run(args) -> int:
    page = ROOT / args.page
    # THE BODY, NOT THE CHANGE LOG. On its first run the advocate spent 7 of 28
    # objections arguing against corrections this page had already made and
    # printed -- "it credited the five-year data with clearing the no-effect
    # line when the body says year three" is our own record of an error we
    # fixed, and it was handed to counsel as a claim to attack. See
    # source_ledger.body_only.
    text = sl.plain(sl.body_only(page.read_text(encoding="utf-8")))
    doc = sl.load(args.slug)
    import audit_stage as A
    held = A.held_for_audit(args.slug)
    resume = getattr(args, "resume", None)
    if resume:
        rd = Path(resume)
        if not rd.is_absolute() and not rd.exists():
            rd = runs_dir(args.slug) / resume
        try:
            saved = json.loads((rd / "inputs.json").read_text(encoding="utf-8"))
            st = json.loads((rd / "state.json").read_text(encoding="utf-8"))
        except Exception as exc:
            raise SystemExit("cannot resume: %s is not an advocate run directory (%s)" % (rd, exc))
        if st.get("status") != "stopped":
            raise SystemExit("cannot resume: the run in %s is %s, not stopped" % (rd, st.get("status")))
        if args.only or args.day:
            raise SystemExit("--resume takes --only and --day from the stopped run; give neither")
        day, only = saved["day"], saved.get("only")
    else:
        day = args.day or datetime.now(timezone.utc).date().isoformat()
        only = args.only
    srcs = doc.get("sources", [])
    if only:
        srcs = [s for s in srcs if s["id"] in set(only)]
    rows = binding_rows(args.slug)
    routed, unrouted = route(text, rows)
    inputs = run_inputs(args, text, srcs, held, day, only, rows)
    if resume:
        changed = sorted(k for k in inputs if k != "day" and inputs[k] != saved.get(k))
        if changed:
            raise SystemExit("cannot resume %s: %s changed since the run stopped; start a new run"
                             % (rd, ", ".join(changed)))
    done_briefs = {b["source"]: b for b in _jsonl(rd / "briefs.jsonl")} if resume else {}
    done_checks = {r["key"]: r for r in _jsonl(rd / "quote_checks.jsonl")} if resume else {}

    # THE STAGE CAP (stage_cap.py): refuse to start if the sources still to be
    # read are estimated to cost more than is left today or on the issue.
    import stage_cap
    stage_cap.guard("advocate", args.slug,
                    sum(1 for s in srcs if s["id"] not in done_briefs and would_call(s, routed)))
    if not resume:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rd, n = runs_dir(args.slug) / stamp, 1
        while rd.exists():                          # two runs in one second: never one ID
            n += 1
            rd = runs_dir(args.slug) / ("%s-%d" % (stamp, n))
        rd.mkdir(parents=True, exist_ok=False)
        (rd / "inputs.json").write_text(json.dumps(inputs, indent=1, ensure_ascii=False) + "\n",
                                        encoding="utf-8")
    _state(rd, status="running", resumed=bool(resume))
    print("  run         %s%s" % (rd.relative_to(ROOT), " (resumed: %d brief(s), %d quotation check(s) "
                                  "saved)" % (len(done_briefs), len(done_checks)) if resume else ""))

    # WHAT REACHED NO SOURCE (GAP-020): every sentence with no binding to a
    # source, reported and saved with the run, never dropped silently.
    held_ids = {s["id"] for s in srcs}
    (rd / "routing.json").write_text(json.dumps({
        "routed": {k: v for k, v in sorted(routed.items()) if k in held_ids},
        "bound_to_sources_not_in_this_run": sorted(k for k in routed if k not in held_ids),
        "unrouted": unrouted}, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print("  routing     %d sentence(s) reach a source by their binding; %d reach none "
          "(%d with no binding row, %d whose row rests on no source; %s)"
          % (len({x for v in routed.values() for x in v}), len(unrouted),
             sum(1 for u in unrouted if u["why"] == NO_ROW),
             sum(1 for u in unrouted if u["why"] == NO_SOURCE),
             (rd / "routing.json").relative_to(ROOT)))

    run_id = rd.name
    bp = briefs_path(args.slug, run_id)
    if bp.exists():
        raise SystemExit("refusing to overwrite %s: run %s has already written its briefs"
                         % (bp, run_id))
    qlog = bp.parent / "quote_checks.jsonl"
    briefs = []
    try:
        for s in srcs:
            st = sl.access_of(s).get("state")
            if st == sl.NOT_OPENED:
                print(f"  {s['id']:5} skipped — nobody has opened it; the ledger blocks "
                      f"characterising it at all")
                continue
            if s["id"] in done_briefs:
                briefs.append(done_briefs[s["id"]])
                print(f"  {s['id']:5} saved       {len(done_briefs[s['id']].get('objections') or [])} "
                      f"{done_briefs[s['id']]['mode']} (from the stopped run)")
                continue
            print(f"  {s['id']:5} {st:12} {principal(s)[:58]}")
            b = brief_for(args.slug, s, routed.get(s["id"]) or [])
            if b:
                briefs.append(b)
                if not b.get("failed"):
                    _append(rd / "briefs.jsonl", b)       # saved the moment it is drafted
                k = len(b.get("objections") or [])
                print(f"        -> {k} {b['mode']}")
        # EVERY QUOTATION CHECKED WHEN WRITTEN (GAP-018, 2026-10-20). On WHU-P02 22
        # of 29 were not in their source even in the reading-order text, and none
        # was checked until the ruling model was told otherwise.

        def log(r):
            _append(rd / "quote_checks.jsonl", r)
            _append(qlog, dict(r, day=day, run=run_id))
        checked = check_quotations(args.slug, briefs, held, log=log, done=done_checks)
    except Exception as exc:
        if not is_cap_stop(exc):
            _state(rd, status="failed", reason="%s: %s" % (type(exc).__name__, exc))
            raise
        _state(rd, status="stopped", reason=str(exc))
        print("\n  STOPPED BY A SPEND CAP. Everything drafted or checked so far is saved in")
        print("  %s. Carry on (after 00:00 UTC for the day cap) with:" % rd.relative_to(ROOT))
        print("    source_advocate.py run %s --page %s --resume %s\n" % (args.slug, args.page, rd.name))
        for line in str(exc).splitlines():
            print("  " + line)
        return 3
    bad = sum(1 for r in checked if r["result"] == QUOTE_NOTE)
    print(f"  quotations  {len(checked)} checked against the held text; {bad} still not in it "
          f"after one re-ask (log: {qlog.relative_to(ROOT)}, never committed)")
    # A PARTIAL RUN NEVER OVERWRITES ANOTHER RUN'S BRIEFS.
    #
    # --only is documented as "source ids, for a cheap partial run". It once
    # wrote the day's brief file from the sources it had just run, deleting the
    # briefs for every source it had not; then it merged into the day's file.
    # Now each run writes its own files under its own ID, holding the sources
    # it ran, and every reader reads all runs' files, so nothing is lost.
    briefs = sorted(briefs, key=lambda b: b.get("source") or "")
    bp.write_text(
        json.dumps(briefs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    p = write_template(args.slug, day, briefs, name=run_id)
    _state(rd, status="complete", resumed=bool(resume))
    print()
    print(f"  briefs      {bp.relative_to(ROOT)}")
    print(f"  adjudicate  {p.relative_to(ROOT)}")
    print(f"  {sum(len(b.get('objections') or []) for b in briefs)} item(s) need a "
          f"MERIT and an EFFECT line before this issue can publish.")
    return 0


def cmd_status(args) -> int:
    print()
    for label, st, detail in preflight_rows(args.slug):
        print(f"{ {OK:'  ok ', BAD:' STOP', WARN:' warn'}[st]:>7}  {label:30} {detail}")
    print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="argue the source's case against our page")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("slug")
    r.add_argument("--page", required=True)
    r.add_argument("--only", nargs="*", help="source ids, for a cheap partial run")
    r.add_argument("--day", help="ISO date shown in the adjudication file's heading (default: "
                                 "today, UTC); the files are named by the run ID")
    r.add_argument("--resume", metavar="RUN_DIR",
                   help="carry on a run a spend cap stopped (advocate/runs/<stamp>); refuses if "
                        "any input changed, and never redoes a saved brief or quotation check")
    r.set_defaults(fn=cmd_run)
    s = sub.add_parser("status")
    s.add_argument("slug")
    s.set_defaults(fn=cmd_status)
    a = ap.parse_args()
    # WHOSE BUDGET. Without this the calls below land in the ledger with no
    # issue and outside every per-issue cap; fc.call refuses rather than spend
    # unattributed. See factcheck_draft.call.
    fc.enter_issue(getattr(a, "slug", "") or "")
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
