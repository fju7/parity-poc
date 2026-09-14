"""Text normalisation and the distinctive-word test behind HEADING.

Ported from scripts/signal/verify_sources.py (title_agreement) and
scripts/whatholdsup/errata.py (resolves_to_us), which learned the hard way that
sequence similarity scores MONARCH 3 against its registry title as a different
trial. Identity is judged on DISTINCTIVE CONTENT WORDS with boilerplate
stripped, and the only thing the test claims is: zero shared distinctive words
means a different document.
"""
from __future__ import annotations

import re
import unicodedata

# Words that appear in nearly every trial or paper title and identify nothing.
LITERATURE_BOILERPLATE = {
    "a", "an", "the", "of", "in", "for", "with", "and", "or", "to", "on", "at", "by", "from",
    "vs", "versus", "plus", "study", "trial", "phase", "randomized", "randomised",
    "double", "blind", "blinded", "placebo", "controlled", "multicenter", "multicentre",
    "open", "label", "active", "evaluate", "evaluation", "test", "investigational",
    "patients", "participants", "adults", "subjects", "efficacy", "safety", "comparing",
    "compared", "comparison", "treatment", "therapy", "first", "second", "line", "i", "ii",
    "iii", "iv", "1", "2", "3", "4", "who", "have", "as", "after", "before", "using", "use",
    "assessment", "analysis", "effect", "effects", "outcomes", "results", "review",
    "systematic", "final", "overall", "update", "updated", "years", "year",
    # Oncology-generic. Added 2026-09-14 when a PMID typed from memory resolved
    # to "Nivolumab plus Ipilimumab in Advanced Non-Small-Cell Lung Cancer" and
    # HEADING passed it against "MONALEESA-7 ... advanced breast cancer" on
    # the strength of "advanced" and "cancer".
    "advanced", "cancer", "cancers", "disease", "metastatic", "carcinoma", "early", "stage",
}

# Words that appear in nearly every statute, rule or manual section and identify
# nothing: the law analogue. "prompt" is NOT here; "payment" is not either --
# 3901.38's heading is "Prompt payments to health care providers definitions".
LAW_BOILERPLATE = {
    "a", "an", "the", "of", "in", "for", "with", "and", "or", "to", "on", "at", "by", "from",
    "as", "any", "all", "such", "shall", "may", "must", "under", "this", "that", "these",
    "section", "sections", "chapter", "rule", "rules", "code", "title", "part", "subpart",
    "provision", "provisions", "requirement", "requirements", "standard", "standards",
    "general", "definitions", "definition", "purpose", "scope", "applicability",
    "claim", "claims", "insurer", "insurers", "insurance", "payer", "payers", "plan", "plans",
    "policy", "policies", "contract", "contracts", "coverage", "covered", "health", "care",
    "medical", "service", "services", "provider", "providers", "person", "persons",
    "means", "including", "other", "each", "not", "no", "is", "are", "be", "been", "was",
    "state", "federal", "law", "act", "regulation", "regulations", "regulatory", "applicable",
    "processing", "process", "practices", "practice", "conditions", "condition", "basic",
    "administrative", "revised", "ohio", "united", "states", "cfr", "usc", "iom", "ncci",
    "manual", "publication", "et", "seq", "based", "basis", "obligation", "obligations",
}


def normalise(s: str | None) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def content_tokens(s: str, boilerplate: set[str]) -> set[str]:
    """Distinctive words: not boilerplate, longer than two letters, not a bare number
    ("Chapter 3902", "Phase 3", "2019" identify nothing on their own)."""
    return {w for w in normalise(s).split() if w not in boilerplate and len(w) > 2 and not w.isdigit()}


def agreement(ours: str, theirs: str, boilerplate: set[str]) -> tuple[float, set[str]]:
    """(ratio, shared) between our characterisation and the registry's heading.

    `theirs` may hold alternatives joined by ' || ' (registry official title,
    brief title, acronym). Containment of one normalised string in the other
    is 1.0 outright -- "MONARCH 3" inside the registry's acronym field.
    """
    a = normalise(ours)
    ta = content_tokens(ours, boilerplate)
    best, best_shared = 0.0, set()
    for cand in (theirs or "").split(" || "):
        b = normalise(cand)
        if not b:
            continue
        if a and b and (a in b or b in a or a.replace(" ", "") in b.replace(" ", "")
                        or b.replace(" ", "") in a.replace(" ", "")):
            return 1.0, ta or {a}
        tb = content_tokens(cand, boilerplate)
        if ta and tb:
            shared = ta & tb
            r = len(shared) / min(len(ta), len(tb))
            if r > best:
                best, best_shared = r, shared
    return round(best, 3), best_shared

# A web page's <title> carries the site's name and furniture. Stripped only
# for the generic adapter, on top of the literature list.
GENERIC_BOILERPLATE = {
    "home", "page", "pages", "site", "official", "website", "www", "com", "gov", "org", "html", "pdf",
    "news", "press", "release", "statement", "document", "documents", "report", "reports", "public",
    "information", "resources", "about", "search", "menu", "skip", "content", "main", "login",
}
