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
    EFFECT  changes / narrows / none  -- what it does to the conclusion
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
from datetime import date
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
  "claim_quoted":  "the exact sentence or phrase from the page you object to",
  "objection":     "your objection, in one sentence",
  "source_says":   "what your document actually says, QUOTED, with a locator
                    (section, table, page). Empty string if you could not find
                    anything.",
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
   Other checks handle figures; you are here for what the page left out.
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


def mentions(page_text: str, src: dict) -> list[str]:
    ids = sl.identifiers(src)
    if not ids:
        return []
    out = []
    for s in sl.sentences(page_text):
        if any(i.lower() in s.lower() for i in ids):
            out.append(s)
    return out


def brief_for(slug: str, src: dict, page_text: str) -> dict | None:
    acc = sl.access_of(src)
    state = acc.get("state")
    sents = mentions(page_text, src)
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

def adjudication_path(slug: str, day: str) -> Path:
    d = sl.case_dir(slug) / "advocate"
    d.mkdir(exist_ok=True)
    return d / f"{day}-adjudication.md"


def briefs_path(slug: str, day: str) -> Path:
    d = sl.case_dir(slug) / "advocate"
    d.mkdir(exist_ok=True)
    return d / f"{day}-briefs.json"


VERDICT = re.compile(r"^\s*MERIT:\s*(yes|partly|no)\b", re.I | re.M)
EFFECT = re.compile(r"^\s*EFFECT:\s*(changes|narrows|none)\b", re.I | re.M)

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


def _closed(chunk: str, mode: str) -> bool:
    if mode == "questions":
        return bool(ANSWERED_BY.search(chunk) and ANSWER.search(chunk)
                    and LOCATOR.search(chunk) and EFFECT.search(chunk))
    return bool(VERDICT.search(chunk) and EFFECT.search(chunk))


def write_template(slug: str, day: str, briefs: list[dict]) -> Path:
    p = adjudication_path(slug, day)
    lines = [f"# {slug} — source advocate, {day}", "",
             "One section per item. Each must be closed before this issue can",
             "publish. An open item blocks; an item closed \"no merit\", with the",
             "reason on the record, does not.", "",
             "For an OBJECTION, from a source a machine could read:", "",
             "    MERIT:  yes | partly | no   — and why, citing what you read",
             "    EFFECT: changes | narrows | none",
             "    DID:    what actually changed, or nothing and why", "",
             "For a QUESTION, from a source only a person is permitted to read:", "",
             "    ANSWERED BY: a person's name. Not \"the team\", not a role.",
             "    ON:          the date they opened the document",
             "    ANSWER:      what it says, quoted",
             "    LOCATOR:     section, table or page",
             "    EFFECT:      changes | narrows | none",
             "    DID:         what changed", "",
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
                lines += [f"**We say.** {o.get('claim_quoted','')}", "",
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


def open_items(slug: str) -> tuple[list[str], list[str]]:
    """(open objections, open questions for a human). Both block."""
    d = sl.case_dir(slug) / "advocate"
    if not d.exists():
        return [], []
    modes = _modes(slug)
    objs, qs = [], []
    for f in sorted(d.glob("*-adjudication.md")):
        if "TEST" in f.name:
            continue
        text = f.read_text(encoding="utf-8")
        for chunk in re.split(r"(?=^### )", text, flags=re.M)[1:]:
            head = chunk.splitlines()[0][4:].strip()
            sid = head.split("-")[0]
            mode = modes.get(sid, "objections")
            if _closed(chunk, mode):
                continue
            (qs if mode == "questions" else objs).append(f"{f.name}: {head}")
    return objs, qs


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
             f"{len(briefs)} run(s), latest {briefs[-1].name[:10]}")]
    rows.append(("advocate objections closed", OK if not objs else BAD,
                 "every objection carries a written verdict and effect"
                 if not objs else
                 f"{len(objs)} with no MERIT/EFFECT recorded: " + "; ".join(objs[:3])))
    rows.append(("questions answered by a reader", OK if not qs else BAD,
                 "every question about a source only a person can read has been "
                 "answered, by name, from the document"
                 if not qs else
                 f"{len(qs)} question(s) about a licence- or paywall-restricted source "
                 f"that no person has answered. Nothing here can answer them: "
                 + "; ".join(qs[:3])))
    return rows


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
    srcs = doc.get("sources", [])
    if args.only:
        srcs = [s for s in srcs if s["id"] in set(args.only)]
    day = args.day or date.today().isoformat()

    briefs = []
    for s in srcs:
        st = sl.access_of(s).get("state")
        if st == sl.NOT_OPENED:
            print(f"  {s['id']:5} skipped — nobody has opened it; the ledger blocks "
                  f"characterising it at all")
            continue
        print(f"  {s['id']:5} {st:12} {principal(s)[:58]}")
        b = brief_for(args.slug, s, text)
        if b:
            briefs.append(b)
            k = len(b.get("objections") or [])
            print(f"        -> {k} {b['mode']}")
    # A PARTIAL RUN MERGES. It used to overwrite.
    #
    # --only is documented as "source ids, for a cheap partial run", and it
    # wrote the day's brief file from the sources it had just run -- deleting
    # the briefs for every source it had not. Running the advocate over eleven
    # sources three at a time, which is the only way to run it where each call
    # is time-limited, would have left the briefs for the last three and a file
    # claiming that was the whole review. The adjudication template is built
    # from that file, so the objections would have gone with it.
    bp = briefs_path(args.slug, day)
    keep = []
    if bp.exists():
        try:
            ran = {b.get("source") for b in briefs}
            keep = [b for b in json.loads(bp.read_text(encoding="utf-8"))
                    if b.get("source") not in ran]
        except Exception:
            keep = []
    briefs = sorted(keep + briefs, key=lambda b: b.get("source") or "")
    bp.write_text(
        json.dumps(briefs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    p = write_template(args.slug, day, briefs)
    print()
    print(f"  briefs      {briefs_path(args.slug, day).relative_to(ROOT)}")
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
    r.add_argument("--day", help="ISO date for the output files")
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
