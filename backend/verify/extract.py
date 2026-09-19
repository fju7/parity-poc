"""Per-class extractors: find every candidate assertion of a class in free text.

Shared assertion policy, Phase B (docs/shared-assertion-policy-phase-a-inventory.md
§D). Each extractor is a pure function text -> list[Candidate]. It finds; it
never decides. Deciding is policy.check()'s job, through the binders in this
package. Nothing here calls a model or the network.

Five classes:
  LEGAL_PROVISION   statute / code / CFR / USC / rule / manual section numbers
                    -- utils.citation_gate.find_citations, unchanged, is the extractor
  IDENTIFIER        DOI / PMID / PMCID / NCT / FDA PMA / journal-style cite
  NAMED_SOURCE      an agency, programme, guideline body, statute NAME or a
                    regulatory-status word, without a number -- the register in
                    which Health's appeal_rights relabelling happened
  FIGURE            numbers (digits or words) -- verify.numbers
  CODED_DESCRIPTOR  a code we hold (CPT/HCPCS/CARC/RARC/ICD-10/NDC) followed by a
                    descriptor the model supplied

False positives are cheap (a finding a human dismisses in seconds); false
negatives are the 2026-09-14 failures. The patterns lean wide.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from utils.citation_gate import find_citations
from .numbers import stated_figures, figures as _figures, _canon


class AssertionClass(str, Enum):
    LEGAL_PROVISION = "legal_provision"
    IDENTIFIER = "identifier"
    NAMED_SOURCE = "named_source"
    FIGURE = "figure"
    CODED_DESCRIPTOR = "coded_descriptor"
    LEGAL_REGISTER = "legal_register"     # APPEALS-3: the register of counsel, not a citation
    ENCLOSURE = "enclosure"               # APPEALS-4: "enclosed / attached / herewith" -- a document the pipeline does not hold


@dataclass(frozen=True)
class Candidate:
    cls: AssertionClass
    text: str            # what was found, as it appeared
    start: int
    end: int
    kind: str = ""       # sub-kind: citation family, identifier system, lexicon term, code system
    value: str = ""      # normalised value where one exists (identifier, code, figure)
    extra: str = ""      # descriptor text for CODED_DESCRIPTOR


# ---------------------------------------------------------------------------
# IDENTIFIER
# ---------------------------------------------------------------------------
_ID_PATTERNS = {
    "doi":     re.compile(r"\b10\.\d{4,9}/[^\s\"'<>)\]]+"),
    "nct":     re.compile(r"\bNCT\d{8}\b"),
    "pmcid":   re.compile(r"\bPMC\d{6,9}\b"),
    "pmid":    re.compile(r"\bPMID:?\s*\d{6,9}\b|\bpubmed\.ncbi\.nlm\.nih\.gov/\d+"),
    # a bare 7-8 digit number is the shape of a PMID typed from memory (Health's
    # _FAB_BARE_PMID_RE); it is reported as "bare_pmid" so a policy can treat
    # it as a weaker signal than an explicit PMID
    "bare_pmid": re.compile(r"(?<![\d.$,/-])\d{7,8}(?![\d.,%-])"),
    "fda_pma": re.compile(r"\b[PK]\d{6}\b"),
    "journal_cite": re.compile(r"\b(?:19|20)\d{2};\s?\d+(?:\(\d+\))?:\s?\d+"),
    "et_al":   re.compile(r"\bet al\b\.?", re.I),
}


# THE RECOMBINATION SHAPE. Jain 2015 was stored as 10.1001/jama.2015.1534:
# correct registrant, correct journal code, correct year -- and the real FIRST
# PAGE (JAMA 2015;313(15):1534-1540) recombined into the DOI suffix. It
# resolved to nothing, and nothing short of the registry round-trip caught it,
# because every part of it was plausible. A DOI whose suffix repeats a page,
# volume or issue number of the citation it sits in is FLAGGED, never refused:
# some publishers mint exactly that shape (10.1093/ije/31.2.285 is volume 31,
# issue 2, page 285, and real). A year in the suffix is not a flag on its own
# -- JAMA and NEJM put the year in every DOI.
_CITE_VOL_ISSUE = re.compile(r"\b(\d{1,4})\s*\((\d{1,4})\)\s*:")           # 313(15):
_CITE_VOL_COLON = re.compile(r"\b(\d{1,4})\s*:\s*(?:[A-Za-z]{0,6}\d)")         # 313:1534, 372:m4570
_CITE_PAGES = re.compile(r"(?:(?<=[:\s])|\bp{1,2}\.?\s*)(e?\d{1,6})(?:\s*[-\u2013\u2014]\s*(e?\d{1,6}))?(?=[\s.,;)]|$)")
_CITE_ELOC = re.compile(r":\s*([A-Za-z]{1,6}\d{3,}[A-Za-z0-9]*|\d{2,}[A-Za-z]{2,}[A-Za-z0-9]*)")   # :m4570 :CD015687 :EVIDra2300029 :110native


def citation_numbers(citation: str, doi: str = "") -> dict:
    """{'volume', 'issue', 'page', 'year', 'article'}: the numbers a citation
    states, with the DOI itself blanked so it cannot vouch for itself.
    'article' holds alphanumeric elocation ids (m4570, CD015687, e424)."""
    c = (citation or "")
    if doi:
        c = c.replace(doi, " ")
    c = re.sub(r"\b10\.\d{4,9}/\S+", " ", c)
    out = {"volume": set(), "issue": set(), "page": set(), "article": set(),
           "year": set(re.findall(r"\b(?:19\d{2}|20[0-2]\d)\b", c))}     # a page number 2030 is not a year
    for m in _CITE_VOL_ISSUE.finditer(c):
        out["volume"].add(m.group(1)); out["issue"].add(m.group(2))
    for m in _CITE_VOL_COLON.finditer(c):
        out["volume"].add(m.group(1))
    for m in _CITE_PAGES.finditer(c):
        for g in (m.group(1), m.group(2)):
            if g and g not in out["year"] and g not in out["volume"] and g not in out["issue"]:
                out["page"].add(g.lstrip("e"))
    for m in _CITE_ELOC.finditer(c):
        out["article"].add(m.group(1))
    return out


def doi_recombination(doi: str, citation: str) -> str | None:
    """A note when the DOI's suffix repeats a page / volume / issue / article
    number the citation states, or the volume, issue and page run together
    (MDPI's nu12061190 is volume 12, issue 06, article 1190); None otherwise.
    Pure numbers are compared as whole digit runs (1534 in ...2015.1534, not
    15 inside 2015); elocation ids as case-insensitive substrings."""
    if not doi or "/" not in doi:
        return None
    suffix = doi.split("/", 1)[1]
    runs = set(re.findall(r"\d+", suffix))
    nums = citation_numbers(citation, doi)
    hits = []
    for label in ("page", "volume", "issue"):
        for n in sorted(nums[label] & runs, key=len, reverse=True):
            if len(n) >= 2:
                hits.append(f"{label} {n}")
    for a in sorted(nums["article"]):
        if len(a) >= 4 and a.lower() in suffix.lower():
            hits.append(f"article {a}")
    for v in nums["volume"]:
        for i in nums["issue"] or {""}:
            for pg in nums["page"] | nums["article"]:
                for ii in {i, i.zfill(2)} if i else {""}:
                    cat = f"{v}{ii}{pg}".lower()
                    if len(cat) >= 6 and cat in suffix.lower():
                        hits.append(f"volume {v}" + (f", issue {i}" if i else "") + f" and {pg} run together")
    seen, uniq = set(), []
    for h in hits:
        if h not in seen:
            seen.add(h); uniq.append(h)
    return ("DOI suffix repeats the citation's " + ", ".join(uniq)) if uniq else None


def _citation_window(text: str, start: int, end: int, span: int = 300) -> str:
    """The citation the identifier sits in: the same line, capped at `span`
    characters each side. Citations use '. ' between their parts, so a
    sentence bound would cut the page range off from the DOI."""
    lo = max(text.rfind("\n", 0, start), start - span)
    hi = text.find("\n", end)
    hi = min(hi if hi != -1 else len(text), end + span)
    return text[lo + 1:hi]


def extract_identifiers(text: str) -> list[Candidate]:
    out = []
    for kind, rx in _ID_PATTERNS.items():
        for m in rx.finditer(text or ""):
            raw = m.group(0)
            val = raw
            extra = ""
            if kind == "doi":
                val = raw.rstrip(".,;)").lower()
                extra = doi_recombination(val, _citation_window(text, m.start(), m.end())) or ""
            elif kind == "pmid":
                val = re.sub(r"\D", "", raw)
            out.append(Candidate(AssertionClass.IDENTIFIER, raw, m.start(), m.end(), kind, val, extra))
    return _dedupe(out)


# ---------------------------------------------------------------------------
# NAMED_SOURCE -- a lexicon, reviewed, small. Grows like the candidate table.
# ---------------------------------------------------------------------------
NAMED_SOURCE_LEXICON = {
    # agencies and bodies
    "fda": r"\bFDA\b|\bFood and Drug Administration\b",
    "cms": r"\bCMS\b|\bCenters for Medicare (?:&|and) Medicaid Services\b",
    "dol": r"\bDOL\b|\bDepartment of Labor\b",
    "ebsa": r"\bEBSA\b|\bEmployee Benefits Security Administration\b",
    "hhs": r"\bHHS\b|\bDepartment of Health and Human Services\b",
    "irs": r"\bIRS\b|\bInternal Revenue Service\b",
    "doi_state": r"\bDepartment of Insurance\b|\bInsurance Commissioner\b",
    "oig": r"\bOIG\b|\bOffice of Inspector General\b",
    "medicare": r"\bMedicare\b",
    "medicaid": r"\bMedicaid\b",
    # guideline bodies
    "nccn": r"\bNCCN\b|\bNational Comprehensive Cancer Network\b",
    "asco": r"\bASCO\b|\bAmerican Society of Clinical Oncology\b",
    "esmo": r"\bESMO\b",
    "nice": r"\bNICE\b|\bNational Institute for Health and Care Excellence\b",
    "uspstf": r"\bUSPSTF\b",
    "aha_acc": r"\bAHA/ACC\b|\bAmerican Heart Association\b|\bAmerican College of Cardiology\b",
    "ama": r"\bAMA\b|\bAmerican Medical Association\b",
    "jama": r"\bJAMA\b|\bJournal of the American Medical Association\b",   # longer than 'ama'; wins the span
    "who": r"\bWHO\b|\bWorld Health Organization\b",
    "cdc": r"\bCDC\b|\bCenters for Disease Control\b",
    # statute and programme names (without numbers)
    "erisa": r"\bERISA\b|\bEmployee Retirement Income Security Act\b",
    "aca": r"\bACA\b|\bAffordable Care Act\b",
    "caa": r"\bCAA\b|\bConsolidated Appropriations Act\b",
    "nsa": r"\bNo Surprises Act\b",
    "hipaa": r"\bHIPAA\b",
    "mhpaea": r"\bMHPAEA\b|\bMental Health Parity\b",
    "cobra": r"\bCOBRA\b",
    "ncci": r"\bNCCI\b|\bNational Correct Coding Initiative\b",
    "fab": r"\bField Assistance Bulletin\b",
    "advisory_opinion": r"\bAdvisory Opinion\b",
    "lcd_ncd": r"\b(?:LCD|NCD)s?\b|\bLocal Coverage Determination\b|\bNational Coverage Determination\b",
    "moldx": r"\bMolDX\b",
    # regulatory status words -- assertions about what a body has done
    "breakthrough": r"\bBreakthrough (?:Device|Therapy)\b",
    "priority_review": r"\bPriority Review\b",
    "fda_status": r"\bFDA[- ](?:approved|cleared|authori[sz]ed|designated)\b",
    "guideline_status": r"\bguideline[- ](?:recommended|endorsed|concordant)\b|\brecommended by\b|\bendorsed by\b",
    "external_review": r"\b(?:independent )?external review\b|\bindependent review organi[sz]ation\b",
}
_NAMED_RX = {k: re.compile(v, re.I if k in ("fda_status", "guideline_status", "external_review") else 0)
             for k, v in NAMED_SOURCE_LEXICON.items()}


def extract_named_sources(text: str) -> list[Candidate]:
    out = []
    for term, rx in _NAMED_RX.items():
        for m in rx.finditer(text or ""):
            out.append(Candidate(AssertionClass.NAMED_SOURCE, m.group(0), m.start(), m.end(), term, term))
    return _dedupe(out)


# ---------------------------------------------------------------------------
# LEGAL_PROVISION -- the citation gate, unchanged
# ---------------------------------------------------------------------------
def extract_legal(text: str) -> list[Candidate]:
    return [Candidate(AssertionClass.LEGAL_PROVISION, c.text, c.start, c.end, c.family, c.text)
            for c in find_citations(text or "")]


# ---------------------------------------------------------------------------
# FIGURE
# ---------------------------------------------------------------------------
def extract_figures(text: str) -> list[Candidate]:
    """Digit-form figures with position; word-form figures are folded in
    without position (verify.numbers keeps exact matching for them)."""
    out = []
    seen = set()
    cursor = 0
    for f in stated_figures(text or ""):
        raw = f.get("text") or str(f.get("value"))
        val = _canon(f["value"])
        pos = (text or "").find(raw, cursor)
        if pos < 0:
            pos = (text or "").find(raw)
        start, end = (pos, pos + len(raw)) if pos >= 0 else (0, 0)
        cursor = max(cursor, end)
        out.append(Candidate(AssertionClass.FIGURE, raw, start, end, "digits", val))
        seen.add(val)
    for v in _figures(text or ""):
        if v not in seen:
            out.append(Candidate(AssertionClass.FIGURE, v, 0, 0, "words", v))
    return out


# ---------------------------------------------------------------------------
# CODED_DESCRIPTOR
# ---------------------------------------------------------------------------
_CODE_RX = re.compile(
    r"\b(?P<system>CPT|HCPCS|CARC|RARC|ICD(?:-?10)?(?:-CM)?|NDC|APC)\b\s*(?:code)?\s*[:#]?\s*"
    r"(?P<code>[A-Z]{0,2}\d{3,5}[A-Z0-9]?|[A-Z]{1,2}-\d{1,3}|[A-Z]\d{2}(?:\.\d{1,4})?|\d{4,5}-\d{3,4}-\d{1,2}|\d{11})"
    r"\s*(?:[—–:\-]|\(|,)\s*(?P<desc>[^.\n()]{4,90})",
)


# CARC/RARC codes are written bare -- "CO-16 (missing information)" -- so the
# system prefix is optional for that shape.
_CARC_RX = re.compile(r"\b(?P<code>(?:CO|PR|OA|PI|CR)-\d{1,3}|[MN]\d{2,3}|MA\d{2,3})\b\s*(?:\(|[—–:\-])\s*(?P<desc>[^.\n()]{4,90})")


def extract_coded_descriptors(text: str) -> list[Candidate]:
    out = []
    for m in _CARC_RX.finditer(text or ""):
        out.append(Candidate(AssertionClass.CODED_DESCRIPTOR, m.group(0), m.start(), m.end(),
                             "CARC", m.group("code"), m.group("desc").strip()))
    for m in _CODE_RX.finditer(text or ""):
        sysname = m.group("system").upper().replace("-", "")
        if sysname.startswith("ICD"):
            sysname = "ICD10"
        out.append(Candidate(AssertionClass.CODED_DESCRIPTOR, m.group(0), m.start(), m.end(),
                             sysname, m.group("code"), m.group("desc").strip()))
    return _dedupe(out)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# LEGAL_REGISTER -- APPEALS-3 (Fred's ruling 2026-09-17). A letter argues on
# evidence; it does not speak as counsel. The citation gate catches section
# numbers and named statutes; it never caught "material breach", "we demand",
# "reserves the right", "without regulatory basis" -- the register that made
# ten letters read as if drafted by a lawyer while citing nothing. This is a
# phrase lexicon, reviewed, small. Every entry is a refusal wherever the class
# is gated; there is no binding that can rescue it. The regression corpus is
# the exact strings quoted in the APPEALS-1 audit (tests/verify/test_legal_register.py).
# Deliberately NOT here: "appeal", "external review", "appeal rights", "medical
# policy", "criteria" -- a letter may repeat what the payer's own letter says.
# ---------------------------------------------------------------------------
LEGAL_REGISTER_LEXICON = {
    # law as such
    "statute":            r"\bstatut(?:e|es|ory|orily)\b",
    "regulation":         r"\bregulat(?:ion|ions|ory)\b",
    "case_law":           r"\bcase law\b|\bprecedent\b",
    "under_applicable":   r"\bunder the applicable\b|\bapplicable (?:state|federal)\b",
    # "under denial code CO-97" / "under the CPT code" are claim facts, not law: the nouns
    # here are law-nouns only; code SECTIONS are the citation gate's business.
    "under_law":          r"\b(?:under|pursuant to|in accordance with|as required by|consistent with)\b[^.\n]{0,60}\b(?:law|laws|statute|statutes|regulation|regulations|rule|rules|act)\b",
    "fed_state_law":      r"\b(?:federal|state)(?: and (?:federal|state))? law\b",
    "legal_word":         r"\blegal(?:ly)?\b|\bunlawful(?:ly)?\b|\blegislat\w*",
    "counsel":            r"\battorney(?:s|-grade)?\b|\blegal counsel\b|\bcounsel\b|\blawyer\b|\blitigat\w*|\blawsuit\b",
    # obligation / breach / threat
    # an obligation laid on the payer ("the plan is required to", "you are obligated to"),
    # not "the note is required to include" -- a documentation statement
    "required_to":        r"\b(?:payer|plan|insurer|carrier|you|they|health plan|[A-Z][A-Za-z]+ Health Plan)\s+(?:is|are|was|were)\s+(?:legally\s+)?(?:required|obligated|obliged|bound)\s+to\b|\brequires? (?:payment|the payer|the plan|the insurer)\b",
    "violat":             r"\bviolat(?:e|es|ed|ing|ion|ions)\b|\bnon-?compliance\b|\bnoncompliant\b",
    "breach":             r"\bbreach(?:es|ed)?\b",
    "reserve_rights":     r"\breserv(?:e|es|ed|ing)\s+(?:all|the|its|our|their|any|every)?\s*(?:other\s+)?[^.\n]{0,40}\brights?\b",
    "demand":             r"\bdemand(?:s|ed|ing)?\b",
    "no_basis":           r"\bwithout (?:contractual|regulatory|legal|statutory)(?: or (?:contractual|regulatory|legal|statutory))? basis\b",
    "prompt_pay":         r"\bprompt[- ]pay(?:ment)?\b",
    "formal_constitutes": r"\bconstitutes? a formal\b",
    "corrective_action":  r"\bpursue (?:corrective|legal|further) action\b|\bcorrective action\b",
    "necessitate":        r"\bnecessitate\b",
    "grounds":            r"\b(?:not|no|without) (?:valid )?grounds\b|\bgrounds for denial\b",
    "rights_assert":      r"\b(?:exercis\w+|assert\w*|knows?|know) (?:its|their|our|his|her) rights?\b|\bright to appeal\b|\bentitled to\b",
    "regulator":          r"\bregulator\b|\binsurance commissioner\b|\bdepartment of insurance\b|\bstate insurance department\b",
    "complaint":          r"\b(?:file|filing|lodge|lodging) a complaint\b|\bcomplaint (?:to|with) (?:the )?(?:state|insurance|regulator)",
    "arbitration":        r"\barbitrat\w*",
    "fiduciary":          r"\bfiduciar(?:y|ies)\b|\bduty to\b|\bduties\b",
    "legal_basis":        r"\blegal/regulatory basis\b|\b(?:legal|regulatory|statutory) basis\b",
    "dispute_resolution": r"\bdispute resolution process\b",
}
_REGISTER_RX = {k: re.compile(v, re.I) for k, v in LEGAL_REGISTER_LEXICON.items()}


def extract_legal_register(text: str) -> list[Candidate]:
    out = []
    for term, rx in _REGISTER_RX.items():
        for m in rx.finditer(text or ""):
            out.append(Candidate(AssertionClass.LEGAL_REGISTER, m.group(0), m.start(), m.end(), term, term))
    return _dedupe(out)


# ---------------------------------------------------------------------------
# ENCLOSURE -- APPEALS-4 (2026-09-19). A letter must not assert an enclosure the
# pipeline does not produce. The provider pipeline returns a PDF of the letter
# and a list of documents for the PRACTICE to gather (attach_documentation); it
# holds and transmits none of them. The patient pipeline appends a code-built
# References list and nothing else. So "enclosed", "attached", "herewith",
# "accompanying" and "find included" are claims neither pipeline can satisfy,
# and every hit is refused. Referring to a document that is "on file with the
# payer", "in the practice's records" or "being submitted separately" is not an
# enclosure claim and does not match.
# ---------------------------------------------------------------------------
ENCLOSURE_LEXICON = {
    "enclosed":     r"\benclos(?:e|es|ed|ure|ures|ing)\b",
    "attached":     r"\battach(?:ed|ment|ments)\b(?! point)",
    "herewith":     r"\b(?:submitted|provided|included|sent|forwarded)\s+herewith\b|\bherewith\b",
    "accompanying": r"\baccompan(?:ies|ying|ied)\s+this\s+(?:letter|appeal|request)\b|\bthe\s+accompanying\s+(?:\w+\s+){0,3}(?:note|notes|record|records|report|reports|documentation|documents)\b",
    "find_included": r"\b(?:please\s+)?find\s+(?:included|enclosed|attached)\b|\bincluded\s+with\s+this\s+(?:letter|appeal|submission)\b|\b(?:is|are)\s+included\s+(?:below|herein|with)\b",
}
_ENCLOSURE_RX = {k: re.compile(v, re.I) for k, v in ENCLOSURE_LEXICON.items()}


def extract_enclosure(text: str) -> list[Candidate]:
    out = []
    for term, rx in _ENCLOSURE_RX.items():
        for m in rx.finditer(text or ""):
            out.append(Candidate(AssertionClass.ENCLOSURE, m.group(0), m.start(), m.end(), term, term))
    return _dedupe(out)


EXTRACTORS = {
    AssertionClass.LEGAL_REGISTER: extract_legal_register,
    AssertionClass.ENCLOSURE: extract_enclosure,
    AssertionClass.LEGAL_PROVISION: extract_legal,
    AssertionClass.IDENTIFIER: extract_identifiers,
    AssertionClass.NAMED_SOURCE: extract_named_sources,
    AssertionClass.FIGURE: extract_figures,
    AssertionClass.CODED_DESCRIPTOR: extract_coded_descriptors,
}


def extract(cls: AssertionClass, text: str) -> list[Candidate]:
    return EXTRACTORS[cls](text)


def _dedupe(cands: list[Candidate]) -> list[Candidate]:
    """Keep the longest match at each position (the citation gate's rule)."""
    keep = [c for c in cands if not any(o is not c and o.start <= c.start and c.end <= o.end
                                        and (o.end - o.start) > (c.end - c.start) for o in cands)]
    seen, out = set(), []
    for c in sorted(keep, key=lambda c: (c.start, -c.end, c.kind)):
        key = (c.start, c.end, c.kind)
        if key not in seen:
            seen.add(key); out.append(c)
    return out
