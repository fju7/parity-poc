#!/usr/bin/env python3
"""
What Holds Up: the source-access ledger.

WHY THIS EXISTS
---------------
On 2026-08-29 a reader found that issue two had criticised the NCCN breast
cancer guideline for a distinction the guideline itself draws, in the same
document, in a section we had never read. Six adverse characterisations of that
document were published by a pipeline in which nothing had opened it.

The information was not missing. It was written down, in prose, in the
`used_for` field of S001 in sources.json:

    "Read directly by a human on 2026-08-28: the licence forbids putting the
     document through an AI tool, so no automated check on this issue has seen
     it."

That is a disclosure. It is not a control. Nothing could act on it, because it
was a sentence rather than a state, and so the piece published six claims about
a document that no check in the pipeline was permitted to read.

The same week, and by the same mechanism, the page called MONALEESA-2's final
overall-survival p-value "two-sided" in five places. Nobody had opened the
paper's statistical section; the characterisation was produced by a model
reasoning about what such a paper probably says, and three separate gate runs
agreed with it, because a checker drawn from the same distribution as the
writer re-derives the writer's guess and reads like corroboration.

THE RULE
--------
The gate already holds that an unrun check is not a pass. This is the same
principle one level down:

    AN UNREAD SOURCE IS NOT A SOURCE THAT AGREES WITH US.

So every source carries a machine-readable access state, and the states that
mean "nobody opened this" block a publish that characterises it.

WHAT THIS DOES NOT DO
---------------------
It does not decide whether a claim is fair. It decides whether anyone was in a
position to know. Those are different questions and only the second one is
mechanical, which is exactly why this file has no model in it.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "issues"

OK, BAD, WARN = "ok", "BLOCKED", "warn"

# ---------------------------------------------------------------------------
# the states
# ---------------------------------------------------------------------------
#
# Ordered by what they license. A claim needs a state at or above its bar.

MACHINE_READ = "machine_read"   # an automated check opened the primary text
HUMAN_READ = "human_read"       # a person opened it; no automated check may
BLOCKED = "blocked"             # we tried and could not open it
NOT_OPENED = "not_opened"       # nobody tried

STATES = (MACHINE_READ, HUMAN_READ, BLOCKED, NOT_OPENED)

# What each state permits, as prose the board prints. The distinction that
# matters is between "somebody read this" and "somebody guessed".
PERMITS = {
    MACHINE_READ: "figures, characterisation, and adverse claims",
    HUMAN_READ: "figures and characterisation; adverse claims need the reader's answer",
    BLOCKED: "figures already extracted; NO new characterisation",
    NOT_OPENED: "nothing. Cite it or open it.",
}

READ_STATES = (MACHINE_READ, HUMAN_READ)


# ---------------------------------------------------------------------------
# adverse and characterising language
# ---------------------------------------------------------------------------
#
# These are recall-oriented, not precise. A false positive costs one line of
# reading on the board. A false negative is how issue two published. The list
# grows when something gets past it; every entry below is here because
# something did.

CHARACTERISING = re.compile(
    r"\b("
    r"states?|said|says|records?|reports?|describes?|defines?|grades?|assigns?|"
    r"lists?|notes?|acknowledges?|concedes?|claims?|asserts?|argues?|maintains?|"
    r"treats? \w+ as|calls?|labels?|characterises?|characterizes?"
    r")\b", re.I)

ADVERSE = re.compile(
    r"\b("
    r"fail(?:s|ed)? to|does not (?:say|state|report|address|establish|mention|disclose)|"
    r"did not (?:say|state|report|address|establish|mention|disclose)|"
    r"never (?:says|states|mentions|reports|discloses)|omits?|omitted|omission|"
    r"quietly|buried|misleading|misleads?|selective(?:ly)?|"
    r"unsupported|not supported|thin|overstates?|overstated|understates?|"
    r"without (?:saying|disclosing|acknowledging)|"
    r"we could not (?:establish|determine|verify|open)|"
    r"invites? the reader|performs? one on the reader|"
    r"is read as|read as a ranking|not a verdict|is not one"
    r")\b", re.I)

SENTENCE = re.compile(r"(?<=[.!?])\s+")


def plain(html_text: str) -> str:
    """Tag-stripped, entity-decoded page text.

    Entities matter: the page writes &ldquo; and &mdash;, and a sentence
    splitter that sees them as words splits in the wrong places, which silently
    shortens the sentences this file matches against.
    """
    import html as _h
    return _h.unescape(re.sub(r"<[^>]+>", " ", html_text))


def sentences(text: str) -> list[str]:
    return [s.strip() for s in SENTENCE.split(text) if s.strip()]


def identifiers(src: dict) -> list[str]:
    """Tokens that mean 'this sentence is about this source'.

    Taken from the title rather than guessed: trial names, journal names and
    organisations are what a page actually says when it refers to a study.
    """
    # An explicit alias list is authoritative. Titles are inferred from, and a
    # title like "KEYNOTE-942: a randomised, phase 2b study - The Lancet, 2024"
    # yields the trial name, which three separate sources on this page share.
    # Inference is a fallback for sources nobody has named; where somebody has
    # said how a document is referred to, that is the answer.
    explicit = [t for t in (src.get("also_called") or []) if str(t).strip()]
    if explicit:
        return sorted(set(explicit), key=len, reverse=True)

    out: list[str] = []
    title = src.get("title", "")
    # Trial and programme names: runs of capitals, often hyphenated with a digit.
    out += re.findall(r"\b[A-Z][A-Z0-9]{2,}(?:-[A-Z0-9]+)*\b", title)
    # Named organisations and journals the page refers to by name.
    for token in ("NCCN", "N Engl J Med", "NEJM", "J Clin Oncol", "Ann Oncol",
                  "Annals of Oncology", "Scientific Reports", "Cancers"):
        if token.lower() in title.lower():
            out.append(token)
    # A page refers to its sources the way prose does — "the guideline", "the
    # label", "the paper" — and almost never by the title in sources.json. The
    # first run of this audit found nothing adverse about the NCCN guideline
    # because not one of the offending sentences contained the string "NCCN".
    # So the role-nouns a page actually uses have to be declared per source, and
    # an undeclared reference is invisible here. That is the known limit of this
    # check and the reason `also_called` is not optional in practice.
    # (reached only when no explicit alias was given)
    # Deduplicate, longest first so "MONALEESA-2" beats "MONALEESA".
    seen, uniq = set(), []
    for t in sorted(set(out), key=len, reverse=True):
        if t.lower() not in seen:
            seen.add(t.lower())
            uniq.append(t)
    return uniq


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob(f"WHU-*-{slug}"))
    if not hits:
        raise SystemExit(f"no case directory for {slug!r} under {CASES}")
    return hits[0]


def sources_path(slug: str) -> Path:
    return case_dir(slug) / "sources.json"


def load(slug: str) -> dict:
    return json.loads(sources_path(slug).read_text(encoding="utf-8"))


def save(slug: str, doc: dict) -> None:
    sources_path(slug).write_text(
        json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def access_of(src: dict) -> dict:
    a = src.get("access")
    if not isinstance(a, dict):
        return {"state": NOT_OPENED}
    if a.get("state") not in STATES:
        return {"state": NOT_OPENED, "malformed": a.get("state")}
    return a


# ---------------------------------------------------------------------------
# the audit
# ---------------------------------------------------------------------------

def audit(slug: str, page_text: str,
          baseline_text: str | None = None) -> list[tuple[str, str, str]]:
    """Rows for the board: (label, status, detail).

    `baseline_text` is the version readers can already see. When it is given,
    only sentences that are NEW or CHANGED since then are held against the
    ledger.

    That scoping is deliberate and it is not a loophole. This gate exists to
    stop an unverified claim from being published; on a correction to a live
    page, holding the whole backlog hostage would block a correction behind
    work unrelated to it, and blocking a correction is worse than the error it
    corrects. New claims get the full bar. Old ones are reported as a backlog
    to work through, which is what they are.
    """
    doc = load(slug)
    srcs = doc.get("sources", [])
    rows: list[tuple[str, str, str]] = []

    missing = [s["id"] for s in srcs if access_of(s).get("state") == NOT_OPENED]
    rows.append((
        "source ledger complete",
        OK if not missing else BAD,
        f"{len(srcs)} source(s), each with an access record"
        if not missing else
        f"{len(missing)} source(s) with no record that anyone opened them: "
        + ", ".join(missing)))

    # A source this audit cannot recognise on the page is a source this audit
    # does not check -- and a check that matches nothing looks exactly like a
    # check that found nothing. That is the failure this whole file exists to
    # prevent, and on 2026-08-29 this file committed it: run against issue one,
    # every row came back clean because issue one's sources.json carries no
    # titles, so identifiers() returned an empty list for all ten sources and
    # not one sentence was ever compared. It reported "no claim says what an
    # unopened source says" about a page it had not read a word of.
    mute = [s["id"] for s in srcs if not identifiers(s)]
    rows.append((
        "sources are identifiable on the page",
        OK if not mute else BAD,
        "every source has a name or an alias this audit can find in the prose"
        if not mute else
        f"{len(mute)} source(s) with nothing to match on — no title, no "
        f"also_called. Every check below silently skips them and reports clean: "
        + ", ".join(mute)))

    # A row in sources.json is not thereby a source. Issue one's was built by
    # sweeping the page's links, which collected the font CDN and the
    # stylesheet host; they are still S001, S002 and S003, typed "press", with
    # an empty used_for. The ledger will faithfully record an access state for
    # a webfont, because it checks whether anyone opened a thing, not whether
    # the thing is a source.
    ASSET_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com", "cdnjs.",
                   "cdn.jsdelivr.net", "code.jquery.com")
    junk = [s["id"] for s in srcs
            if any(h in (s.get("url") or "") for h in ASSET_HOSTS)
            or not (s.get("used_for") or "").strip()]
    rows.append((
        "every source is a source",
        OK if not junk else BAD,
        "no asset hosts or empty entries in the source list"
        if not junk else
        f"{len(junk)} entr(y/ies) that cite nothing or point at an asset host — "
        f"build the list from the page's own sources section, not from a link "
        f"sweep: " + ", ".join(junk)))

    # Sources that descend from one upstream document are one source.
    #
    # Issue two said no randomised head-to-head trial existed, and the COVERAGE
    # role found agreement everywhere. Every agreeing document was downstream of
    # the same claim: NCCN summaries repeating the guideline, and P-VERIFY,
    # which the page itself quotes as describing its purpose as working "in the
    # absence of randomised trials that directly compare the three" -- and the
    # page cited that as confirmation. Counting agreeing documents is not
    # counting evidence. There is no way for a machine to detect an echo it has
    # not been told about, so this reports the derivation structure the issue
    # has declared and says plainly how much of it is independent.
    derived = [(s["id"], s.get("derives_from"))
               for s in srcs if s.get("derives_from")]
    independent = len(srcs) - len(derived)
    if derived:
        rows.append((
            "independent sources", WARN,
            "%d of %d source(s) declare an upstream: %s. Agreement between these "
            "is an echo, not corroboration."
            % (len(derived), len(srcs),
               "; ".join("%s <- %s" % (i, d if isinstance(d, str) else ", ".join(d))
                         for i, d in derived[:4]))))
    else:
        rows.append((
            "independent sources", OK,
            "no source declares an upstream. That is either true or unexamined — "
            "`derives_from` is only as good as the reading behind it."))

    read_ids = {s["id"] for s in srcs if access_of(s).get("state") in READ_STATES}

    sents = sentences(page_text)
    old_sents = set(sentences(baseline_text)) if baseline_text is not None else None

    unread_chars: list[str] = []
    backlog: list[str] = []
    adverse_unanswered: list[str] = []

    for s in srcs:
        state = access_of(s).get("state")
        ids = identifiers(s)
        if not ids:
            continue
        # A claim ABOUT one source can be sourced TO another -- the page takes
        # MONALEESA-7's test direction from the ASCO abstract of the same
        # analysis, and says so in the sentence. Declared support counts.
        supported = set(s.get("characterisation_supported_by") or []) & read_ids
        for sent in sents:
            if not any(i.lower() in sent.lower() for i in ids):
                continue
            is_new = old_sents is None or sent not in old_sents
            if state in (NOT_OPENED, BLOCKED) and CHARACTERISING.search(sent):
                if supported:
                    continue
                (unread_chars if is_new else backlog).append(
                    f"{s['id']}: {sent[:110]}")
            elif state == HUMAN_READ and ADVERSE.search(sent) and is_new:
                adverse_unanswered.append(f"{s['id']}: {sent[:110]}")

    rows.append((
        "new claims about unread sources",
        OK if not unread_chars else BAD,
        "no claim added since the live version says what an unopened source says"
        if not unread_chars else
        f"{len(unread_chars)} NEW sentence(s) say what an unopened source says. "
        "This is the class that published 'two-sided' about a paywalled "
        "statistical section: " + " | ".join(unread_chars[:4])))

    if backlog:
        rows.append((
            "unread-source backlog", WARN,
            f"{len(backlog)} sentence(s) already live say what an unopened source "
            f"says. Not blocking this correction, and not fine either: "
            + " | ".join(backlog[:3])))

    rows.append((
        "adverse claims needing the human reader",
        OK if not adverse_unanswered else WARN,
        "none" if not adverse_unanswered else
        f"{len(adverse_unanswered)} adverse sentence(s) about a source only a "
        "person has read — the advocate cannot check these, so the reader must: "
        + " | ".join(adverse_unanswered[:3])))

    return rows


def brief(slug: str) -> str:
    doc = load(slug)
    out = [f"source ledger — {slug}", ""]
    for s in doc.get("sources", []):
        a = access_of(s)
        st = a.get("state")
        line = f"  {s['id']:5} {st:13} {s.get('title','')[:64]}"
        out.append(line)
        who = a.get("by") or "?"
        when = a.get("on") or "?"
        if st in READ_STATES:
            out.append(f"        read by {who} on {when}")
            if a.get("not_read"):
                out.append(f"        NOT read: {'; '.join(a['not_read'])}")
        elif st == BLOCKED:
            out.append(f"        blocked by {a.get('blocked_by') or 'unstated'}"
                       f" — tried {when}")
        else:
            out.append("        nobody has opened this")
        out.append(f"        permits: {PERMITS[st]}")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def cmd_status(args) -> int:
    print()
    print(brief(args.slug))
    print()
    return 0


def cmd_set(args) -> int:
    doc = load(args.slug)
    for s in doc.get("sources", []):
        if s["id"] != args.id:
            continue
        a = {"state": args.state,
             "by": args.by,
             "on": args.on or date.today().isoformat()}
        if args.sections:
            a["sections"] = args.sections
        if args.not_read:
            a["not_read"] = args.not_read
        if args.blocked_by:
            a["blocked_by"] = args.blocked_by
        if args.note:
            a["note"] = args.note
        s["access"] = a
        save(args.slug, doc)
        print(f"  {args.id}: {args.state} (by {a['by']} on {a['on']})")
        print(f"  permits: {PERMITS[args.state]}")
        return 0
    print(f"no source {args.id!r} in {sources_path(args.slug)}", file=sys.stderr)
    return 1


def cmd_audit(args) -> int:
    page = ROOT / args.page
    text = plain(page.read_text(encoding="utf-8"))
    rows = audit(args.slug, text)
    print()
    for label, st, detail in rows:
        mark = {OK: "  ok ", BAD: " STOP", WARN: " warn"}[st]
        print(f"{mark:>7}  {label:38} {detail}")
    print()
    return 0 if not any(st == BAD for _l, st, _d in rows) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[2])
    sub = ap.add_subparsers(dest="cmd", required=True)

    st = sub.add_parser("status", help="what has been opened, and by whom")
    st.add_argument("slug")
    st.set_defaults(fn=cmd_status)

    se = sub.add_parser("set", help="record that a source was opened, or could not be")
    se.add_argument("slug")
    se.add_argument("id")
    se.add_argument("--state", choices=STATES, required=True)
    se.add_argument("--by", required=True, help="who opened it — a name, not a role")
    se.add_argument("--on", help="ISO date; defaults to today")
    se.add_argument("--sections", nargs="*", help="what parts were read")
    se.add_argument("--not-read", nargs="*", dest="not_read",
                    help="parts NOT read, named so the gap is a fact and not a silence")
    se.add_argument("--blocked-by", choices=("paywall", "licence", "captcha", "dead-link"))
    se.add_argument("--note")
    se.set_defaults(fn=cmd_set)

    au = sub.add_parser("audit", help="check the page's claims against the ledger")
    au.add_argument("slug")
    au.add_argument("--page", required=True, help="repo-relative path to the page")
    au.set_defaults(fn=cmd_audit)

    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
