"""SUBJECT: does the supporting document contain the claim's distinguishing terms?

The binding that was missing. FIGURE, SPAN and CHRONOLOGY check a number, a
quotation and a date; a claim with none of the three -- "The UK General
Medical Council found that the Wakefield et al. research involved undisclosed
financial conflicts of interest ... data manipulation, and dishonesty" -- was
shown, levelled IDENTITY_ONLY, on a retraction notice that says nothing of the
kind. The operator found it on the live page (2026-09-15); a hand audit of
the other 67 IDENTITY_ONLY claims found 19 more of the same shape at two
magnitudes -- the document contains neither the claim's subject nor its
attribution. This is that audit as code.

WHAT IS EXTRACTED FROM THE CLAIM (never hand-authored per claim):
    named      capitalised tokens and acronyms -- bodies, persons, places,
               products ("General Medical Council", "Wakefield", "CHMP",
               "Yokohama", "M-M-R II") -- minus the source's own name (its
               first author, its title's words, its container) and topic
               boilerplate ("MMR", "ASD", "UK", "FDA" when it IS the source)
    quantity   prose quantities the figure binder does not see: "millions",
               "multiple countries", "substantially", "most"
    content    every other distinctive word of the claim: not boilerplate,
               not generic to the topic, not in the source's title, not a
               digit, longer than three letters -- "conflated", "leaky",
               "persistence", "outweigh", "syndrome", "clustering"

THE RULE: a named term or a prose quantity absent from the held text refuses
(a body or a number-word the document never mentions is an assertion the
document cannot support); otherwise the claim binds when at least
SUBJECT_MIN_PRESENT of its content terms are present and at most
SUBJECT_MAX_ABSENT are absent. Matching is by stem, against the held text
plus what the registry said (title, container, author, year), lower-cased.
Nothing here judges meaning; it asks whether the words that make this claim
THIS claim occur in the document at all. A claim that clears SUBJECT is
still not verified -- it is not contradicted by absence.
"""
from __future__ import annotations

import re

from .text import LITERATURE_BOILERPLATE, content_tokens, normalise_text as normalise
from .types import Binding, Document, Kind

# Words any claim on any topic may use to describe a study without saying
# anything distinctive about THIS study. Kept short and general on purpose:
# the source's own title, author and container are removed per source, not
# here, and a topic's own vocabulary ("autism", "vaccine") is removed by the
# caller through `topic_terms`.
GENERIC = {
    "study", "studies", "found", "finding", "findings", "evidence", "association", "associated", "risk", "risks",
    "children", "child", "cohort", "case", "control", "published", "research", "paper", "data", "rates", "rate",
    "increase", "increased", "increasing", "between", "after", "following", "link", "linked", "linking", "causal",
    "cause", "causes", "causing", "causation", "hypothesis", "analysis", "analyses", "results", "result",
    "reported", "report", "concluded", "conclusion", "conclusions", "large", "scale", "significant",
    "significantly", "statistically", "population", "based", "authors", "review", "reviewed", "systematic",
    "committee", "safety", "effect", "effects", "relationship", "outcome", "outcomes", "examined", "examine",
    "investigated", "assessed", "compared", "comparison", "group", "groups", "subgroup", "subgroups", "rest",
    "rests", "showed", "shows", "shown", "suggest", "suggests", "suggested", "indicate", "indicates", "consistent",
    "directly", "specifically", "specific", "overall", "including", "included", "across", "among", "within",
    "whether", "there", "their", "these", "those", "this", "that", "which", "were", "was", "been", "being",
    "have", "has", "had", "does", "did", "not", "than", "then", "also", "both", "such", "only", "even", "still",
    "further", "later", "earlier", "since", "before", "during", "while", "when", "where", "into", "onto", "over",
    "under", "about", "against", "through", "without", "toward", "towards", "rather", "instead", "however",
    "year", "years", "time", "period", "date", "day", "month", "months", "later", "first", "second", "original",
    "subsequent", "later", "new", "old", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
    "ten", "per", "cent", "percent",
    # verbs and adverbs of reporting, method and phrasing -- general English,
    # not subject matter; they count as content, never as distinguishing
    "detected", "detect", "observed", "observe", "considered", "consider", "having", "ruling", "ruled", "rule",
    "initiated", "initiate", "rejected", "reject", "carry", "carried", "citing", "cited", "cite", "creating",
    "created", "create", "spanning", "spanned", "regardless", "higher", "lower", "designed", "design", "designs",
    "established", "establish", "tested", "test", "proposed", "propose", "supported", "support", "supporting",
    "conducted", "conduct", "defined", "define", "determined", "demonstrated", "indicated", "remained",
    "resulting", "resulted", "dropped", "dropping", "continued", "continue", "discontinued", "declined",
    "withdrew", "withdrawn", "held", "held", "addressing", "addressed", "reflecting", "reflected", "convened",
    "granted", "published", "described", "characterized", "characterised", "attributed", "identified", "identifying",
    "directed", "focus", "actual", "future", "provided", "applying", "applied", "recommended", "concluding",
    "removed", "constituted", "contradicting", "contradicted", "disproving", "disproved", "substantiated",
    "representing", "informed", "inform", "involved", "formally", "specifically", "directly", "consistently",
    "convincingly", "strongly", "substantially",
}
# (c) THE REPORTING / PARAPHRASE CLASS -- words that describe the act of
# studying, reporting or presenting rather than what was studied. Derived: a
# base list of verb stems x their inflections, plus adjectives of assessment
# and nouns of presentation. A word in this class counts as neither content
# nor distinguishing; the check asks about the subject, not the verb the
# summariser chose.
_REPORTING_STEMS = [
    "analy", "synthesi", "indicat", "show", "involv", "reaffirm", "examin", "conduct", "conclud", "report", "note",
    "describ", "represent", "assess", "investigat", "evaluat", "compar", "review", "demonstrat", "suggest", "find",
    "found", "observ", "identif", "confirm", "establish", "determin", "estimat", "measur", "calculat", "test", "stud",
    "address", "highlight", "emphasi", "argu", "claim", "state", "propos", "present", "publish", "cit", "document",
    "discuss", "consider", "characteri", "defin", "includ", "cover", "span", "follow", "track", "monitor", "revisit",
    "updat", "reiterat", "recommend", "advis", "urg", "call", "detect", "rule", "initiat", "reject", "carry", "creat",
    "design", "provid", "apply", "appli", "direct", "focus", "grant", "conven", "attribut", "remov", "constitut",
    "contradict", "disprov", "substantiat", "inform", "involv", "reflect", "enrol", "recruit", "surve", "sampl",
    "pool", "adjust", "control", "match", "link", "record", "collect", "obtain", "select", "restrict", "stratif",
    "sugges", "explain", "account", "reveal", "assert", "affirm", "deny", "dispute", "question", "challeng", "support",
    "contain", "hold", "regard", "restat", "reword", "summari", "interpret", "read", "mean", "imply", "infer",
]
_INFLECTIONS = ["", "e", "s", "es", "ed", "ing", "ings", "ation", "ations", "er", "ers", "ment", "ments", "ive", "ively", "ingly", "edly", "y", "ies", "ied", "d", "ze", "zed", "zes", "zing", "se", "sed", "ses", "sing", "sis", "ses", "tic", "tical", "tically"]
_ASSESSMENT = {"credible", "robust", "rigorous", "notable", "clear", "clearly", "consistent", "consistently", "convincing",
               "convincingly", "compelling", "strong", "strongly", "weak", "weakly", "reliable", "definitive", "authoritative",
               "comprehensive", "thorough", "landmark", "seminal", "influential", "widely", "broadly", "generally", "largely",
               "directly", "specifically", "explicitly", "formally", "actual", "actually", "novel", "sudden", "null", "similar",
               "similarly", "elevated", "higher", "lower", "greater", "smaller", "increased", "decreased", "reduced", "either",
               "both", "any", "various", "different", "same", "certain", "particular", "possible", "likely", "unlikely", "true",
               "false", "correct", "incorrect", "valid", "invalid"}
_PRESENTATION_NOUNS = {"timeline", "timelines", "narrative", "narratives", "account", "accounts", "description", "descriptions",
                       "summary", "summaries", "wording", "phrasing", "language", "terms", "version", "versions", "history",
                       "histories", "record", "records", "finding", "findings", "result", "results", "conclusion", "conclusions",
                       "evidence", "data", "analysis", "analyses", "approach", "approaches", "method", "methods", "design", "designs"}


def _reporting_class() -> set[str]:
    out = set(_ASSESSMENT) | set(_PRESENTATION_NOUNS)
    for stem in _REPORTING_STEMS:
        for inf in _INFLECTIONS:
            out.add(stem + inf)
    return out


REPORTING = _reporting_class()

# Prose quantities and intensifiers that characterise a claim without a digit.
QUANTITY = {
    "millions", "million", "thousands", "thousand", "hundreds", "hundred", "dozens", "billions",
    "multiple", "several", "numerous", "many", "most", "majority", "all", "every", "none", "no",
    "substantially", "strongly", "vast", "overwhelming", "comprehensive", "largest", "strongest", "authoritative",
}
# Tokens that look like names but are the topic's or the field's furniture.
NAME_BOILERPLATE = {"MMR", "ASD", "PDD", "UK", "US", "USA", "EU", "DOI", "CI", "HR", "RR", "OR", "The", "This", "These",
                    "In", "It", "Its", "No", "A", "An", "After", "Among", "When", "Following", "Because", "Both", "Multiple",
                    "Serious", "Anti", "Danish", "Denmark", "Japanese", "Japan", "British", "English", "European", "American"}
# (b) Statistical vocabulary: abbreviation <-> expansion, a table like the
# institutional aliases -- no inference. Applied by EXPANDING the abbreviation
# in both the claim and the document before matching (case-sensitive on the
# raw text, so "or" the conjunction is untouched and "OR" the statistic is).
STAT_ABBREVIATIONS = {
    "OR": "odds ratio", "aOR": "adjusted odds ratio", "RR": "relative risk", "aRR": "adjusted relative risk",
    "HR": "hazard ratio", "aHR": "adjusted hazard ratio", "CI": "confidence interval", "IRR": "incidence rate ratio",
    "PRR": "proportional reporting ratio", "SMR": "standardized mortality ratio", "RCT": "randomised controlled trial",
    "RCTs": "randomised controlled trials", "SCCS": "self-controlled case series", "ITS": "interrupted time series",
    "PDD": "pervasive developmental disorder", "ASD": "autism spectrum disorder", "MDE": "major depressive episode",
    "NNT": "number needed to treat", "SD": "standard deviation", "SE": "standard error", "PY": "person-years",
}
_STAT_RX = re.compile(r"(?<![\w-])(" + "|".join(sorted(map(re.escape, STAT_ABBREVIATIONS), key=len, reverse=True)) + r")(?![\w-])")


def expand_abbreviations(text: str) -> str:
    """'OR 0.92 (95% CI ...)' -> 'OR odds ratio 0.92 (95% CI confidence interval ...)': the
    abbreviation is kept and its expansion added, so either form matches."""
    return _STAT_RX.sub(lambda m: m.group(1) + " " + STAT_ABBREVIATIONS[m.group(1)], text or "")


# (a) Number-word equivalence: a scale word in the claim ("million") is
# satisfied by a digit string of that magnitude in the document, grouped by
# space, thin space or comma ("23 480 668", "23,480,668"), with the same
# tolerance the figure binder applies -- it is the figure binder that decides
# whether 23 million is 23,480,668; here the question is only whether the
# document counts in millions at all.
SCALE_WORDS = {"thousand": 10 ** 3, "thousands": 10 ** 3, "million": 10 ** 6, "millions": 10 ** 6, "billion": 10 ** 9, "billions": 10 ** 9}


def _scale_satisfied(word: str, raw_text: str) -> bool:
    from .numbers import canonical_numbers
    floor = SCALE_WORDS[word]
    for n in canonical_numbers(raw_text):
        try:
            if abs(float(n)) >= floor:
                return True
        except ValueError:
            continue
    return False


SUBJECT_MIN_PRESENT = 0.5      # share of content terms that must be present
SUBJECT_MAX_ABSENT = 3         # and at most this many absent
# A distinguishing term is one that occurs in at most this many of the topic's
# claims: it is what makes the claim THIS claim, and its absence from the
# document refuses on its own ("preterm", "attenuated", "conflated").
DISTINGUISHING_MAX_CLAIMS = 2
DISTINGUISHING_MAX_DOCS = int(__import__("os").environ.get("DISTDOCS", 2))
# Institutional and geographic aliases -- an acronym in the claim against the
# name in the document, or the reverse. Static and general; not per claim.
ALIASES = {
    "iom": ["institute of medicine"], "cdc": ["centers for disease control"], "fda": ["food and drug administration"],
    "gmc": ["general medical council"], "ema": ["european medicines agency"], "chmp": ["committee for medicinal products"],
    "acip": ["advisory committee on immunization practices"], "vaers": ["vaccine adverse event reporting system"],
    "nejm": ["new england journal of medicine"], "bmj": ["british medical journal"], "who": ["world health organization"],
    "united kingdom": ["uk", "britain", "england"], "united states": ["us", "usa", "america"],
    "spectrum": ["asd"], "autism spectrum disorder": ["asd"], "autism": ["asd", "pervasive developmental disorder", "autistic"],
    "institute of medicine": ["iom"], "general medical council": ["gmc"], "european medicines agency": ["ema"],
    "centers for disease control": ["cdc"], "food and drug administration": ["fda"],
}


def _stem(w: str) -> str:
    for suf in ("ations", "ation", "ingly", "ing", "edly", "ed", "ies", "ers", "er", "es", "s", "ly", "al", "ity"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def _word_present(w: str, text: str) -> bool:
    """A word is present by itself, by stem ("received" ~ "receipt" via
    "recei"), or with a negating prefix removed ("unvaccinated" ~ "vaccinated")."""
    if w in text or _stem(w) in text:
        return True
    if len(w) >= 8 and w[:6] in text:
        return True
    for pre in ("un", "non", "in", "im"):
        if w.startswith(pre) and len(w) - len(pre) >= 5 and _stem(w[len(pre):]) in text:
            return True
    return False


def _present(term: str, text: str) -> bool:
    t = normalise(term).strip()
    if not t:
        return True
    if t in text:
        return True
    for alias in ALIASES.get(t, []):
        if re.search(r"\b" + re.escape(alias) + r"\b", text):
            return True
    return all(_word_present(w, text) for w in t.split())


_NAME_RUN = re.compile(r"(?:[A-Z][\w'’-]*|M-M-R)(?:\s+(?:(?:of|the|and|for|on|in|&)\s+)?(?:[A-Z][\w'’-]*|II\b))*")


def named_terms(assertion: str) -> list[str]:
    """Capitalised runs -- "General Medical Council", "Institute of Medicine",
    "Wakefield", "CHMP", "M-M-R II" -- minus boilerplate and a sentence-initial
    common word. Each run is one phrase; matching accepts the phrase, an
    alias, or every one of its words."""
    text = assertion or ""
    sentence_starts = {m.group(1) for m in re.finditer(r"(?:^|[.!?]\s+)([A-Z][\w\-'’]*)", text)}
    out = []
    for m in _NAME_RUN.finditer(text):
        run = re.sub(r"['’]s\b", "", m.group(0)).strip(" -")
        toks = [t for t in re.split(r"\s+", run) if t and t not in ("of", "the", "and", "for", "&", "on", "in")]
        toks = [t for t in toks if t not in NAME_BOILERPLATE and not re.fullmatch(r"[A-Z][a-z]{0,2}", t)]
        toks = [t for t in toks if not re.fullmatch(r"(?:MMR|ASD|UK|US)-[a-z]+", t)]     # "MMR-autism": topic words, not a name
        if toks and toks[0] in sentence_starts and not toks[0].isupper() and text.count(toks[0]) == 1 and len(toks) == 1:
            continue
        if toks:
            out.append(" ".join(toks))
    seen, uniq = set(), []
    for t in out:
        if t.lower() not in seen:
            seen.add(t.lower()); uniq.append(t)
    return uniq


def extract_terms(assertion: str, source_words: set[str], topic_terms: set[str],
                  claim_frequency: dict[str, int] | None = None, document_frequency: dict[str, int] | None = None) -> dict:
    """{'named', 'quantity', 'content', 'distinguishing'} from the claim. The
    source's own name (author, title, container) is removed from the NAMED
    terms -- a claim naming its own source proves nothing -- but not from the
    content terms, whose test is presence in the text. `claim_frequency` is
    how many of the topic's claims each normalised word occurs in; a content
    word at or under DISTINGUISHING_MAX_CLAIMS is distinguishing."""
    src = {normalise(w) for w in source_words} | {_stem(normalise(w)) for w in source_words}
    topic = {normalise(w) for w in topic_terms} | {_stem(normalise(w)) for w in topic_terms}
    named = [n for n in named_terms(assertion) if normalise(n) not in src and _stem(normalise(n)) not in src and normalise(n) not in topic]
    words = normalise(assertion).split()
    quantity = [w for w in words if w in QUANTITY and w not in ("no", "all", "none", "every", "many", "most")]   # negation/quantifier words too common to be evidence
    content = []
    for w in content_tokens(expand_abbreviations(assertion), LITERATURE_BOILERPLATE):
        if w in GENERIC or w in QUANTITY or w in REPORTING or w.isdigit() or len(w) <= 3:
            continue
        if w in topic or _stem(w) in topic:
            continue
        if any(w == normalise(n) or w in normalise(n).split() for n in named_terms(assertion)):
            continue
        content.append(w)
    # Distinguishing: rare among the topic's claims AND rare across the topic's
    # held documents. A word many documents use ("assess", "reduced", "million")
    # is general vocabulary whatever one claim does with it; a word almost no
    # document uses ("preterm", "conflated", "leaky") is what makes the claim
    # this claim, and its absence from the one document that should carry it
    # refuses on its own.
    freq = claim_frequency or {}; dfreq = document_frequency or {}
    distinguishing = sorted(w for w in set(content)
                            if freq and freq.get(w, 0) <= DISTINGUISHING_MAX_CLAIMS
                            and (not dfreq or dfreq.get(_stem(w), dfreq.get(w, 0)) <= DISTINGUISHING_MAX_DOCS)
                            and w not in src)
    # the source's own title words are content the document trivially contains;
    # the SHARE is judged over the rest, or a claim that restates a title's
    # subject and adds one absent predicate would still pass on the title
    own = sorted(w for w in set(content) if w in src or _stem(w) in src)
    return {"named": named, "quantity": sorted(set(quantity)), "content": sorted(set(content)),
            "distinguishing": distinguishing, "own": own}


def document_frequency(texts: list[str]) -> dict[str, int]:
    """stem -> number of documents whose text contains it. Computed once per
    topic over the surviving documents' held text."""
    out: dict[str, int] = {}
    for t in texts:
        stems = {_stem(w) for w in set(normalise(t).split()) if len(w) > 3}
        for st in stems:
            out[st] = out.get(st, 0) + 1
    return out


def bind_subject(assertion: str, document: Document, source_words: set[str], topic_terms: set[str],
                 registry_text: str = "", claim_frequency: dict[str, int] | None = None,
                 doc_frequency: dict[str, int] | None = None, subject_terms: set[str] | None = None) -> Binding:
    """Are the claim's distinguishing terms in the document's held text?

    `topic_terms`: the topic's frequent vocabulary, exempt from the content
    count. `subject_terms`: the topic's subject itself (its title's words --
    "autism", "vaccine"); a document that never mentions one the claim uses
    cannot support the claim."""
    if document is None or document.text_layer != "DECLARED_SOUND":
        return Binding(Kind.SUBJECT, False, reason="no held text to check the claim's subject against")
    terms = extract_terms(assertion, source_words, topic_terms, claim_frequency, doc_frequency)
    raw = (document.text or "") + " " + (registry_text or "")
    text = normalise(expand_abbreviations(raw))
    # The topic's own vocabulary is exempt from the content count because every
    # claim uses it -- but a document that never mentions it at all cannot
    # support a claim about it (the EMA's M-M-RVaxPro page, 19k characters,
    # zero occurrences of "autism", 2026-09-15).
    claim_words = set(normalise(assertion).split())
    missing_topic = sorted(w for w in (subject_terms or set()) if normalise(w) in claim_words and len(normalise(w)) > 3
                           and not _present(normalise(w), text))
    missing_named = [n for n in terms["named"] if not _present(n, text)]
    missing_qty = [q for q in terms["quantity"]
                   if not _present(q, text) and not (q in SCALE_WORDS and _scale_satisfied(q, raw))]
    present = [w for w in terms["content"] if _present(w, text)]
    absent = [w for w in terms["content"] if w not in present]
    missing_dist = [w for w in terms["distinguishing"] if w in absent]
    beyond = [w for w in terms["content"] if w not in terms["own"]]          # words beyond the source's own subject
    present_beyond = [w for w in beyond if w in present]
    total = len(beyond)
    share = (len(present_beyond) / total) if total else 1.0
    evidence = f"named {len(terms['named']) - len(missing_named)}/{len(terms['named'])}, quantity {len(terms['quantity']) - len(missing_qty)}/{len(terms['quantity'])}, content beyond the source's own subject {len(present_beyond)}/{total}, distinguishing {len(terms['distinguishing']) - len(missing_dist)}/{len(terms['distinguishing'])}"
    if missing_topic:
        return Binding(Kind.SUBJECT, False, evidence=evidence,
                       reason="the document never mentions the claim's subject: " + ", ".join(missing_topic))
    if missing_named or missing_qty or missing_dist:
        return Binding(Kind.SUBJECT, False, evidence=evidence,
                       reason="not in the document: " + ", ".join(dict.fromkeys(missing_named + missing_qty + missing_dist)) + (f" (also absent: {', '.join(w for w in absent if w not in missing_dist)[:120]})" if [w for w in absent if w not in missing_dist] else ""))
    absent_beyond = [w for w in beyond if w not in present]
    # with one or two words beyond the source's own subject, every one must be
    # present: "removed the primary published basis" is one assertion, and
    # half of it is not a match
    if total and (share < SUBJECT_MIN_PRESENT or len(absent_beyond) > SUBJECT_MAX_ABSENT or (total <= 2 and absent_beyond)):
        return Binding(Kind.SUBJECT, False, evidence=evidence,
                       reason=f"the claim's distinguishing words are mostly not in the document: absent {', '.join(absent_beyond[:8])}")
    if not terms["named"] and not terms["quantity"] and not terms["content"]:
        return Binding(Kind.SUBJECT, False, abstained=True, evidence=evidence,
                       reason="the claim has no distinguishing term beyond its source's own name; nothing to match")
    return Binding(Kind.SUBJECT, True, evidence=evidence + (f"; absent: {', '.join(absent)}" if absent else ""))
