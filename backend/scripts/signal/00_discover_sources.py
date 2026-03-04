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

SYSTEM_PROMPT = """You are a medical research librarian curating sources for an evidence intelligence platform called Parity Signal.

Your task: produce a list of REAL, citable, high-quality sources on the given topic. These must be actual publications, regulatory filings, clinical trials, or institutional reports that exist and can be verified.

CRITICAL RULES:
- Every source must be REAL — do not fabricate citations, DOIs, or publication dates
- Prefer peer-reviewed journals, FDA filings, Cochrane reviews, meta-analyses, and landmark clinical trials
- Include accurate publication dates (year and month minimum)
- Provide substantive summaries and key findings, not placeholders
- Use proper citation format (Author(s), Title, Journal, Year)
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
  "url": "https://doi.org/... or https://clinicaltrials.gov/... or journal URL",
  "source_type": "clinical_trial" or "rct",
  "publication_date": "YYYY-MM-DD",
  "fetchable": false,
  "fetch_strategy": "metadata_only",
  "summary": "2-3 sentence summary of what the study found",
  "citation": "Author(s). Title. Journal. Year;Volume:Pages.",
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
  "url": "https://www.fda.gov/... or regulatory URL",
  "source_type": "fda" or "regulatory",
  "publication_date": "YYYY-MM-DD",
  "fetchable": false,
  "fetch_strategy": "metadata_only",
  "summary": "2-3 sentence summary of the regulatory action",
  "citation": "Proper citation for the regulatory document",
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
  "url": "https://doi.org/... or journal URL",
  "source_type": "systematic_review" or "meta_analysis" or "guideline",
  "publication_date": "YYYY-MM-DD",
  "fetchable": false,
  "fetch_strategy": "metadata_only",
  "summary": "2-3 sentence summary of what the review concluded",
  "citation": "Author(s). Title. Journal. Year;Volume:Pages.",
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
  "url": "https://doi.org/... or organization URL",
  "source_type": "observational" or "policy" or "guideline" or "organization",
  "publication_date": "YYYY-MM-DD",
  "fetchable": false,
  "fetch_strategy": "metadata_only",
  "summary": "2-3 sentence summary of findings or recommendations",
  "citation": "Proper citation for the source",
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

def _get_client():
    """Create Anthropic client."""
    import anthropic
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)


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

    for batch_name, prompt_template in BATCH_PROMPTS.items():
        count = batch_counts.get(batch_name, per_batch)
        print(f"\n  Batch: {batch_name} (requesting {count} sources)...")

        prompt = prompt_template.format(
            count=count, title=title, description=description,
        )

        try:
            raw = _call_claude(client, SYSTEM_PROMPT, prompt)
            sources = _parse_json_response(raw)

            if not isinstance(sources, list):
                print(f"    WARNING: Expected list, got {type(sources).__name__}")
                continue

            # Deduplicate by slug
            added = 0
            for src in sources:
                slug = src.get("slug", "")
                if slug and slug not in seen_slugs:
                    seen_slugs.add(slug)
                    all_sources.append(src)
                    added += 1

            print(f"    Got {added} unique sources (total: {len(all_sources)})")

        except json.JSONDecodeError as exc:
            print(f"    ERROR: Failed to parse JSON from Claude: {exc}")
            continue
        except Exception as exc:
            print(f"    ERROR: Claude API call failed: {exc}")
            continue

        # Brief pause between batches
        time.sleep(1)

    return all_sources


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
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"SOURCE DISCOVERY: {args.title}")
    print(f"Slug: {args.slug}")
    print(f"Target: ~{args.count} sources")
    print(f"{'='*60}")

    client = _get_client()

    # Discover sources
    sources = discover_sources(client, args.title, args.description, args.count)

    if not sources:
        print("\nERROR: No sources discovered")
        sys.exit(1)

    # Discover categories
    categories = discover_categories(client, args.title, args.description)

    # Write sources manifest
    output_path = SOURCES_DIR / f"{args.slug}_sources.json"

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
