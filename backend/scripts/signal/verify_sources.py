"""Does every source in the Signal corpus point at a document that exists?

WHY THIS EXISTS
---------------
On 2026-08-31, adjudicating a consensus label, two claims appeared to
contradict each other about whether alcohol's effect on breast cancer risk is
hormone-receptor specific. Reading the sources dissolved the contradiction and
found something worse.

  1. Both DOIs were wrong. One resolved to a paper on lipid nanoparticles in
     prostate cancer; the other to a journal's editorial board page.
  2. Resolving all 220 DOIs in the corpus: 46% correct, 27% pointing at a
     DIFFERENT paper, 27% not existing at all. 54% bad. In
     breast-cancer-therapies -- the corpus behind What Holds Up issue two --
     14 of 15.
  3. And the cause: 380 of 381 sources have never had their real content
     fetched. `content_text` holds a model-written summary, median 473
     characters. Every claim in Signal was extracted from those summaries
     rather than from the documents.

That last one explains all the rest. A 473-character summary does not contain
a hazard ratio, a confidence interval, or a subgroup breakdown -- so when
extraction was asked for claims at that level of detail, the figures were
invented. PALOMA-3's "p=0.0221" (the real analysis reports P=0.09) and EPIC's
"stronger for hormone receptor-positive tumors" (the real paper concludes the
association holds in BOTH) are the same error, not two errors.

THE PART THAT MATTERS FOR HOW WE BUILD
--------------------------------------
collect_sources.py ALREADY KNEW HOW TO CHECK. _fetch_doi_metadata() calls the
exact CrossRef endpoint this script calls. It ran. For a fabricated DOI it
returned nothing, printed "No content fetched, using summary", fell back to
the model's own text, and stored the row. The capability existed, the check
executed, it failed, and the failure was handled by substituting fiction and
carrying on.

A warning that does not block is not a control. That is the whole lesson, and
it is why this script EXITS NONZERO rather than printing advice.

WHAT IT CHECKS -- all deterministic, no model, no drift, no API cost
--------------------------------------------------------------------
  PROVENANCE  Was content_text actually fetched, or is it a model summary?
              Free, offline, needs no network, and would have caught this on
              day one.
  EXISTS      Does the DOI / NCT / PMID resolve at all?
  IDENTITY    Does the registered title match the title we display?

Usage:
    python scripts/signal/verify_sources.py --offline   # provenance only, seconds
    python scripts/signal/verify_sources.py             # full check
    python scripts/signal/verify_sources.py --slug glp1-drugs
    python scripts/signal/verify_sources.py --json out.json
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import map_consensus as mc

UA = {"User-Agent": "civicscale-source-verification"}
# Zero shared distinctive words means a different document. Some overlap but
# little means our title is a paraphrase worth a human look, not a fabrication.
TITLE_DIFFERENT_DOCUMENT = 0.0
TITLE_DIVERGENT_BELOW = 0.25

# A fetched source carries the shape of the thing it was fetched from.
# _fetch_doi_metadata() builds "Title: ...\nAuthors: ...", the ClinicalTrials
# fetcher emits the registry's own field names, and an HTML fetch runs long.
# A model summary is a few hundred characters of prose and matches none of it.
FETCHED_PREFIXES = ("Title:", "Authors:", "Journal:")
FETCHED_MARKERS = ("Brief Title:", "Official Title:", "Primary Outcome",
                   "Eligibility Criteria", "Study Type:")
LONG_ENOUGH_TO_BE_REAL = 6000


def _get(url: str, timeout: int = 25) -> str | None:
    try:
        return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout).read()
    except Exception:
        return None


def normalise(s: str | None) -> str:
    s = re.sub(r"<[^>]+>", "", s or "")
    s = re.sub(r"[^a-z0-9 ]", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def identifier(url: str | None) -> tuple[str, str] | None:
    """(kind, value) for a resolvable identifier, or None."""
    if not url:
        return None
    u = url.strip()
    if "doi.org/" in u:
        return ("doi", u.split("doi.org/")[-1].strip().rstrip("/"))
    m = re.search(r"(NCT\d{8})", u, re.I)
    if m:
        return ("nct", m.group(1).upper())
    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", u)
    if m:
        return ("pmid", m.group(1))
    return None


def provenance(content_text: str | None) -> str:
    """Where did the text the claims were extracted from come from?"""
    ct = (content_text or "").strip()
    if not ct:
        return "EMPTY"
    if ct.startswith(FETCHED_PREFIXES) or any(k in ct[:600] for k in FETCHED_MARKERS):
        return "FETCHED"
    if len(ct) > LONG_ENOUGH_TO_BE_REAL:
        return "FETCHED"
    return "MODEL_SUMMARY"


# Words that appear in nearly every trial or paper title and identify nothing.
BOILERPLATE = {
    "a", "an", "the", "of", "in", "for", "with", "and", "or", "to", "on", "at",
    "vs", "versus", "plus", "study", "trial", "phase", "randomized", "randomised",
    "double", "blind", "blinded", "placebo", "controlled", "multicenter",
    "multicentre", "open", "label", "active", "evaluate", "evaluation", "test",
    "investigational", "patients", "participants", "adults", "subjects", "efficacy",
    "safety", "comparing", "compared", "comparison", "treatment", "therapy", "first",
    "second", "line", "i", "ii", "iii", "iv", "1", "2", "3", "4", "who", "have",
    "as", "after", "before", "using", "use", "assessment", "analysis", "effect",
    "effects", "outcomes", "results", "review", "systematic",
}


def content_tokens(s: str) -> set[str]:
    return {w for w in normalise(s).split() if w not in BOILERPLATE and len(w) > 2}


def title_agreement(ours: str, registered: str) -> float:
    """How far our displayed title and the registry's agree, 0.0 to 1.0.

    `registered` may hold several alternatives joined by ' || '.

    THIS IS THE SECOND VERSION AND THE FIRST ONE WAS WRONG IN THE WAY THAT
    MATTERS. Sequence similarity against a registry's official title scored
    MONARCH 3, DESTINY-Breast01, -02, -03 and KEYNOTE-522 as WRONG DOCUMENT
    when every one was the correct trial. Registries store formal
    descriptions -- "A Phase 3, Multicenter, Randomized, Open-label,
    Active-controlled Study of DS-8201a..." -- and we store the name people
    use. Those share almost no character sequence and refer to the same study.

    A check that cries wolf gets switched off, which is precisely the failure
    this file exists to prevent. So identity is judged on DISTINCTIVE CONTENT
    WORDS, with trial boilerplate stripped. DESTINY-Breast01 and its registry
    entry share metastatic/breast/cancer/trastuzumab; PALOMA-1 and the
    electroporation-device study it actually points to share nothing at all.
    That is the difference the check has to see, and it is the only one it
    claims to.
    """
    a = normalise(ours)
    ta = content_tokens(ours)
    best = 0.0
    for cand in (registered or "").split(" || "):
        b = normalise(cand)
        if not b:
            continue
        if a and b and (a in b or b in a or
                        a.replace(" ", "") in b.replace(" ", "") or
                        b.replace(" ", "") in a.replace(" ", "")):
            return 1.0
        tb = content_tokens(cand)
        if ta and tb:
            best = max(best, len(ta & tb) / min(len(ta), len(tb)))
    return round(best, 3)


def resolve(kind: str, value: str) -> tuple[str, str | None]:
    """(status, registered_title). status is EXISTS, NONEXISTENT or UNCHECKED."""
    if kind == "doi":
        # The Handle System covers every registration agency, not just
        # CrossRef -- checked before trusting a 404, so a DataCite-registered
        # DOI is never reported as fabricated.
        h = _get("https://doi.org/api/handles/" + urllib.parse.quote(value))
        if not h:
            return ("NONEXISTENT", None)
        try:
            if json.loads(h).get("responseCode") != 1:
                return ("NONEXISTENT", None)
        except Exception:
            return ("UNCHECKED", None)
        meta = _get("https://api.crossref.org/works/" + urllib.parse.quote(value))
        if not meta:
            return ("EXISTS", None)
        try:
            return ("EXISTS", (json.loads(meta)["message"].get("title") or [None])[0])
        except Exception:
            return ("EXISTS", None)

    if kind == "nct":
        raw = _get(f"https://clinicaltrials.gov/api/v2/studies/{value}"
                   "?fields=protocolSection.identificationModule")
        if not raw:
            return ("NONEXISTENT", None)
        try:
            idm = json.loads(raw)["protocolSection"]["identificationModule"]
        except Exception:
            return ("EXISTS", None)
        # THREE titles, not one. A registry official title is a formal
        # description -- "A Randomized, Double-Blind, Placebo-Controlled,
        # Phase 3 Study of Nonsteroidal Aromatase..." -- while we store the
        # name people use, "MONARCH 3". Comparing ours to the official title
        # alone scored MONARCH 3, DESTINY-Breast01, -02 and -03 as WRONG
        # DOCUMENT when all four were correct. A check that cries wolf gets
        # switched off, which is the failure this whole exercise is about.
        # The acronym is what actually identifies the trial to a reader.
        cands = [idm.get("officialTitle"), idm.get("briefTitle"), idm.get("acronym")]
        return ("EXISTS", " || ".join(c for c in cands if c) or None)

    if kind == "pmid":
        raw = _get("https://www.ebi.ac.uk/europepmc/webservices/rest/search?query="
                   + urllib.parse.quote(f"EXT_ID:{value}") + "&format=json&pageSize=1&resultType=core")
        if not raw:
            return ("UNCHECKED", None)
        try:
            res = json.loads(raw).get("resultList", {}).get("result", [])
            return ("EXISTS", res[0].get("title")) if res else ("NONEXISTENT", None)
        except Exception:
            return ("UNCHECKED", None)

    return ("UNCHECKED", None)


def check(rows: list[dict], offline: bool, pause: float = 0.12) -> list[dict]:
    out = []
    for i, r in enumerate(rows, 1):
        rec = {
            "id": r["id"], "slug": r["slug"], "title": r["title"], "url": r.get("url"),
            "provenance": provenance(r.get("content_text")),
            "identifier": None, "exists": None, "registered_title": None,
            "title_ratio": None, "verdict": None,
        }
        ident = identifier(r.get("url"))
        if ident:
            rec["identifier"] = f"{ident[0]}:{ident[1]}"

        if offline or not ident:
            rec["exists"] = "SKIPPED" if offline else "NO_IDENTIFIER"
        else:
            status, reg = resolve(*ident)
            rec["exists"] = status
            rec["registered_title"] = reg
            if reg:
                rec["title_ratio"] = title_agreement(r["title"], reg)
            time.sleep(pause)

        # Worst finding wins. A source whose text was never fetched is
        # unusable whatever its DOI does, because the claims did not come
        # from the document either way.
        if rec["exists"] == "NONEXISTENT":
            rec["verdict"] = "FABRICATED_IDENTIFIER"
        elif rec["title_ratio"] is not None and rec["title_ratio"] <= TITLE_DIFFERENT_DOCUMENT:
            rec["verdict"] = "WRONG_DOCUMENT"
        elif (rec["title_ratio"] is not None
              and rec["title_ratio"] < TITLE_DIVERGENT_BELOW
              and rec["provenance"] != "MODEL_SUMMARY"):
            rec["verdict"] = "TITLE_DIVERGENT"
        elif rec["provenance"] == "MODEL_SUMMARY":
            rec["verdict"] = "NEVER_FETCHED"
        elif rec["provenance"] == "EMPTY":
            rec["verdict"] = "NO_CONTENT"
        elif rec["exists"] == "NO_IDENTIFIER":
            rec["verdict"] = "UNVERIFIABLE_URL"
        else:
            rec["verdict"] = "OK"
        out.append(rec)
        if i % 25 == 0:
            print(f"  ...{i}/{len(rows)}", flush=True)
    return out


FAILING = {"FABRICATED_IDENTIFIER", "WRONG_DOCUMENT", "NEVER_FETCHED",
           "NO_CONTENT", "UNVERIFIABLE_URL"}

BACKEND = Path(__file__).resolve().parents[2]
PUBLISHED = BACKEND / "data" / "verify" / "published"


def published_problems(slug: str, source_ids: set[str],
                       root: Path = PUBLISHED, backend: Path = BACKEND) -> list[str]:
    """What is wrong with a PUBLISHED topic's sources, judged by its publish record.

    A published topic's corpus rows still hold the model summaries the claims
    were extracted from -- the corpus is frozen, so the row check above calls
    every one of them NEVER_FETCHED. What a reader sees is governed by the
    publish record instead: publish_topic.py resolved each source itself,
    fetched the document, kept it under data/verify/docs, and withheld every
    claim it could not bind to that text. So for a published topic the
    question is whether the record still covers it:

      - a record exists (latest.json);
      - every source the record lets survive has a held document on disk;
      - the corpus has not changed since the record (a source added or
        removed after publishing was never gated).

    Returns a list of problems; empty means the record covers the topic.
    """
    rec_path = root / slug / "latest.json"
    if not rec_path.exists():
        shown = rec_path.relative_to(backend) if rec_path.is_relative_to(backend) else rec_path
        return [f"no publish record at {shown}"]
    try:
        rec = json.loads(rec_path.read_text(encoding="utf-8"))
    except Exception as exc:  # unreadable record is a failure, not a pass
        return [f"publish record unreadable: {exc}"]
    problems = []
    recorded = {s.get("source_id") for s in rec.get("sources", [])}
    for s in rec.get("sources", []):
        if not s.get("survives"):
            continue
        doc = s.get("document") or {}
        path = doc.get("path")
        if not path or not (backend / path).exists():
            problems.append(f"surviving source {str(s.get('source_id'))[:8]} has no held "
                            f"document ({path or 'no path in record'})")
    added = source_ids - recorded
    removed = recorded - source_ids
    if added:
        problems.append(f"{len(added)} corpus source(s) not in the publish record "
                        f"(added after publishing, never gated): "
                        + ", ".join(sorted(x[:8] for x in added)))
    if removed:
        problems.append(f"{len(removed)} recorded source(s) no longer in the corpus: "
                        + ", ".join(sorted(str(x)[:8] for x in removed)))
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--offline", action="store_true",
                    help="Provenance only. No network, no API calls, runs in seconds. "
                         "This alone would have caught the 2026-08-31 finding.")
    ap.add_argument("--slug", help="One topic only")
    ap.add_argument("--json", help="Write the full per-source result to this path")
    args = ap.parse_args()

    sb = mc._get_supabase()
    issues = sb.table("signal_issues").select("id,slug,status").execute().data or []
    iss = {r["id"]: r["slug"] for r in issues}
    published = {r["slug"] for r in issues if r.get("status") == "published"}
    raw = sb.table("signal_sources").select("id,issue_id,title,url,content_text").execute().data or []
    rows = [{**r, "slug": iss.get(r["issue_id"])} for r in raw]
    if args.slug:
        rows = [r for r in rows if r["slug"] == args.slug]
        if not rows:
            sys.exit(f"No sources for slug '{args.slug}'.")
        published = published & {args.slug}

    print(f"Verifying {len(rows)} sources" + (" (offline: provenance only)" if args.offline else ""))
    results = check(rows, args.offline)

    if args.json:
        Path(args.json).write_text(json.dumps(results, indent=1))
        print(f"\nFull result -> {args.json}")

    verdicts = Counter(r["verdict"] for r in results)
    print(f"\n{'=' * 70}\nSOURCE VERIFICATION\n{'=' * 70}")
    for k, v in verdicts.most_common():
        print(f"  {k:24s} {v:4d}   {v / len(results):5.1%}")

    bad = [r for r in results if r["verdict"] in FAILING]
    if bad:
        per = Counter(r["slug"] for r in bad)
        tot = Counter(r["slug"] for r in results)
        print("\nby topic (failing / total):")
        for slug, n in sorted(per.items(), key=lambda x: -x[1] / max(tot[x[0]], 1)):
            tag = "  published: corpus rows only, see record below" if slug in published else ""
            print(f"  {slug:54s} {n:3d}/{tot[slug]:3d}  {n / tot[slug]:5.0%}{tag}")

    wrong = [r for r in results if r["verdict"] == "WRONG_DOCUMENT"][:8]
    if wrong:
        print("\nPointing at a DIFFERENT document (first 8):")
        for r in wrong:
            print(f"  {r['identifier']}")
            print(f"     we say : {r['title'][:88]}")
            print(f"     it is  : {(r['registered_title'] or '')[:88]}")

    code, outcome = report(results, bad, published, rows)
    print(f"\nSOURCES_OUTCOME={outcome}")
    return code


def report(results: list[dict], bad: list[dict], published: set[str],
           rows: list[dict], root: Path = PUBLISHED) -> tuple[int, str]:
    """Print the verdict and return (exit code, outcome).

    FAILS only for what reaches a reader: a PUBLISHED topic whose publish
    record is missing, holds a surviving source with no document, or no
    longer matches the corpus. Draft topics are not served (the anon key reads
    published topics only -- migration 078, enforced daily by db-posture), so
    their uncitable rows are reported in full but do not fail the job. A draft
    is fixed by rebuilding it through publish_topic.py, which is the same gate
    that makes a published topic citable, not by anything this job can see.

    Before 2026-10-19 this failed on every draft row, every week, since
    2026-08-31 -- a control that is red regardless of what changes stops
    being read, which is the failure this file was written to prevent.
    """
    ids_by_slug: dict[str, set[str]] = {}
    for r in rows:
        ids_by_slug.setdefault(r["slug"], set()).add(r["id"])
    pub_problems = {s: published_problems(s, ids_by_slug.get(s, set()), root=root)
                    for s in sorted(published)}
    draft_bad = [r for r in bad if r["slug"] not in published]
    draft_total = sum(1 for r in results if r["slug"] not in published)

    print(f"\n{'=' * 70}")
    if pub_problems:
        print("PUBLISHED TOPICS -- judged by their publish record, not the corpus rows")
        for slug, probs in pub_problems.items():
            if probs:
                print(f"  {slug}: FAIL")
                for p in probs:
                    print(f"      {p}")
            else:
                print(f"  {slug}: ok -- every surviving source has a held document "
                      f"and the record matches the corpus")
    if draft_total:
        print(f"\nDRAFT TOPICS (not served): {len(draft_bad)} of {draft_total} sources cannot be cited.")
        print("A source that was never fetched did not supply the claims attributed to")
        print("it -- a model summary did. A source whose identifier does not resolve")
        print("names no document at all. These topics stay unpublishable until they")
        print("are rebuilt through publish_topic.py. Reported, not failed.")

    if any(pub_problems.values()):
        print("\nA PUBLISHED topic's sources are not covered by its record. Fix before")
        print("anything else: re-run the publish gate, or unpublish the topic.")
        return 1, "published_problem"
    if not bad:
        print("\nEvery source resolves to the document it names, and every claim was "
              "extracted from text actually fetched from it.")
        return 0, "clean"
    return 0, "drafts_only"


if __name__ == "__main__":
    sys.exit(main())
