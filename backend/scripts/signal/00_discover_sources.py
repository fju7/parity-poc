"""
Parity Signal: Claude-powered source discovery for new topics.

Given a topic slug, title, and description, uses Claude to generate a curated
list of 30-40 credible sources and writes them to the sources manifest JSON.

Usage:
    cd backend && source venv/bin/activate
    export $(grep -v '^#' .env | xargs)

    python scripts/signal/00_discover_sources.py \
        --slug ozempic-kidney \\
        --title "Ozempic & Kidney Disease" \\
        --description "Evidence on semaglutide for chronic kidney disease" \\
        --count 35
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_ROOT.parent
SOURCES_DIR = PROJECT_ROOT / "data" / "signal" / "sources"

# Retry config for Claude API
MAX_RETRIES = 3
RETRY_DELAYS = [2, 5, 10]

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

# 2026-09-15 (shared assertion policy, surface S4 -> WITHHOLD). Until today
# every batch prompt below carried a slot "url": "https://doi.org/..." and the
# system prompt said "do not fabricate citations, DOIs". 59 of the frozen
# corpus's 381 identifiers resolve to nothing and 33 to a different paper.
# The slot is gone: the model proposes what it can know -- title, first
# author, container, year -- and verify.search asks the registries whether
# such a thing exists. A title that resolves to nothing is written to the
# manifest as UNRESOLVED and is never given an identifier. The prompt does
# not name the thing it must not produce, because naming it puts it in
# context (CLAUDE.md, the two prohibition rules).
SYSTEM_PROMPT = """You are a medical research librarian proposing sources for an evidence intelligence platform called Parity Signal.

Your task: propose a list of real, high-quality publications, regulatory documents, clinical trials and institutional reports on the given topic, described by their bibliographic facts. The platform looks each one up in the publisher and trial registries itself; you supply what a librarian would type into a catalogue search.

RULES:
- Give the exact title as published, the first author's surname, the journal or issuing body, and the year. Where you are unsure of a detail, leave that field null rather than filling it.
- Prefer peer-reviewed journals, regulatory documents, Cochrane reviews, meta-analyses, and landmark clinical trials
- Provide substantive summaries and key findings, not placeholders
- Each source needs a unique slug (lowercase-kebab-case, descriptive)

Source types to use: clinical_trial, meta_analysis, systematic_review, rct, fda, regulatory, guideline, observational, policy, journal, government, organization, news

Return ONLY a JSON array of source objects. No markdown fencing, no explanatory text."""

BATCH_PROMPTS = {
    "clinical_rct": """Find {count} high-quality clinical trials and RCTs on: {title}

Description: {description}

Focus on landmark trials, pivotal studies, and well-cited RCTs. Include:
- Phase III trials with significant findings
- Pivotal trials that led to regulatory decisions
- Well-powered RCTs with clear endpoints

Return a JSON array where each object has:
{{
  "slug": "unique-kebab-case-id",
  "title": "Full publication title",
  "first_author": "surname of the first author, or null",
  "container": "journal name, or null",
  "year": 2019,
  "trial_registry_title": "the trial's registered title if this is a registered trial, else null",
  "source_type": "clinical_trial" or "rct",
  "publication_date": "YYYY-MM-DD",
  "fetchable": false,
  "fetch_strategy": "metadata_only",
  "summary": "2-3 sentence summary of what the study found",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"]
}}""",
    "regulatory_fda": """Find {count} FDA regulatory documents, safety communications, and approval-related sources on: {title}

Description: {description}

Focus on:
- FDA approval letters and label changes
- Safety communications and boxed warnings
- Advisory committee briefing documents
- EMA or other regulatory agency decisions

Return a JSON array where each object has:
{{
  "slug": "unique-kebab-case-id",
  "title": "Full document title",
  "issuing_body": "the agency, e.g. FDA, EMA, MHRA",
  "year": 2019,
  "url": "the document's web address if you are confident of it, else null",
  "source_type": "fda" or "regulatory",
  "publication_date": "YYYY-MM-DD",
  "fetchable": false,
  "fetch_strategy": "metadata_only",
  "summary": "2-3 sentence summary of the regulatory action",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"]
}}""",
    "reviews_meta": """Find {count} systematic reviews, meta-analyses, and Cochrane reviews on: {title}

Description: {description}

Focus on:
- Cochrane systematic reviews
- High-impact meta-analyses in top journals
- Umbrella reviews or scoping reviews
- Clinical practice guideline reviews

Return a JSON array where each object has:
{{
  "slug": "unique-kebab-case-id",
  "title": "Full publication title",
  "first_author": "surname of the first author, or null",
  "container": "journal name, or null",
  "year": 2019,
  "source_type": "systematic_review" or "meta_analysis" or "guideline",
  "publication_date": "YYYY-MM-DD",
  "fetchable": false,
  "fetch_strategy": "metadata_only",
  "summary": "2-3 sentence summary of what the review concluded",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"]
}}""",
    "observational_policy": """Find {count} observational studies, real-world evidence, policy analyses, and expert commentary on: {title}

Description: {description}

Focus on:
- Large observational cohort studies
- Real-world evidence / registry studies
- Health policy analyses
- Expert position statements from major medical societies
- Health economics / cost-effectiveness analyses

Return a JSON array where each object has:
{{
  "slug": "unique-kebab-case-id",
  "title": "Full publication or report title",
  "first_author": "surname of the first author or null",
  "container": "journal, agency or organisation, or null",
  "year": 2019,
  "url": "for an organisation or agency web page only: its address, or null",
  "source_type": "observational" or "policy" or "guideline" or "organization",
  "publication_date": "YYYY-MM-DD",
  "fetchable": false,
  "fetch_strategy": "metadata_only",
  "summary": "2-3 sentence summary of findings or recommendations",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"]
}}""",
}

CATEGORIES_PROMPT = """Given this medical/health topic, generate exactly 6 evidence categories for organizing claims and sources.

Topic: {title}
Description: {description}

Each category should be:
- A lowercase_snake_case identifier (e.g., "treatment_efficacy", "safety_profile")
- Relevant to the kinds of evidence claims that would be scored on this topic
- Distinct from other categories (minimal overlap)

Return ONLY a JSON array of 6 strings. No explanation. Example:
["efficacy", "safety", "cardiovascular", "pricing", "regulatory", "emerging"]"""


# ---------------------------------------------------------------------------
# Claude API helper
# ---------------------------------------------------------------------------

def _metered(client, *, role=""):
    """Wrap the client so every call lands in the spend ledger.

    By PATH, never by putting backend/scripts on sys.path: scripts/signal/ is a
    package named `signal` and shadows the stdlib from there, which broke the
    gate outright on 2026-08-31.
    """
    try:
        import importlib.util
        from pathlib import Path as _P
        _p = _P(__file__).resolve().parents[1] / "spend_ledger.py"
        _s = importlib.util.spec_from_file_location("spend_ledger", _p)
        _m = importlib.util.module_from_spec(_s)
        _s.loader.exec_module(_m)
        return _m.metered(client, script=_P(__file__).name, role=role)
    except Exception:
        return client


def _get_client():
    """Create Anthropic client."""
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    return _metered(anthropic.Anthropic(api_key=api_key))


def _call_claude(client, system: str, user_msg: str, max_tokens: int = 8192) -> str:
    """Call Claude with retry logic."""
    for attempt in range(MAX_RETRIES):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                temperature=0.3,
                system=system,
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = ""
            for block in response.content:
                if hasattr(block, "text"):
                    raw += block.text
            return raw.strip()
        except Exception as exc:
            if attempt < MAX_RETRIES - 1:
                delay = RETRY_DELAYS[attempt]
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {delay}s: {exc}")
                time.sleep(delay)
            else:
                raise


def _parse_json_response(raw: str) -> list | dict:
    """Parse Claude's response, stripping markdown fencing if present."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```\s*$", "", raw)
    return json.loads(raw.strip())


# ---------------------------------------------------------------------------
# Source discovery
# ---------------------------------------------------------------------------

def discover_sources(client, title: str, description: str, total_count: int) -> list[dict]:
    """Discover sources in batches by source type."""
    batch_types = list(BATCH_PROMPTS.keys())
    per_batch = max(5, total_count // len(batch_types))
    # Give clinical trials a larger share
    batch_counts = {
        "clinical_rct": per_batch + 3,
        "regulatory_fda": per_batch - 1,
        "reviews_meta": per_batch,
        "observational_policy": per_batch - 2,
    }

    all_sources = []
    seen_slugs = set()
    seen_ids = set()

    for batch_name, prompt_template in BATCH_PROMPTS.items():
        count = batch_counts.get(batch_name, per_batch)
        print(f"\n  Batch: {batch_name} (requesting {count} sources)...")

        prompt = prompt_template.format(
            count=count, title=title, description=description,
        )
        # Later batches are told what earlier ones already proposed, so the
        # model does not spend a batch re-proposing the same landmark papers.
        already = [x.get("title") for x in all_sources if x.get("title")]
        if already:
            prompt += "\n\nAlready proposed (do not repeat these):\n" + "\n".join(f"- {t}" for t in already)

        try:
            raw = _call_claude(client, SYSTEM_PROMPT, prompt)
            sources = _parse_json_response(raw)

            if not isinstance(sources, list):
                print(f"    WARNING: Expected list, got {type(sources).__name__}")
                continue

            # Deduplicate by slug, then RESOLVE: identifiers come from the
            # registries, never from the reply.
            added = 0
            for src in sources:
                slug = src.get("slug", "")
                if slug and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    resolved_src = _resolve_proposal(src)
                    # One source per real document: two proposals that resolve
                    # to the same identifier are the same source.
                    key = resolved_src.get("identifier") or resolved_src.get("url")
                    if key and key in seen_ids:
                        print(f"    [dup] {slug} resolves to {key}, already held")
                        continue
                    if key:
                        seen_ids.add(key)
                    all_sources.append(resolved_src)
                    added += 1

            resolved = sum(1 for x in all_sources if x.get("identifier"))
            print(f"    Got {added} unique sources (total: {len(all_sources)}, resolved so far: {resolved})")

        except json.JSONDecodeError as exc:
            print(f"    ERROR: Failed to parse JSON from Claude: {exc}")
            continue
        except Exception as exc:
            print(f"    ERROR: Claude API call failed: {exc}")
            continue

        # Brief pause between batches
        time.sleep(1)

    return all_sources


# ---------------------------------------------------------------------------
# Resolution: the registry answers, not the model
# ---------------------------------------------------------------------------
LITERATURE_TYPES = {"clinical_trial", "rct", "meta_analysis", "systematic_review", "observational", "journal", "guideline"}
PAGE_TYPES = {"fda", "regulatory", "government", "organization", "policy", "news"}


def _resolve_proposal(src: dict) -> dict:
    """Attach identifier/url/resolution from a registry search, or mark the
    proposal UNRESOLVED. Any url or identifier-shaped field the model put in
    the reply for a literature source is discarded before this runs."""
    sys.path.insert(0, str(BACKEND_ROOT))
    from verify.search import search, Found
    from verify import generic
    from verify.text import agreement, LITERATURE_BOILERPLATE

    stype = (src.get("source_type") or "").lower()
    title = src.get("title") or ""
    year = src.get("year") if isinstance(src.get("year"), int) else None
    out = dict(src)
    out.pop("url", None); out.pop("doi", None); out.pop("identifier", None); out.pop("citation", None)

    if stype in LITERATURE_TYPES or stype not in PAGE_TYPES:
        kind = "trial" if stype in ("clinical_trial", "rct") and src.get("trial_registry_title") else None
        r = search(src.get("trial_registry_title") or title, src.get("first_author"), year, kind)
        if isinstance(r, Found):
            out["identifier"] = f"{r.identifier.system}:{r.identifier.value}"
            out["url"] = r.canonical
            out["resolution"] = {"registry": r.registry, "heading": r.heading, "provenance": "SEARCHED",
                                 "ratio": round(r.ratio, 3), "shared": sorted(r.shared), "checked_at": r.checked_at,
                                 "first_author": r.first_author, "year": r.year}
            out["fetch_strategy"] = "doi_metadata" if r.identifier.system == "doi" else out.get("fetch_strategy", "metadata_only")
        else:
            out["url"] = None
            out["unresolved"] = r.to_dict()                # reason, status (NOT_FOUND | REGISTRY_UNAVAILABLE), registries, candidates
            out["fetch_strategy"] = "unresolved"
        return out

    # An agency / organisation page has no registry. The model may propose the
    # address; it is kept only if the page fetched under it carries the title.
    url = src.get("url")
    if url:
        ident = generic.identify(url)
        res = generic.resolve(ident) if ident else None
        heading = (res.heading or "") if res else ""
        ratio, shared = agreement(title, heading, LITERATURE_BOILERPLATE) if heading else (0.0, set())
        if res and res.exists.value == "EXISTS" and (ratio == 1.0 and shared or (ratio >= 0.5 and len(shared) >= 2)):
            out["url"] = url
            out["resolution"] = {"registry": "generic_fetch", "heading": heading, "provenance": "TYPED_THEN_FETCHED",
                                 "ratio": round(ratio, 3), "shared": sorted(shared), "checked_at": res.checked_at}
            return out
        out["unresolved"] = {"reason": "proposed page did not carry the proposed title" if res else "proposed page could not be fetched",
                             "candidates": [("generic_fetch", heading)] if heading else [], "checked_at": _now()}
    else:
        out["unresolved"] = {"reason": "no registry for this source type and no address proposed", "candidates": [], "checked_at": _now()}
    out["url"] = None
    out["fetch_strategy"] = "unresolved"
    return out


def _now() -> str:
    import datetime as _dt
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def discover_categories(client, title: str, description: str) -> list[str]:
    """Use Claude to generate 6 evidence categories for the topic."""
    print("\n  Generating evidence categories...")
    prompt = CATEGORIES_PROMPT.format(title=title, description=description)

    try:
        raw = _call_claude(client, SYSTEM_PROMPT, prompt, max_tokens=256)
        categories = _parse_json_response(raw)
        if isinstance(categories, list) and len(categories) >= 4:
            print(f"    Categories: {categories}")
            return categories[:6]
    except Exception as exc:
        print(f"    WARNING: Category generation failed: {exc}")

    # Fallback generic categories
    fallback = ["efficacy", "safety", "outcomes", "access", "regulatory", "emerging"]
    print(f"    Using fallback categories: {fallback}")
    return fallback


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Discover credible sources for a Signal topic using Claude."
    )
    parser.add_argument("--slug", required=True, help="Topic slug (kebab-case)")
    parser.add_argument("--title", required=True, help="Topic title")
    parser.add_argument("--description", required=True, help="Topic description")
    parser.add_argument("--count", type=int, default=35, help="Target source count (default: 35)")
    parser.add_argument("--dry-run", action="store_true", help="Print results without writing file")
    parser.add_argument("--out", default=None, help="Write the manifest here instead of data/signal/sources/ (scratch runs; never the pipeline path)")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"SOURCE DISCOVERY: {args.title}")
    print(f"Slug: {args.slug}")
    print(f"Target: ~{args.count} sources")
    print(f"{'='*60}")

    client = _get_client()

    # Discover sources
    sources = discover_sources(client, args.title, args.description, args.count)
    n_res = sum(1 for x in sources if x.get("identifier") or x.get("resolution"))
    n_unres = sum(1 for x in sources if x.get("unresolved"))
    print(f"\nResolution: {n_res} of {len(sources)} proposals resolved by registry/fetch; {n_unres} unresolved (kept, marked, never guessed)")

    if not sources:
        print("\nERROR: No sources discovered")
        sys.exit(1)

    # Discover categories
    categories = discover_categories(client, args.title, args.description)

    # Write sources manifest
    output_path = Path(args.out) if args.out else SOURCES_DIR / f"{args.slug}_sources.json"

    if args.dry_run:
        print(f"\n[DRY RUN] Would write {len(sources)} sources to {output_path}")
        print(f"[DRY RUN] Categories: {categories}")
    else:
        SOURCES_DIR.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(sources, f, indent=2)
        print(f"\nWrote {len(sources)} sources to {output_path}")

    # Output categories as JSON to stdout for caller to capture
    print(f"\n__CATEGORIES_JSON__:{json.dumps(categories)}")

    print(f"\nSource discovery complete: {len(sources)} sources, {len(categories)} categories")


if __name__ == "__main__":
    main()
