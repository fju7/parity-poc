#!/usr/bin/env python3
"""
What Holds Up: inherited claims — what a source says versus what we know.

WHY THIS EXISTS
---------------
Issue two published "No randomised trial has tested one of these drugs against
another" four times. The sentence came from NCCN, which says "the CDK4/6
inhibitors have not been directly compared in clinical trials", in a passage
about first-line aromatase-inhibitor combinations.

We verified that. The source advocate asked whether the guideline really says
it; the operator opened the guideline and confirmed the sentence word for word.
Everything about that verification was correct, and it verified a QUOTATION.
The page then printed the claim as its own unqualified statement about the
world, with the guideline's scope removed, and two randomised head-to-head
trials existed.

    Verifying that a source says X is not verifying X.

The same shape produced "MONALEESA-2's p-value is two-sided" and the 0.754
meta-analysis claim. It is the most expensive error class this publication has,
and nothing in the pipeline distinguished the two states, because both look
identical once the sentence is on the page.

THE TWO STATES
--------------
    quoted       We have established that a named source says this. It may be
                 published ONLY as a quotation or an attribution, and the
                 source's scope travels with it.
    established  We have checked the world, not just the source. It may be
                 published as our own assertion.

A `quoted` claim on the page without attribution language is the error, and it
is machine-detectable, which is the whole point: the rule already existed in
prose and did not fire.

WHY THE SCOPE FIELD MATTERS AS MUCH AS THE VERDICT
--------------------------------------------------
The guideline's sentence was true. Ours was false. The difference was entirely
scope: the guideline was talking about a treatment setting, and we generalised
to all settings. So an inherited claim records the source's ACTUAL wording, and
the check compares what we wrote against what they wrote.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CASES = ROOT / "issues"
OK, BAD, WARN = "ok", "BLOCKED", "warn"

# Language that marks a sentence as reporting somebody else's claim rather than
# asserting our own.
ATTRIBUTED = re.compile(
    r"\b(the guideline (?:records?|states?|says?|notes?)|according to|"
    r"as (?:the|its) \w+ (?:records?|states?|puts? it)|"
    r"\w+ (?:records?|states?|reports?|says?|writes?|concludes?) that|"
    r"in (?:their|its) (?:words|account)|they (?:say|state|record)|"
    r"is recorded (?:by|in)|on (?:their|its) account)\b", re.I)

TEMPLATE = {
    "_what_this_is": (
        "Claims this issue takes from a source rather than establishes itself. Each records "
        "the source's ACTUAL wording and scope, so the check can compare what we wrote "
        "against what they wrote. A claim marked `quoted` may appear on the page only as a "
        "quotation or an attribution; a claim marked `established` may be asserted, and the "
        "`how_established` field says what we did beyond reading the source."),
    "_why": (
        "Issue two took 'the CDK4/6 inhibitors have not been directly compared in clinical "
        "trials' from NCCN — a sentence about first-line aromatase-inhibitor combinations — "
        "verified that the guideline says it, then printed it as an unqualified claim about "
        "the world. Two randomised head-to-head trials existed. Verifying that a source says "
        "X is not verifying X."),
    "claims": [
        {"id": "IC-001",
         "we_wrote": "",
         "provenance": "quoted",
         "_provenance_values": ["quoted", "established"],
         "source": "",
         "their_wording": "",
         "their_scope": "the setting, population or line of therapy the source's sentence covers",
         "how_established": "for `established` only: what we checked beyond reading the source",
         "checked_by": "", "checked_on": ""},
    ],
}


# A claim of priority or uniqueness is the shape a source's own boast takes
# when it is printed as ours. "The first individualised cancer vaccine to reach
# Phase 3 in any tumour type" is a sentence a company writes about itself; the
# error is not that it is false but that the page states it in its own voice,
# with nothing recording who said it or what was checked.
# "the only" is deliberately ABSENT. It appeared in the first version and made
# three of four hits on the recall fixture noise -- "the only route to it is a
# clinical trial", "the only survival figure in the programme is descriptive"
# -- both the page's own analysis rather than anybody's boast. Precision is
# worth more than reach in a surfacer a person has to read.
PRIORITY = re.compile(
    r"\b(the first|first[- ]ever|the largest|the longest|"
    r"never before|no other|unprecedented|for the first time)\b", re.I)

_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\u201c\"])")


def unattributed_priority_claims(page_text: str) -> list[str]:
    """Priority claims stated in the page's own voice.

    This is the INHERITED class's surfacer, and it exists because the class had
    a module but no way to fire: preflight_rows needs the issue's
    inherited.json, so on any page without one -- including the recall fixture
    -- the check could not run at all, and fatal_recall.py scored it MISSING.
    A control that cannot be exercised is not a control.

    Deterministic and deliberately narrow. It surfaces the sentence; whether
    the claim is ours to make is decided in inherited.json by a person.
    """
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", page_text))
    out = []
    for sent in _SENTENCE.split(flat):
        if PRIORITY.search(sent) and not ATTRIBUTED.search(sent):
            out.append(" ".join(sent.split()))
    return out


def case_dir(slug: str) -> Path:
    hits = sorted(CASES.glob(f"WHU-*-{slug}"))
    if not hits:
        raise SystemExit(f"no case directory for {slug!r}")
    return hits[0]


def path(slug: str) -> Path:
    return case_dir(slug) / "inherited.json"


def load(slug: str) -> dict | None:
    p = path(slug)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def _real(c: dict) -> bool:
    return bool(str(c.get("we_wrote", "")).strip())


def preflight_rows(slug: str, page_text: str) -> list[tuple[str, str, str]]:
    # Surfaced whether or not inherited.json exists. Until today this check
    # returned early on a missing file and looked at nothing, so a page with no
    # record got a warning about the record rather than a reading of the page.
    priority = unattributed_priority_claims(page_text)
    pri_row = [("priority claims stated as ours", WARN,
                "%d claim(s) of being first, largest or unprecedented, in our own voice "
                "with nothing recording whose claim it is: %s"
                % (len(priority), " || ".join(c[:90] for c in priority[:2])))] if priority else []

    d = load(slug)
    if d is None:
        return pri_row + [("inherited claims recorded", WARN,
                 "no inherited.json — nothing records which claims on this page are "
                 "somebody else's and which are ours. publish.py inherited init %s" % slug)]
    claims = [c for c in d.get("claims", []) if _real(c)]
    if not claims:
        return [("inherited claims recorded", WARN,
                 "inherited.json exists but is still the template")]

    rows = [("inherited claims recorded", OK,
             "%d claim(s), %d quoted and %d established"
             % (len(claims),
                sum(1 for c in claims if c.get("provenance") == "quoted"),
                sum(1 for c in claims if c.get("provenance") == "established")))]

    flat = re.sub(r"\s+", " ", page_text)
    bare = []
    for c in claims:
        if c.get("provenance") != "quoted":
            continue
        frag = re.sub(r"\s+", " ", str(c.get("we_wrote", "")))[:70]
        if not frag or frag not in flat:
            continue
        i = flat.index(frag)
        window = flat[max(0, i - 240): i + len(frag) + 60]
        if not ATTRIBUTED.search(window):
            bare.append("%s: %s" % (c.get("id", "?"), frag))
    rows.extend(pri_row)
    rows.append(("quoted claims are attributed on the page",
                 OK if not bare else BAD,
                 "every claim we took from a source is attributed to it"
                 if not bare else
                 "%d claim(s) verified only as quotations and printed as our own "
                 "assertion. This is the class that published 'no randomised trial "
                 "has compared any of the three': %s"
                 % (len(bare), " || ".join(bare[:3]))))

    noscope = [c.get("id", "?") for c in claims
               if c.get("provenance") == "quoted"
               and not str(c.get("their_scope", "")).strip()]
    rows.append(("inherited scope recorded", OK if not noscope else WARN,
                 "every inherited claim records the scope of the sentence it came from"
                 if not noscope else
                 "%d without the source's scope — the scope is what was dropped when "
                 "NCCN's first-line sentence became our claim about every setting: %s"
                 % (len(noscope), ", ".join(noscope))))

    unestablished = [c.get("id", "?") for c in claims
                     if c.get("provenance") == "established"
                     and not str(c.get("how_established", "")).strip()]
    rows.append(("established claims say how", OK if not unestablished else BAD,
                 "every claim asserted as ours records what we checked"
                 if not unestablished else
                 "%d marked established with nothing recorded beyond reading the "
                 "source, which is what `quoted` means: %s"
                 % (len(unestablished), ", ".join(unestablished))))
    return rows


def cmd_init(args) -> int:
    p = path(args.slug)
    if p.exists() and not args.force:
        print("  %s already exists (--force to overwrite)" % p.relative_to(ROOT))
        return 1
    p.write_text(json.dumps(TEMPLATE, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("  wrote %s" % p.relative_to(ROOT))
    return 0


def cmd_status(args) -> int:
    import html as _h
    page = ROOT / args.page
    text = _h.unescape(re.sub(r"<[^>]+>", " ", page.read_text(encoding="utf-8")))
    print()
    for label, st, detail in preflight_rows(args.slug, text):
        print("%7s  %-42s %s" % ({OK: "  ok ", BAD: " STOP", WARN: " warn"}[st], label, detail))
    print()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="what a source says versus what we know")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init"); i.add_argument("slug")
    i.add_argument("--force", action="store_true"); i.set_defaults(fn=cmd_init)
    s = sub.add_parser("status"); s.add_argument("slug")
    s.add_argument("--page", required=True); s.set_defaults(fn=cmd_status)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
