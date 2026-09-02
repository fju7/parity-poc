#!/usr/bin/env python3
"""The binding store — which words in which document support this sentence.

WHY
---
Every control in this repository is about a DOCUMENT: is it held, what kind is
it, was it read, does the ledger overstate it. None is about a SENTENCE. So
nothing anywhere records the only thing that would make verification complete,
deterministic, cheap and repeatable:

    this sentence rests on this source, at this locator, supported by
    these exact words.

Spec: docs/whatholdsup-claim-bindings-spec.md. This module is step 2 of its
build order — the store, and B1, the check that every empirical sentence has a
row. The span checks (B2, B3, B5, B6) come next and all of them need this.

WHAT B1 ALONE IS WORTH
----------------------
On 2026-09-01 the published page carried eight figures from a reconstructed
patient-data comparison that had its own entry in the visible source list and
NO entry in sources.json. No id, no access record, nothing in the library, no
row in the twenty-five sources we publish as our count. It was invisible to the
ledger, the quotation check, the gap list and preflight, because every one of
those starts from the source list and it was not in the source list.

B1 starts from the PAGE. A sentence carrying a figure, a trial name, a registry
id or a quotation, with no binding row, is a defect — whether or not anybody
remembered to write the source down.

R1 FROM THE SPEC, RESTATED HERE BECAUSE IT GOVERNS THIS FILE
-----------------------------------------------------------
This layer may assert only the presence or absence of a span. It may never
assert that a sentence is true. It reports what it can observe and hands the
resolution to a person: a block is a question, not a verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import source_store as store      # noqa: E402
import source_ledger as ledger    # noqa: E402

OK, BAD, WARN = "ok", "BLOCKED", "warn"

BUCKETS = ("deterministic", "context", "judgement", "figure")
QUESTIONS = ("locatable", "faithful", "warranted")


# ---------------------------------------------------------------------------
# which sentences must be bound
# ---------------------------------------------------------------------------

FIGURE = re.compile(r"\b\d+\.\d+\b|\b\d{1,3}(?:,\d{3})+\b|\b\d+(?:\.\d+)?\s?%")
NCT = re.compile(r"\bNCT\d{8}\b")
DOI = re.compile(r"\b10\.\d{4,9}/\S+")
QUOTED = re.compile(r"[“\"][^”\"]{25,}[”\"]")


def trial_names(srcs: list[dict]) -> set[str]:
    names = set()
    for s in srcs:
        for n in (s.get("also_called") or []):
            if len(n) > 3:
                names.add(n)
    return names


def is_empirical(sent: str, names: set[str]) -> tuple[bool, str]:
    """(must_be_bound, why). The why is printed, so a person can disagree with
    the classifier rather than guess at it."""
    if NCT.search(sent):
        return True, "registry identifier"
    if DOI.search(sent):
        return True, "DOI"
    if QUOTED.search(sent):
        return True, "quoted passage"
    if FIGURE.search(sent):
        return True, "figure"
    hit = next((n for n in names if re.search(r"\b%s\b" % re.escape(n), sent)), None)
    if hit:
        return True, "names %s" % hit
    return False, ""


# Page furniture is not a claim.
#
# The pages carry no <main> or <article>, so sentence extraction was taking the
# whole document — and the first "empirical sentence" needing a binding was the
# site navigation: "The Category Difference — What Holds Up What Holds Up What
# this is Issue one Issue two Who pays for this". It contains digits and proper
# nouns, so it looked empirical to a check counting digits and proper nouns.
#
# Every denominator this file has reported was inflated by it. Removing the nav,
# header and footer is not cosmetic: it changes what "141 sentences rest on
# nothing" means, and a number that is wrong in our favour is worse than one
# that is merely large.
FURNITURE = re.compile(r"<(nav|header|footer|aside)\b[^>]*>.*?</\1>",
                       re.S | re.I)


def page_sentences(slug: str) -> list[str]:
    html = ledger.page_text(slug) if hasattr(ledger, "page_text") else None
    if html is None:
        html = _page_html(slug)
    html = FURNITURE.sub(" ", html)
    return [" ".join(s.split()) for s in ledger.sentences(ledger.plain(html))]


def _page_html(slug: str) -> str:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "pub", str(Path(__file__).resolve().parent / "publish.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    cfg = m.ISSUES[slug]
    return (m.ROOT / cfg["page"]).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# the store
# ---------------------------------------------------------------------------

def fingerprint(sent: str) -> str:
    return hashlib.sha256(" ".join(sent.split()).encode("utf-8")).hexdigest()[:16]


def path(slug: str) -> Path:
    return store.case_dir(slug) / "bindings.json"


def load(slug: str) -> dict:
    p = path(slug)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return {
        "_what_this_is":
            "One row per empirical sentence on the page: the source it rests "
            "on, the exact words in that source that support it, and who "
            "signed for each of the three questions. Spec: "
            "docs/whatholdsup-claim-bindings-spec.md.",
        "_r1":
            "This file records the presence or absence of a span. It does not "
            "record that a sentence is true. A row with every verdict signed "
            "means the sentence is WARRANTED by named evidence and named "
            "signers -- which is not the same claim and must never be printed "
            "as though it were.",
        "bindings": {},
    }


def save(slug: str, doc: dict) -> None:
    path(slug).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")


def blank_row(sent: str, why: str) -> dict:
    return {
        "sentence": sent[:600],
        "sentence_sha": fingerprint(sent),
        "why_empirical": why,
        "bucket": None,          # declared by whoever writes the sentence
        "source_id": None,
        "document_sha": None,
        "locator_type": None,    # prose | table | field | figure | none
        "locator": None,
        "span": None,
        "envelope": None,
        "scope_words": [],
        "falsifier": None,       # what would show this sentence wrong
        "verdicts": {q: None for q in QUESTIONS},
        "first_seen": date.today().isoformat(),
    }


def scan(slug: str) -> tuple[dict, list[str], list[str]]:
    """(doc, unbound, stale). Adds a blank row for every empirical sentence
    that has none; never deletes, because a sentence that has left the page is
    evidence about a correction and belongs in the record."""
    doc = load(slug)
    rows = doc.setdefault("bindings", {})
    names = trial_names(store.sources(slug))
    live, unbound = set(), []
    for sent in page_sentences(slug):
        must, why = is_empirical(sent, names)
        if not must:
            continue
        sha = fingerprint(sent)
        live.add(sha)
        if sha not in rows:
            rows[sha] = blank_row(sent, why)
        rows[sha]["on_page"] = True
        if not rows[sha].get("span"):
            unbound.append(sha)
    stale = []
    for sha, row in rows.items():
        if sha not in live:
            row["on_page"] = False
            row["left_page"] = row.get("left_page") or date.today().isoformat()
            stale.append(sha)
    save(slug, doc)
    return doc, unbound, stale


# ---------------------------------------------------------------------------
# running the checks FROM the binding, never from a caller's choice
# ---------------------------------------------------------------------------

def run_checks(slug: str, *, only: str = "") -> dict:
    """Run every span check against the source THE ROW NAMES.

    WHY THIS IS THE ONLY SANCTIONED WAY TO CALL THEM.

    On 2026-09-01 B12 was run against a document that happened to be in the
    library rather than the one the sentence cites, and reported two correct
    sentences on a live page as errors: "we print 0.510, the source says 0.51".
    The page cites the Journal of Clinical Oncology five-year paper, which
    prints 0.510. What prints 0.51 is a company press release the page does not
    cite. The check was right about the document it was given and the document
    it was given was the wrong one.

    Every span check takes a source id. Whoever supplies it can be wrong, and
    was. The binding row is the answer to "which document does this sentence
    rest on", recorded once, reviewable, and not re-decided at each call site.

    A caller reaching past this into b2_present or b12_precision directly is
    asserting provenance it has to be able to defend. The canary does, because
    it asks about a document rather than about a sentence. Preflight does not,
    and uses this.
    """
    import spancheck as SC
    doc = load(slug)
    rows = doc.get("bindings") or {}
    tally = {"checked": 0, "flags": 0, "undetermined": 0}
    for sha, row in rows.items():
        if only and sha != only:
            continue
        if not row.get("on_page") or not row.get("span") or not row.get("source_id"):
            continue
        sid, span, sent = row["source_id"], row["span"], row["sentence"]
        found = []
        tally["checked"] += 1

        present, why = SC.b2_present(span, slug, sid)
        if present is SC.UNDETERMINED:
            tally["undetermined"] += 1
            found.append({"check": "B2", "verdict": "undetermined", "why": why})
        elif present is not True:
            other, why2 = SC.b3_elsewhere(span, slug, sid)
            found.append({"check": "B2/B3", "verdict": "absent",
                          "why": "%s; %s" % (why, why2)})
        else:
            ok5, why5 = SC.b5_complete(span, slug, sid)
            if not ok5:
                found.append({"check": "B5", "verdict": "truncated", "why": why5})
            # A SCOPE WORD MAY BE DISPOSED OF, BY A PERSON, IN THE ROW.
            #
            # "Of the study it is actually announcing it says only that the
            # endpoints were met ... No hazard ratio, no interval, no p-value,
            # no percentage" is an absence claim about a WHOLE DOCUMENT. No span
            # can carry "only", so B6 is right that nothing maps and will be
            # right forever. Left alone it becomes the flag the operator learns
            # to scroll past, which is how a check stops working.
            #
            # So the row may carry a disposition: the word, why it is not a
            # claim the span is meant to bear, WHAT WOULD SHOW IT WRONG, and who
            # signed. Same discipline as b13's declared exclusions -- a
            # signature, not a filter. A disposition with no falsifier or no
            # signer does not count, and one whose word is no longer in the
            # sentence is itself a flag.
            disposed = {}
            for d in (row.get("scope_words") or []):
                if isinstance(d, dict) and d.get("word") and \
                        (d.get("falsifier") or "").strip() and \
                        (d.get("by") or "").strip():
                    disposed[d["word"]] = d
            for w, why6 in SC.b6_scope(sent, span):
                if w in disposed:
                    continue
                found.append({"check": "B6", "verdict": "unmapped scope word",
                              "why": "%s — %s" % (w, why6)})
            live_words = {w for w, _ in SC.b6_scope(sent, "")}
            for w, d in disposed.items():
                if w not in live_words:
                    found.append({
                        "check": "B6", "verdict": "stale disposition",
                        "why": "%r is disposed of in this row and is no longer a "
                               "scope word in the sentence; a disposition that "
                               "outlives its word is a filter" % w})
            import autobind as AB
            for a in AB.anchors_of(sent):
                ok12, why12 = SC.b12_precision(a, slug, sid)
                if not ok12:
                    found.append({"check": "B12", "verdict": "added precision",
                                  "why": why12})
        row["check_flags"] = found
        row["checked_on"] = date.today().isoformat()
        tally["flags"] += len(found)
    save(slug, doc)
    return tally


# ---------------------------------------------------------------------------
# B1
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# THE WRITING RULE
# ---------------------------------------------------------------------------
#
# Adopted 2026-09-02, by the editor, after two page-gate runs produced eleven
# findings that were right:
#
#   1. NO FACTUAL STATEMENT THAT IS NOT BASED ON A DOCUMENT WE HAVE AND HAVE
#      FULLY READ.
#   2. EVERY INFERENCE FLAGGED, WITH THE LOGIC AND THE FACTS THAT SUPPORT IT.
#
# Ten of the eleven would have been prevented by those two sentences. The
# eleventh -- a subheading contradicting the paragraph beneath it -- is a
# relation between two things we wrote, which no sourcing rule can reach; that
# is B16's contradiction question.
#
# WHY THIS IS IN CODE AND NOT IN A DOCUMENT
#
# Both rules were ALREADY in this repository. `bucket` has been a field on every
# binding row since the row was designed, and it is null on all eighty sentences
# of issue one. "Empirical sentences bound" has been a WARN reporting 20 of 80.
# The spec's deletion rule, the "write the correction from the source record"
# rule, and undefined_states were the same: written down, gating nothing, and
# each one was followed by the error it described.
#
# A rule that does not block is a rule that will be broken by whoever is tired.
#
# THERE IS NO GRANDFATHERING, AND THERE WAS FOR ABOUT AN HOUR
#
# The first version of this exempted every sentence already on the page, on the
# reasoning that blocking 318 sentences would stop three issues and teach the
# operator to waive the check. That reasoning is the reasoning behind every
# waiver ever granted, and the editor rejected it in one line: given the state
# of the drafting, every sentence in all three articles should be revalidated
# or rewritten.
#
# He is right, and the exemption had already proved him right before he said
# it. Drawn the obvious way -- "everything unbound today" -- it excused a
# sentence written that same afternoon, one of two the gate had never examined.
# Redrawn from git, it still excused sixty-four sentences whose only claim to
# exemption was that nobody had checked them yet. A rule whose scope is "not
# the things we already did" is not a rule.
#
# So the two rules apply to every empirical sentence on every page. The count
# of sentences that fail them is the real backlog, printed rather than
# absorbed, and the only way it falls is by binding or removing a sentence.

RULE_ADOPTED = "2026-09-02"


def bind_field(slug: str, sha: str, sid: str, path: str) -> tuple[bool, str]:
    """Bind a sentence to a STRUCTURED FIELD in a held registry record.

    WHY THIS IS NOT THE PROSE PATH
    ------------------------------
    modelbind rejects a field binding, and it is right to. Its guard asks
    whether the span shares subject matter with the sentence, because a span
    that shares only digits is a coincidence of numbers. But a registry field
    reads `"hasResults":false`, and the sentence reads "the registry carries no
    posted results" -- zero words in common, and the binding is nonetheless
    exactly right. Loosening the prose guard to let this through would loosen
    it for everything.

    So relevance is established differently here, and the record says which:
    the caller names the FIELD PATH, this walks the held JSON to it, and the
    span is that field as the document actually writes it. A path that does not
    resolve is refused. The claim being made is still only R1's -- this field,
    with this value, is in this document -- and not that the sentence is true.
    """
    text = _held_text(slug, sid)
    if text is None:
        return False, "%s is not in the library" % sid
    try:
        data = json.loads(text)
    except ValueError:
        return False, "%s is not JSON, so it has no fields to bind to" % sid
    node, walked = data, []
    for key in path.split("."):
        walked.append(key)
        if isinstance(node, list):
            try:
                node = node[int(key)]
            except (ValueError, IndexError):
                return False, "%s does not resolve in %s" % (".".join(walked), sid)
        elif isinstance(node, dict) and key in node:
            node = node[key]
        else:
            return False, "%s does not resolve in %s" % (".".join(walked), sid)
    span = "%s:%s" % (json.dumps(path.split(".")[-1]), json.dumps(node))
    if span.replace(" ", "") not in text.replace(" ", ""):
        return False, ("%s resolves to %r but that is not how %s writes it"
                       % (path, node, sid))
    doc = load(slug)
    row = (doc.get("bindings") or {}).get(sha)
    if row is None:
        return False, "no binding row %s" % sha[:8]
    row.update(source_id=sid, span=span, locator="$." + path,
               locator_type="field", envelope=None,
               document_sha=(store.held(slug).get(sid) or {}).get("sha256"),
               proposed_by="bind_field", confirmed=False,
               proposed_on=date.today().isoformat(),
               why_bound="the field %s in %s carries this value; relevance is "
                         "the named field path, not prose overlap" % (path, sid))
    save(slug, doc)
    return True, "bound to $.%s in %s" % (path, sid)


def _held_text(slug: str, sid: str):
    import spancheck as SC
    return SC._text(slug, sid)


def _as_numbers(figs) -> set[float]:
    """Figures compared as NUMBERS, because 1.0 and 1 are the same number.

    The coverage check first compared figure strings, and reported that "an HR
    of 1.0" was unsupported by a source saying "if HR = 1". Same number, two
    spellings, and the check could not see it -- the same family as The
    Lancet's middle dot and the Greek alpha extracting as "a". A comparison
    that cannot see the thing it is comparing does not get to report an
    absence.

    Precision differences are B12's question, not this one. This check asks
    only whether the quantity appears at all.
    """
    out = set()
    for f in figs:
        try:
            out.add(float(f))
        except ValueError:
            continue
    return out


def _claim_figures(text: str) -> set[str]:
    """The figures a sentence CLAIMS, which is not every digit string in it.

    "KEYNOTE-942" and "mRNA-4157" are names. The first run of the coverage
    check read 942 as a figure and reported it missing from the span the
    sentence was bound to, which is true and meaningless. A number inside a
    token that also carries letters is part of an identifier, not a
    measurement -- stated as a rule about token shape rather than as a list of
    the identifiers we happen to have met, because every allowlist built from
    met vocabulary in this repository has been wrong.
    """
    import modelbind as MB
    named = set()
    for tok in re.split(r"\s+", text):
        if re.search(r"[A-Za-z]", tok) and re.search(r"\d", tok):
            named |= MB.figures(tok)
    return {f for f in MB.figures(text) if f not in named}


def rule_rows(slug: str) -> list[tuple[str, str, str]]:
    """The two rules, as blocking rows. Every sentence on the page, no exemptions."""
    import spancheck as SC
    import modelbind as MB
    doc = load(slug)
    rows = doc.get("bindings") or {}
    on_page = {k: v for k, v in rows.items() if v.get("on_page")}

    # WHAT RULE 1 ASKS OF A JUDGEMENT, AND WHY IT IS NOT A SPAN
    #
    # The editor's two rules divide the page: a FACTUAL STATEMENT rests on a
    # document we hold and read; an INFERENCE is flagged and shows the logic
    # and the facts behind it. The first version of this check demanded a span
    # from every sentence including the judgements, which would have pushed me
    # to point "0.0266 and 0.053 are the same result" at some passage it does
    # not rest on -- inventing a binding to satisfy a check, which is the
    # failure mode this whole file exists to prevent.
    #
    # So a judgement satisfies rule 1 through its PREMISES, each of which is a
    # span in a held document, checked by rule 2 below. This is not a softer
    # requirement: a judgement must carry premises AND a written-out step,
    # where a report needs only its span. Declaring a sentence a judgement to
    # escape rule 1 buys strictly more work, which is the property that keeps
    # the bucket honest.
    def covering(v):
        spans = []
        if v.get("span"):
            spans.append((v.get("source_id"), v["span"]))
        spans += [(x.get("source_id"), x.get("span") or "")
                  for x in (v.get("also_rests_on") or [])]
        if (v.get("bucket") or "") == "judgement":
            spans += [(x.get("source_id"), x.get("span") or "")
                      for x in (v.get("premises") or [])]
        return [(sid, sp) for sid, sp in spans if sid and sp]

    unbound = [k for k, v in on_page.items() if not covering(v)]

    # A SENTENCE IS NOT BOUND BECAUSE ONE OF ITS FIGURES IS.
    #
    # "the three-year paper says 80% power against a one-sided alpha of 0.10,
    # and the ASCO deck states the same threshold" rests on two documents. Bind
    # it to the paper and rule 1 goes green with half the sentence resting on
    # nothing -- a check applied where its premise holds, and nothing asking
    # the other question, which is the shape of every failure in this file's
    # history. So: every figure the sentence carries must appear in a span the
    # sentence is actually bound to.
    loose, loose_keys = [], set()
    for k, v in on_page.items():
        spans = covering(v)
        if not spans:
            continue
        covered = ""
        for sid, span in spans:
            present, why = SC.b2_present(span, slug, sid)
            if present is not True:
                loose.append("%s: a span it names is not in %s" % (k[:8], sid))
                loose_keys.add(k)
                continue
            covered += " " + SC._norm(span)
        held = _as_numbers(MB.figures(covered))
        missing = [f for f in _claim_figures(v["sentence"])
                   if MB._weight(f) and not _as_numbers([f]) <= held]
        if missing:
            loose.append("%s: %s in no span it is bound to (%s)"
                         % (k[:8], ", ".join(sorted(missing)[:4]),
                            v["sentence"][:40]))
            loose_keys.add(k)

    out = [("rule 1 — written from a document we hold",
            OK if not (unbound or loose) else BAD,
            "all %d sentence(s) name the words they rest on, and every figure "
            "they carry is in one of those spans" % len(on_page)
            if not (unbound or loose) else
            "%d of %d rest on nothing, %d carry a figure no bound span "
            "contains: %s"
            % (len(unbound), len(on_page), len(loose),
               " || ".join(([on_page[k]["sentence"][:50] for k in unbound[:2]]
                            + loose)[:3])))]

    # RULE 2, IN THE SPEC'S VOCABULARY AND NOT A NEW ONE
    #
    # The first draft of this check invented a bucket called "inference".
    # BUCKETS had been defined at the top of this file since the spec was
    # written -- deterministic, context, judgement, figure -- and used by
    # nothing. Section 3 already says an unclassified sentence is a defect;
    # section 7 already routes a licence-reserved source to the operator by
    # recorded question and answer. Both were written down and neither ran.
    # That is the fifth instance of this pattern in three days, so: no new
    # words. An inference is a `judgement` sentence, and the editor's demand
    # that it show its logic and its facts is the premises-and-step
    # requirement below.
    unbucketed = [k for k, v in on_page.items() if not v.get("bucket")]
    wrong = [k for k, v in on_page.items()
             if v.get("bucket") and v["bucket"] not in BUCKETS]
    bad = ["%s: bucket %r is not one of %s"
           % (k[:8], on_page[k]["bucket"], ", ".join(BUCKETS)) for k in wrong]

    for k, v in on_page.items():
        bucket = v.get("bucket") or ""
        if bucket == "judgement":
            # The editor's rule 2: flag the inference, show the logic and the
            # facts. Premises are checked against held bytes; the step is
            # written out so a reader can disagree with the reasoning rather
            # than only with the conclusion.
            prem = v.get("premises") or []
            if not prem:
                bad.append("%s: a judgement with no premises" % k[:8])
            for pr in prem:
                sid, span = pr.get("source_id"), pr.get("span") or ""
                if not sid or not span:
                    bad.append("%s: a premise with no source or no span" % k[:8])
                    continue
                present, why = SC.b2_present(span, slug, sid)
                if present is not True:
                    bad.append("%s: a premise whose span is not in %s"
                               % (k[:8], sid))
            if not (v.get("step") or "").strip():
                bad.append("%s: a judgement with no step written out" % k[:8])
        elif bucket == "figure":
            # Spec section 3: for a figure-based sentence "locatable" is NOT
            # POSSIBLE by machine, and section 7 routes anything a licence
            # reserves to a person to the operator, by recorded question and
            # answer. So the row must name the person, the record, and the
            # place in the document -- and this check must never report such a
            # span as verified, because it has not read the document.
            for field, what in (("attested_by", "who read it"),
                                ("attested_in", "the record of the reading"),
                                ("locator", "where in the document")):
                if not (v.get(field) or "").strip():
                    bad.append("%s: a figure-based sentence with no %s"
                               % (k[:8], what))

    out.append(("rule 2 — every sentence declares its kind, judgements show "
                "their work",
                OK if not (unbucketed or bad) else BAD,
                "all %d sentence(s) declare a bucket, and every judgement "
                "shows its premises and its step" % len(on_page)
                if not (unbucketed or bad) else
                "%d undeclared, %d problem(s): %s"
                % (len(unbucketed), len(bad),
                   " || ".join((bad + [on_page[k]["sentence"][:50]
                                       for k in unbucketed])[:3]))))

    todo = set(unbound) | set(unbucketed) | set(wrong)
    todo |= loose_keys
    if todo:
        out.append(("sentences still to revalidate", WARN,
                    "%d of %d. Adopted %s with no exemption for what was "
                    "already written: every sentence in the article is either "
                    "bound to the words it rests on, declared as an inference "
                    "and shown, or off the page."
                    % (len(todo), len(on_page), RULE_ADOPTED)))
    return out


def preflight_rows(slug: str) -> list[tuple[str, str, str]]:
    try:
        doc = load(slug)
    except Exception as exc:
        return [("claim bindings", WARN, "could not read bindings.json: %s" % exc)]
    rows = doc.get("bindings") or {}
    if not rows:
        return [("claim bindings", WARN,
                 "no bindings recorded — run bindings.py %s scan. Until then no "
                 "sentence on this page names the words it rests on." % slug)]
    on_page = {k: v for k, v in rows.items() if v.get("on_page")}
    bound = [k for k, v in on_page.items() if v.get("span")]
    unbucketed = [k for k, v in on_page.items() if not v.get("bucket")]
    out = [("empirical sentences bound",
            OK if len(bound) == len(on_page) else WARN,
            "all %d empirical sentence(s) name the words they rest on"
            % len(on_page) if len(bound) == len(on_page) else
            "%d of %d empirical sentence(s) are bound to a span; %d rest on "
            "nothing this system can name"
            % (len(bound), len(on_page), len(on_page) - len(bound)))]
    out.extend(rule_rows(slug))
    flagged = [k for k, v in on_page.items() if v.get("check_flags")]
    checked = [k for k, v in on_page.items() if v.get("checked_on")]
    if checked:
        out.append(("bound sentences the span checks flagged",
                    OK if not flagged else BAD,
                    "none of the %d bound sentence(s) is flagged" % len(checked)
                    if not flagged else
                    "%d of %d bound sentence(s) carry a flag: %s"
                    % (len(flagged), len(checked),
                       " || ".join("%s %s" % (f["check"], f["verdict"])
                                   for k in flagged[:4]
                                   for f in on_page[k]["check_flags"][:1]))))
    if unbucketed:
        out.append(("sentences with no declared bucket", WARN,
                    "%d of %d — a sentence whose kind nobody declared cannot be "
                    "routed to the process that should check it"
                    % (len(unbucketed), len(on_page))))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("slug")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("scan", help="add a blank row for every unbound empirical sentence")
    u = sub.add_parser("unbound", help="print the sentences that rest on nothing named")
    u.add_argument("--limit", type=int, default=25)
    sub.add_parser("check", help="run the span checks from the bindings")
    sub.add_parser("status")
    args = ap.parse_args()

    if args.cmd == "check":
        t = run_checks(args.slug)
        print("\n  %d bound sentence(s) checked against the source each row "
              "names" % t["checked"])
        print("  %d flag(s), %d undetermined\n" % (t["flags"], t["undetermined"]))
        doc = load(args.slug)
        for sha, row in (doc.get("bindings") or {}).items():
            # ONLY WHAT IS STILL ON THE PAGE. A row whose sentence has been
            # edited keeps its old flags as history and is no longer a finding;
            # printing them made the header say "0 flags" above two flags.
            if not row.get("on_page"):
                continue
            for f in (row.get("check_flags") or []):
                print("  %-7s %-20s %s" % (f["check"], f["verdict"],
                                           row["sentence"][:78]))
                print("          %s" % f["why"][:130])
        print()
        return 0

    if args.cmd == "scan":
        doc, unbound, stale = scan(args.slug)
        rows = doc["bindings"]
        on_page = sum(1 for v in rows.values() if v.get("on_page"))
        print("\n  %d empirical sentence(s) on the page" % on_page)
        print("  %d bound, %d unbound" % (on_page - len(unbound), len(unbound)))
        if stale:
            print("  %d row(s) for sentences no longer on the page, kept as record"
                  % len(stale))
        print("  written to %s\n" % path(args.slug))
        return 0

    if args.cmd == "unbound":
        doc = load(args.slug)
        rows = [v for v in (doc.get("bindings") or {}).values()
                if v.get("on_page") and not v.get("span")]
        print("\n  %d unbound empirical sentence(s)\n" % len(rows))
        for r in rows[:args.limit]:
            print("  [%s] %s" % (r["why_empirical"], r["sentence"][:150]))
        print()
        return 0

    print()
    for label, state, detail in preflight_rows(args.slug):
        print("  %-6s %-34s %s" % (state, label, detail))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
