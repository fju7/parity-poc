"""The one client the backend reads the Signal corpus with.

WHY THIS EXISTS
---------------
Migration 078 gates every Signal corpus table on signal_issues.status =
'published' with row-level security. RLS binds anon and authenticated; it
does not bind service_role, and the backend's ordinary client
(supabase_client.supabase) IS service_role. So a router that read
signal_claims through the ordinary client would see every draft topic and
serve it, exactly as it did before the gate existed.

This client is built with the anon key. Whatever it reads, the policies have
already filtered, so a router that reads through it cannot show a draft --
not because the router remembers to check status, but because the rows are
not there. tests/signal/test_signal_reads_are_gated.py fails the build if a
router reads a corpus table through anything else.

Writers -- pipeline scripts, the /admin endpoints -- keep the service key:
they need to see drafts, and they are not the surface a reader meets.
"""
from __future__ import annotations

import os

from postgrest import SyncPostgrestClient

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kfxxpscdwoemtzylhhhb.supabase.co")

# The publishable key is public by design (the SPA ships it to every browser,
# frontend/src/lib/supabase.js); it is only ever as powerful as RLS lets it be.
SUPABASE_ANON_KEY = os.environ.get(
    "SUPABASE_ANON_KEY", "sb_publishable_i3Is6dAsKW6ERM9v39PluA_Tw-X3cp-"
)

# Every table that holds corpus content or a bridge into it. A router may
# read these ONLY through signal_reader(). Kept here so the static test and
# the migration name the same set.
CORPUS_TABLES = frozenset({
    "signal_issues", "signal_sources", "signal_claims", "signal_claim_sources",
    "signal_claim_scores", "signal_claim_composites", "signal_consensus",
    "signal_summaries", "signal_evidence_updates", "signal_cpt_mappings",
    "signal_denial_playbook", "signal_topic_counts",
})

_reader = None


def signal_reader():
    """A PostgREST client that sees only published Signal topics.

    Built on postgrest-py directly rather than supabase.create_client: the
    pinned supabase-py (2.13.0) rejects any key that is not JWT-shaped, and
    the publishable key is not. The `.table(...)` builder is the same object
    supabase-py hands back, so call sites read identically.
    """
    global _reader
    if _reader is None:
        _reader = SyncPostgrestClient(
            SUPABASE_URL.rstrip("/") + "/rest/v1",
            headers={"apikey": SUPABASE_ANON_KEY,
                     "Authorization": "Bearer " + SUPABASE_ANON_KEY},
        )
    return _reader


# ---------------------------------------------------------------------------
# The frozen publication record (Phase 3). status = 'published' opens the
# door; the record says what stands inside it. Every consumer that shows a
# claim filters by it, so a claim the gates did not support is never served
# even from a published topic.
# ---------------------------------------------------------------------------
CORPUS_TABLES = CORPUS_TABLES | {"topic_publications", "topic_rechecks"}


def latest_publication(slug: str) -> dict | None:
    """The newest topic_publications row for a slug, or None (also None before 080)."""
    try:
        rows = (signal_reader().table("topic_publications")
                .select("slug,publish_id,published_at,gate_version,supported_claim_ids,surviving_source_ids,flipped")
                .eq("slug", slug).order("published_at", desc=True).limit(1).execute().data)
        return rows[0] if rows else None
    except Exception:
        return None


def published_claim_ids(slug: str) -> set | None:
    """Claim ids the record supports, or None when there is no record --
    in which case a consumer must serve NO claims: no record, no support."""
    pub = latest_publication(slug)
    return set(pub["supported_claim_ids"]) if pub else None
