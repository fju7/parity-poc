"""One place that asks the registry before anything asks a model.

WHY THIS EXISTS
---------------
The 2026-08-31 page gate cost $5.70. Its single most expensive line:

    source:HARMONIA — ClinicalTrials.gov    $0.87   253,272 tok   9 searches

Nine web searches and eighty-seven cents to establish that HARMONIA opened in
March 2022, terminated, and enrolled 61 patients. All three are structured
fields. The ClinicalTrials.gov API returns them in under a second, for nothing.
`registry_facts.py` had ALREADY CONFIRMED ALL THREE, on the board, before the
run started -- and the run went and bought them again.

The deterministic tier was overturning the model's verdict AFTER the spend.
registry_figures.py's own docstring says it

    "runs BEFORE the SOURCE role, settles what it can, and is both cheaper and
     more accurate than the thing it short-circuits"

and it did not. It ran in the preflight, which is a different program. The
sentence described an intention.

WHAT THIS DOES
--------------
It is the one object both callers use, so they cannot drift:

    the GATE   asks it before building each source group, drops the claims it
               settles, and skips the API call entirely when a group empties.
    the BOARD  asks it when deciding whether a model's NOT_FOUND or WRONG_VALUE
               survives contact with the registry.

Same evidence, same rule, one implementation.

A SETTLED CLAIM IS NOT A SKIPPED CLAIM. It comes back with a verdict, a reason
and the registry record behind it, and it appears in the report as VERIFIED by
the registry. A claim that vanishes because it was cheap to settle would make
the report say less than it knows, which is the failure mode of every
optimisation in this pipeline.

WHAT IT WILL NOT SETTLE
-----------------------
Everything else. It confirms; it never contradicts, and it never settles a
claim whose checkable parts it cannot ALL confirm. Where it is silent the model
runs exactly as before and costs exactly what it cost. The saving comes only
from work that did not need doing.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _sibling(name):
    sp = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


class Settler:
    """What the trial registry can confirm about this page, asked once."""

    def __init__(self, slug: str, page_text: str):
        self.slug = slug
        self.numbers: set[str] = set()
        self.facts: dict = {}
        self.error: str | None = None
        try:
            rfig = _sibling("registry_figures")
            rfac = _sibling("registry_facts")
            self._rfac = rfac
            self.numbers = {f["norm"] for f in rfig.findings(slug, page_text)
                            if f["in_registry"]}
            self.facts = rfac.confirmed_keys(slug, page_text)
        except BaseException as exc:   # noqa: BLE001
            # BaseException, NOT Exception. registry_figures.case_dir() raises
            # SystemExit for an unknown slug, and SystemExit is not an Exception
            # -- so the first version of this let it straight through and a
            # cost-saving pre-check killed the email gate, after that run had
            # already paid for claim extraction. A helper that promises never to
            # break its caller has to mean every exit path.
            if isinstance(exc, KeyboardInterrupt):
                raise
            self._rfac = None
            self.error = "%s: %s" % (type(exc).__name__, exc)

    def __bool__(self) -> bool:
        return bool(self.numbers or self.facts)

    def settles(self, figure: str = "", quote: str = "",
                attributed_to: str = "") -> str | None:
        """A reason, if the registry confirms every checkable part. Else None."""
        if self.error:
            return None
        import re

        # 1. Against the record the claim ITSELF names.
        #
        # This was missing from the first version and it is where nearly all
        # the saving is. registry_figures only reads figures out of SHORT page
        # blocks carrying one NCT -- a scope rule it needed, because it was
        # attributing figures found in prose. Here there is nothing to guess:
        # the gate has already told us this claim is attributed to
        # "MONALEESA-7 — ClinicalTrials.gov results posting. NCT02278120", and
        # the question is only whether that record contains these numbers.
        #
        # Without this, a claim reading "MONALEESA-7's results posting gives
        # p = 0.00973" went to a model with web search, which could not reach
        # the posting, and came back NOT_FOUND -- about a number sitting in the
        # record the claim names.
        ncts = {n.upper() for n in re.findall(r"NCT\d{8}", attributed_to or "", re.I)}
        if len(ncts) == 1:
            why = self._against_record(ncts.pop(), figure, quote)
            if why:
                return why

        # 2. Against what the registry confirms elsewhere on the page.
        nums = re.findall(r"\d+\.\d+", figure or "")
        if nums and all(("%g" % float(n)) in self.numbers for n in nums):
            return ("every figure in this claim is posted in the trial's "
                    "ClinicalTrials.gov record: %s" % ", ".join(sorted(set(nums))))
        if self._rfac is not None:
            for text in (quote, figure):
                if text and self._rfac.quote_fully_confirmed(text, self.facts):
                    parts = ", ".join(
                        "%s=%s" % (f, v)
                        for f, v, _m in self._rfac.claims_in(text))
                    return ("every trial fact in this claim is a structured field "
                            "in its ClinicalTrials.gov record: %s" % parts)
        return None

    def _against_record(self, nct: str, figure: str, quote: str) -> str | None:
        """Confirm a claim against one named registry record."""
        import re
        try:
            rfig = _sibling("registry_figures") if not hasattr(self, "_rfig") else self._rfig
            self._rfig = rfig
            raw = rfig.registry_text(nct)
        except Exception:
            return None
        if not raw:
            return None

        text = "%s %s" % (figure or "", quote or "")

        # The claim is that the trial HAS this registry number. The record
        # answers it: does it name the trial? "HARMONIA is registered as
        # NCT05207709" went to a model with web search, three times over three
        # runs, for a string comparison against a document we already had.
        if re.fullmatch(r"\s*NCT\d{8}\s*", figure or ""):
            names = re.findall(r"\b[A-Z][A-Z0-9]{3,}(?:-\d+[a-z]?)?\b", quote or "")
            named = [n for n in names if not n.startswith("NCT")]
            hits = [n for n in named if re.search(r"\b%s\b" % re.escape(n), raw, re.I)]
            if named and len(hits) == len(named):
                return ("the record for %s names %s, so the registration this claim "
                        "states is the registration the registry holds"
                        % (nct, ", ".join(sorted(set(hits)))))
            return None

        nums = re.findall(r"\d+\.\d+", figure or "")
        if not nums:
            return self._annotation(nct, figure, quote)
        posted = rfig.numbers_in(raw)
        if all(("%g" % float(n)) in posted for n in nums):
            return ("every figure in this claim appears in %s, the "
                    "ClinicalTrials.gov record the claim itself names: %s"
                    % (nct, ", ".join(sorted(set(nums)))))
        return None

    _JSON: dict = {}

    def _record_json(self, nct: str):
        """The results section as structured data, cached per process."""
        if nct in Settler._JSON:
            return Settler._JSON[nct]
        import json as _json
        import urllib.request
        out = None
        try:
            url = ("https://clinicaltrials.gov/api/v2/studies/" + nct
                   + "?fields=ResultsSection")
            req = urllib.request.Request(
                url, headers={"User-Agent": "civicscale-registry-check"})
            out = _json.load(urllib.request.urlopen(req, timeout=30))
        except Exception:
            out = None
        Settler._JSON[nct] = out
        return out

    def _annotation(self, nct: str, figure: str, quote: str) -> str | None:
        """A quoted annotation the registry attaches to its own analyses.

        WHY THIS IS SEPARATE FROM THE NUMBERS.

        The claim that cost the most in the 2026-09-01 run was not a number:

            PALOMA-2's ClinicalTrials.gov results posting annotates every
            log-rank p-value as '1-sided p-value from the stratified log-rank
            test'.

            source:PALOMA-2 — ClinicalTrials.gov   $0.92  270,004 tok  8 searches

        Eight web searches and ninety-two cents for a string comparison against
        a document the API hands over in a second. It was the only claim in its
        group the settler could not take, and one unsettled claim keeps the
        whole group's call alive -- so it cost more than the three groups the
        settler eliminated saved.

        AND THE WORD "EVERY" IS THE POINT. Finding the string once would not
        establish the claim; the claim is universal. So this does not search for
        the string, it ENUMERATES: take the analyses whose statistical method
        the claim names, and require that every one of them carries it. Three of
        three, for PALOMA-2. If some carry it and some do not, the universal is
        false or narrower than stated, and this stays silent and lets the model
        and then a person deal with it.

        Confirming a universal by finding one instance is the error this whole
        apparatus exists to prevent. It would have been the cheap way to write
        this function.
        """
        import re
        fig = " ".join((figure or "").split()).strip().strip("'\u2018\u2019\"\u201c\u201d")
        if len(fig) < 20 or re.fullmatch(r"[\d\s.,%()\u2013-]+", fig):
            return None
        doc = self._record_json(nct)
        if not doc:
            return None
        try:
            oms = doc["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"]
        except Exception:
            return None

        text = ((figure or "") + " " + (quote or "")).lower()
        want = None
        for key, needle in (("log-rank", "log rank"), ("log rank", "log rank"),
                            ("fisher", "fisher"), ("cox", "cox"),
                            ("chi-square", "chi-squar")):
            if key in text:
                want = needle
                break

        matched, carrying = [], []
        for om in oms:
            for a in om.get("analyses", []) or []:
                method = (a.get("statisticalMethod") or "").lower()
                comment = a.get("pValueComment") or ""
                if want is not None:
                    if want not in method:
                        continue
                elif not comment:
                    continue
                matched.append(a)
                if fig.lower().rstrip(".") in " ".join(comment.split()).lower():
                    carrying.append(a)

        if matched and len(carrying) == len(matched):
            return ("every one of the %d %sanalysis/analyses in %s carries this "
                    "annotation verbatim -- enumerated in the record, not found "
                    "once and generalised"
                    % (len(matched), (want + " ") if want else "", nct))
        return None

    def summary(self) -> str:
        if self.error:
            return "the registry check did not run (%s)" % self.error
        return ("%d figure(s) and %d trial fact(s) confirmed at ClinicalTrials.gov"
                % (len(self.numbers), sum(len(v) for v in self.facts.values())))
