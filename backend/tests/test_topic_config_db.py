"""Offline tests for database-backed topic resolution in topic_config.

These exist because of a specific operational failure: topics registered at
runtime were persisted ONLY to backend/data/signal/dynamic_topics.json, a
gitignored file. Six of the nine topics live on the site had no definition on
the operator's machine at all, so every pipeline script raised "Unknown topic
slug" for them. The site published topics that could not be re-run.

topic_config now falls back to signal_issues. What these tests protect is that
the fallback is lossless (a rebuilt config equals what register_topic wrote),
that hardcoded topics still win, and that a missing or broken database
degrades to the old KeyError rather than crashing the import.

No network, no Supabase — a stub client answers from a fixture.
"""

import sys
from pathlib import Path

import pytest

SIGNAL_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts" / "signal"
sys.path.insert(0, str(SIGNAL_SCRIPTS))

import topic_config  # noqa: E402


ROW_CAP = 1000  # what PostgREST would truncate an unpaged select to


# ---------------------------------------------------------------------------
# Stub Supabase
# ---------------------------------------------------------------------------

class StubQuery:
    def __init__(self, table, client):
        self.table = table
        self.client = client
        self.filters = {}
        self._range = None

    def select(self, *_a, **_k):
        return self

    def eq(self, col, val):
        self.filters[col] = val
        return self

    def limit(self, _n):
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def execute(self):
        self.client.queries.append((self.table, dict(self.filters), self._range))
        rows = self.client.data.get(self.table, [])
        for col, val in self.filters.items():
            rows = [r for r in rows if r.get(col) == val]
        if self._range is not None:
            start, end = self._range
            rows = rows[start : end + 1]
        return type("Res", (), {"data": rows})()


class StubClient:
    def __init__(self, data):
        self.data = data
        self.queries = []

    def table(self, name):
        return StubQuery(name, self)


class ExplodingClient:
    """Every query raises — stands in for a down or misconfigured database."""

    def table(self, _name):
        raise RuntimeError("connection refused")


ISSUE_ID = "11111111-1111-1111-1111-111111111111"

FIXTURE = {
    "signal_issues": [
        {
            "id": ISSUE_ID,
            "slug": "crispr-gene-therapy",
            "title": "CRISPR Gene Therapy",
            "description": "Evidence assessment of CRISPR-based gene therapies.",
        }
    ],
    "signal_consensus": [
        {"issue_id": ISSUE_ID, "category": "safety"},
        {"issue_id": ISSUE_ID, "category": "efficacy"},
        {"issue_id": ISSUE_ID, "category": "access"},
    ],
    "signal_claims": [],
}


@pytest.fixture(autouse=True)
def clear_caches():
    """Each test starts with no memoised database lookups."""
    topic_config._DB_TOPIC_CACHE.clear()
    topic_config._DB_MISSING.clear()
    yield
    topic_config._DB_TOPIC_CACHE.clear()
    topic_config._DB_MISSING.clear()


def use(monkeypatch, client):
    monkeypatch.setattr(topic_config, "_get_supabase", lambda: client)


# ---------------------------------------------------------------------------
# Resolution order
# ---------------------------------------------------------------------------

def test_hardcoded_topic_wins_over_database(monkeypatch):
    """A hardcoded topic must keep its hand-written prompt_detail.

    The description column is one sentence; TOPICS['glp1-drugs'] carries a
    paragraph the extraction prompts depend on. The database must not shadow it.
    """
    poisoned = {
        "signal_issues": [
            {"id": "x", "slug": "glp1-drugs", "title": "WRONG", "description": "WRONG"}
        ],
        "signal_consensus": [],
        "signal_claims": [],
    }
    client = StubClient(poisoned)
    use(monkeypatch, client)

    topic = topic_config.get_topic("glp1-drugs")

    assert topic["title"] == "GLP-1 Receptor Agonist Drugs"
    assert "semaglutide" in topic["prompt_detail"]
    assert client.queries == [], "hardcoded topics must not query the database"


def test_database_topic_resolves(monkeypatch):
    use(monkeypatch, StubClient(FIXTURE))

    topic = topic_config.get_topic("crispr-gene-therapy")

    assert topic["slug"] == "crispr-gene-therapy"
    assert topic["title"] == "CRISPR Gene Therapy"
    assert topic["categories"] == ["access", "efficacy", "safety"]
    assert topic["manifest_filename"] == "crispr-gene-therapy_sources.json"


def test_rebuilt_config_equals_what_register_topic_would_write(monkeypatch):
    """The whole justification for reading from the database: nothing is lost.

    register_topic derives prompt_subject from the title, prompt_detail from
    the description, and manifest_filename from the slug. If that ever stops
    being true, the fallback starts silently returning a different config and
    this test fails.
    """
    use(monkeypatch, StubClient(FIXTURE))
    from_db = topic_config.get_topic("crispr-gene-therapy")

    expected = topic_config._build_topic(
        "crispr-gene-therapy",
        "CRISPR Gene Therapy",
        "Evidence assessment of CRISPR-based gene therapies.",
        ["access", "efficacy", "safety"],
    )
    assert from_db == expected


def test_database_lookup_is_cached(monkeypatch):
    client = StubClient(FIXTURE)
    use(monkeypatch, client)

    topic_config.get_topic("crispr-gene-therapy")
    first = len(client.queries)
    topic_config.get_topic("crispr-gene-therapy")

    assert len(client.queries) == first, "second lookup must come from cache"


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

def test_categories_fall_back_to_claims_when_consensus_is_empty(monkeypatch):
    """A topic scored but not yet consensus-mapped still needs its categories."""
    data = {
        "signal_issues": FIXTURE["signal_issues"],
        "signal_consensus": [],
        "signal_claims": [
            {"issue_id": ISSUE_ID, "category": "safety"},
            {"issue_id": ISSUE_ID, "category": "efficacy"},
            {"issue_id": ISSUE_ID, "category": "safety"},
        ],
    }
    use(monkeypatch, StubClient(data))

    topic = topic_config.get_topic("crispr-gene-therapy")
    assert topic["categories"] == ["efficacy", "safety"]


def test_claims_fallback_pages_past_the_postgrest_row_cap(monkeypatch):
    """The category that only appears after row 1000 must still be found.

    This repo has shipped this bug twice (P0.1, the A1 citation map). An
    unpaged select would return the first 1000 rows and silently drop
    'late_category'.
    """
    claims = [{"issue_id": ISSUE_ID, "category": "safety"} for _ in range(ROW_CAP)]
    claims.append({"issue_id": ISSUE_ID, "category": "late_category"})
    data = {
        "signal_issues": FIXTURE["signal_issues"],
        "signal_consensus": [],
        "signal_claims": claims,
    }
    client = StubClient(data)
    use(monkeypatch, client)

    topic = topic_config.get_topic("crispr-gene-therapy")

    assert topic["categories"] == ["late_category", "safety"]
    ranges = [q[2] for q in client.queries if q[0] == "signal_claims"]
    assert len(ranges) > 1, "must issue more than one page"


# ---------------------------------------------------------------------------
# Degradation
# ---------------------------------------------------------------------------

def test_unknown_slug_raises_keyerror_listing_valid_slugs(monkeypatch):
    use(monkeypatch, StubClient(FIXTURE))

    with pytest.raises(KeyError) as exc:
        topic_config.get_topic("no-such-topic")

    msg = str(exc.value)
    assert "no-such-topic" in msg
    assert "crispr-gene-therapy" in msg, "the error must name the topics that DO exist"


def test_missing_database_degrades_to_keyerror(monkeypatch):
    """No credentials must not crash the pipeline — it behaves as before."""
    use(monkeypatch, lambda: None)
    monkeypatch.setattr(topic_config, "_get_supabase", lambda: None)

    with pytest.raises(KeyError):
        topic_config.get_topic("crispr-gene-therapy")


def test_broken_database_degrades_to_keyerror(monkeypatch):
    use(monkeypatch, ExplodingClient())

    with pytest.raises(KeyError):
        topic_config.get_topic("crispr-gene-therapy")


def test_missing_slug_is_not_retried(monkeypatch):
    client = StubClient(FIXTURE)
    use(monkeypatch, client)

    for _ in range(3):
        with pytest.raises(KeyError):
            topic_config.get_topic("no-such-topic")

    issue_lookups = [
        q for q in client.queries
        if q[0] == "signal_issues" and q[1].get("slug") == "no-such-topic"
    ]
    assert len(issue_lookups) == 1, "a known-absent slug must not be re-queried"


# ---------------------------------------------------------------------------
# list_slugs
# ---------------------------------------------------------------------------

def test_list_slugs_merges_database_topics(monkeypatch):
    use(monkeypatch, StubClient(FIXTURE))

    slugs = topic_config.list_slugs()

    assert "glp1-drugs" in slugs
    assert "crispr-gene-therapy" in slugs
    assert slugs == sorted(slugs)


def test_list_slugs_offline_excludes_database(monkeypatch):
    client = StubClient(FIXTURE)
    use(monkeypatch, client)

    slugs = topic_config.list_slugs(include_database=False)

    assert "crispr-gene-therapy" not in slugs
    assert "glp1-drugs" in slugs
    assert client.queries == []
