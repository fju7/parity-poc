"""
Parity Signal: Collect and load GLP-1 source library into Supabase.

Reads the curated source manifest from data/signal/sources/glp1_sources.json
and loads each source into the signal_sources table. Creates the GLP-1 issue
row in signal_issues if it doesn't already exist.

Usage:
    cd backend
    python3 scripts/signal/collect_sources.py [--dry-run] [--fetch-content] [--slugs slug1,slug2]

Flags:
    --dry-run         Print what would be inserted without touching Supabase
    --fetch-content   Attempt to fetch full text for fetchable sources
    --slugs           Comma-separated list of slugs to process (default: all)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from html.parser import HTMLParser
from pathlib import Path

# Add backend/ to sys.path so we can import supabase_client
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

try:
    import httpx
    _HTTP_CLIENT = "httpx"
except ImportError:
    _HTTP_CLIENT = "urllib"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
MANIFEST_PATH = PROJECT_ROOT / "data" / "signal" / "sources" / "glp1_sources.json"

GLP1_ISSUE = {
    "slug": "glp1-drugs",
    "title": "GLP-1 Receptor Agonist Drugs",
    "description": (
        "Evidence assessment of GLP-1 receptor agonist medications "
        "(semaglutide/Ozempic/Wegovy, tirzepatide/Mounjaro/Zepbound) "
        "for obesity, diabetes, and cardiovascular outcomes."
    ),
    "status": "draft",
}

HTTP_TIMEOUT = 15  # seconds
FETCH_DELAY = 1.0  # seconds between fetches (rate-limit courtesy)
MAX_CONTENT_LENGTH = 50_000  # truncate fetched content


# ---------------------------------------------------------------------------
# HTML text extraction
# ---------------------------------------------------------------------------

class _HTMLTextExtractor(HTMLParser):
    """Minimal HTML-to-text converter using stdlib."""

    def __init__(self):
        super().__init__()
        self._parts: list[str] = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._skip = False
        if tag in ("p", "div", "br", "h1", "h2", "h3", "h4", "li", "tr"):
            self._parts.append("\n")

    def handle_data(self, data):
        if not self._skip:
            self._parts.append(data)

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Collapse whitespace
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _html_to_text(html: str) -> str:
    extractor = _HTMLTextExtractor()
    extractor.feed(html)
    return extractor.get_text()


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _http_get(url: str, timeout: int = HTTP_TIMEOUT) -> str | None:
    """Fetch a URL and return the response body as text, or None on failure."""
    try:
        if _HTTP_CLIENT == "httpx":
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "ParitySignal/1.0"})
                resp.raise_for_status()
                return resp.text
        else:
            import urllib.request
            req = urllib.request.Request(url, headers={"User-Agent": "ParitySignal/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"  [WARN] HTTP fetch failed for {url}: {exc}")
        return None


# ---------------------------------------------------------------------------
# Content fetchers by strategy
# ---------------------------------------------------------------------------

def _fetch_clinicaltrials(source: dict) -> str | None:
    """Fetch structured study data from ClinicalTrials.gov v2 API."""
    nct_id = source.get("nct_id")
    if not nct_id:
        return None
    url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    raw = _http_get(url)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        parts = []
        proto = data.get("protocolSection", {})

        ident = proto.get("identificationModule", {})
        parts.append(f"Title: {ident.get('officialTitle', ident.get('briefTitle', ''))}")

        desc = proto.get("descriptionModule", {})
        if desc.get("briefSummary"):
            parts.append(f"\nBrief Summary:\n{desc['briefSummary']}")
        if desc.get("detailedDescription"):
            parts.append(f"\nDetailed Description:\n{desc['detailedDescription']}")

        design = proto.get("designModule", {})
        if design:
            parts.append(f"\nStudy Type: {design.get('studyType', 'N/A')}")
            phases = design.get("phases", [])
            if phases:
                parts.append(f"Phase: {', '.join(phases)}")
            enroll = design.get("enrollmentInfo", {})
            if enroll:
                parts.append(f"Enrollment: {enroll.get('count', 'N/A')} ({enroll.get('type', '')})")

        outcomes = proto.get("outcomesModule", {})
        primary = outcomes.get("primaryOutcomes", [])
        if primary:
            parts.append("\nPrimary Outcomes:")
            for o in primary[:5]:
                parts.append(f"  - {o.get('measure', '')}")

        results = data.get("resultsSection")
        if results:
            parts.append("\n[Results section available in registry]")

        return "\n".join(parts)
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"  [WARN] Failed to parse ClinicalTrials.gov response for {nct_id}: {exc}")
        return None


def _fetch_doi_metadata(source: dict) -> str | None:
    """Fetch article metadata from CrossRef API using DOI."""
    doi = source.get("doi")
    if not doi:
        return None
    url = f"https://api.crossref.org/works/{doi}"
    raw = _http_get(url)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        work = data.get("message", {})
        parts = []
        titles = work.get("title", [])
        if titles:
            parts.append(f"Title: {titles[0]}")
        authors = work.get("author", [])
        if authors:
            names = [f"{a.get('given', '')} {a.get('family', '')}".strip() for a in authors[:10]]
            parts.append(f"Authors: {', '.join(names)}")
        container = work.get("container-title", [])
        if container:
            parts.append(f"Journal: {container[0]}")
        published = work.get("published-print") or work.get("published-online")
        if published and published.get("date-parts"):
            parts.append(f"Published: {'-'.join(str(p) for p in published['date-parts'][0])}")
        abstract = work.get("abstract", "")
        if abstract:
            # CrossRef abstracts contain JATS XML tags
            clean = re.sub(r"<[^>]+>", "", abstract)
            parts.append(f"\nAbstract:\n{clean}")
        return "\n".join(parts)
    except (json.JSONDecodeError, KeyError) as exc:
        print(f"  [WARN] Failed to parse CrossRef response for {doi}: {exc}")
        return None


def _fetch_fda_html(source: dict) -> str | None:
    """Fetch FDA press release and extract text."""
    raw = _http_get(source["url"])
    if not raw:
        return None
    return _html_to_text(raw)


def _fetch_generic_html(source: dict) -> str | None:
    """Fetch generic HTML page and extract text."""
    raw = _http_get(source["url"])
    if not raw:
        return None
    return _html_to_text(raw)


def fetch_content(source: dict) -> str | None:
    """Dispatch content fetching based on the source's fetch_strategy."""
    strategy = source.get("fetch_strategy", "metadata_only")

    if strategy == "metadata_only":
        return None
    elif strategy == "clinicaltrials_api":
        return _fetch_clinicaltrials(source)
    elif strategy == "doi_metadata":
        return _fetch_doi_metadata(source)
    elif strategy == "fda_html":
        return _fetch_fda_html(source)
    elif strategy == "html":
        return _fetch_generic_html(source)
    else:
        print(f"  [WARN] Unknown fetch_strategy: {strategy}")
        return None


# ---------------------------------------------------------------------------
# Manifest loading
# ---------------------------------------------------------------------------

def load_manifest(path: Path = MANIFEST_PATH) -> list[dict]:
    """Read and validate the source manifest JSON."""
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found at {path}")
    with open(path) as f:
        sources = json.load(f)
    required = {"slug", "title", "source_type"}
    for i, s in enumerate(sources):
        missing = required - set(s.keys())
        if missing:
            raise ValueError(f"Source index {i} ('{s.get('slug', '?')}') missing fields: {missing}")
    print(f"Loaded manifest: {len(sources)} sources from {path.name}")
    return sources


# ---------------------------------------------------------------------------
# Supabase operations
# ---------------------------------------------------------------------------

def ensure_glp1_issue(sb) -> str:
    """Create or retrieve the GLP-1 issue row. Returns the issue UUID."""
    resp = sb.table("signal_issues").select("id").eq("slug", GLP1_ISSUE["slug"]).execute()
    if resp.data:
        issue_id = resp.data[0]["id"]
        print(f"Found existing issue: {GLP1_ISSUE['slug']} ({issue_id})")
        return issue_id

    resp = sb.table("signal_issues").insert(GLP1_ISSUE).execute()
    issue_id = resp.data[0]["id"]
    print(f"Created issue: {GLP1_ISSUE['slug']} ({issue_id})")
    return issue_id


def get_existing_slugs(sb, issue_id: str) -> set[str]:
    """Get the set of source slugs already loaded for this issue."""
    resp = (
        sb.table("signal_sources")
        .select("metadata")
        .eq("issue_id", issue_id)
        .execute()
    )
    slugs = set()
    for row in resp.data:
        meta = row.get("metadata")
        if isinstance(meta, dict) and "slug" in meta:
            slugs.add(meta["slug"])
    if slugs:
        print(f"Found {len(slugs)} existing sources in Supabase")
    return slugs


def build_supabase_row(source: dict, issue_id: str, content: str | None) -> dict:
    """Map a manifest source dict to a signal_sources table row."""
    content_text = content or source.get("summary", "")
    if content_text and len(content_text) > MAX_CONTENT_LENGTH:
        content_text = content_text[:MAX_CONTENT_LENGTH] + "\n\n[truncated]"

    return {
        "issue_id": issue_id,
        "title": source["title"],
        "url": source.get("url"),
        "source_type": source["source_type"],
        "publication_date": source.get("publication_date"),
        "content_text": content_text,
        "metadata": {
            "slug": source["slug"],
            "drug": source.get("drug", []),
            "subcategory": source.get("subcategory"),
            "citation": source.get("citation"),
            "key_findings": source.get("key_findings", []),
            "fetch_strategy": source.get("fetch_strategy"),
            "fetchable": source.get("fetchable", False),
        },
    }


def load_sources(
    sb,
    sources: list[dict],
    issue_id: str,
    existing_slugs: set[str],
    do_fetch: bool,
    dry_run: bool,
) -> tuple[int, int, int]:
    """Load sources into Supabase. Returns (loaded, skipped, failed) counts."""
    loaded = 0
    skipped = 0
    failed = 0
    total = len(sources)

    for i, source in enumerate(sources, 1):
        slug = source["slug"]
        prefix = f"[{i:>2}/{total}]"

        if slug in existing_slugs:
            print(f"{prefix} [SKIP] already loaded: {slug}")
            skipped += 1
            continue

        content = None
        if do_fetch and source.get("fetchable"):
            print(f"{prefix} Fetching content for: {slug} ({source.get('fetch_strategy')})...")
            content = fetch_content(source)
            if content:
                print(f"        Fetched {len(content)} chars")
            else:
                print(f"        No content fetched, using summary")
            time.sleep(FETCH_DELAY)

        row = build_supabase_row(source, issue_id, content)

        if dry_run:
            print(f"{prefix} [DRY RUN] would insert: {slug} ({source['source_type']})")
            loaded += 1
            continue

        try:
            sb.table("signal_sources").insert(row).execute()
            print(f"{prefix} Loaded: {slug} ({source['source_type']})")
            loaded += 1
        except Exception as exc:
            print(f"{prefix} [ERROR] Failed to insert {slug}: {exc}")
            failed += 1

    return loaded, skipped, failed


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Load GLP-1 source library into Supabase signal_sources table."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be inserted without touching Supabase",
    )
    parser.add_argument(
        "--fetch-content",
        action="store_true",
        help="Attempt to fetch full text for fetchable sources",
    )
    parser.add_argument(
        "--slugs",
        type=str,
        default="",
        help="Comma-separated list of slugs to process (default: all)",
    )
    args = parser.parse_args()

    # Load manifest
    sources = load_manifest()

    # Filter by slugs if specified
    if args.slugs:
        slug_filter = {s.strip() for s in args.slugs.split(",") if s.strip()}
        sources = [s for s in sources if s["slug"] in slug_filter]
        unknown = slug_filter - {s["slug"] for s in sources}
        if unknown:
            print(f"[WARN] Unknown slugs (not in manifest): {', '.join(unknown)}")
        print(f"Filtered to {len(sources)} sources")

    if not sources:
        print("No sources to process.")
        return

    # Connect to Supabase
    if args.dry_run:
        print("\n--- DRY RUN MODE (no Supabase writes) ---\n")
        # For dry run, we don't need Supabase at all
        loaded, skipped, failed = 0, 0, 0
        for i, source in enumerate(sources, 1):
            print(f"[{i:>2}/{len(sources)}] [DRY RUN] would insert: {source['slug']} ({source['source_type']})")
            loaded += 1
    else:
        from supabase_client import supabase as sb

        if sb is None:
            print("ERROR: Supabase client not initialized.")
            print("Set SUPABASE_SERVICE_KEY environment variable before running.")
            print("  export SUPABASE_SERVICE_KEY=your_service_role_key_here")
            sys.exit(1)

        issue_id = ensure_glp1_issue(sb)
        existing_slugs = get_existing_slugs(sb, issue_id)
        loaded, skipped, failed = load_sources(
            sb, sources, issue_id, existing_slugs, args.fetch_content, dry_run=False
        )

    # Summary
    print(f"\n{'='*50}")
    print(f"Source collection complete.")
    print(f"  Loaded:  {loaded}")
    print(f"  Skipped: {skipped}")
    print(f"  Failed:  {failed}")
    print(f"  Total:   {loaded + skipped + failed}")


if __name__ == "__main__":
    main()
