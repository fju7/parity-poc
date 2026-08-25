"""Offline tests for the Parity Signal count helpers.

These exist because of a specific production bug: /api/signal/topics counted
claims by selecting every matching row and tallying them in Python. PostgREST
caps the rows it returns (Supabase default: 1000), so once the corpus passed
1000 claims the counts silently truncated — the landing-page claim counts
summed to exactly 1000 while the topic pages showed the true totals.

The fix moved counting into Postgres (view signal_topic_counts, migration 070)
with an exact-HEAD-count fallback. What these tests protect is that neither
path ever counts returned rows.

No network, no Supabase — a stub client records every query it is handed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from routers.signal_metrics import _approved_issues, _exact_count, _topic_counts  # noqa: E402


ROW_CAP = 1000  # what PostgREST would truncate to


class StubQuery:
    def __init__(self, table, client):
        self.table = table
        self.client = client
        self.filters = {}
        self.count_mode = None
        self.head = False

    def select(self, *cols, count=None, head=False):
        self.count_mode = count
        self.head = head
        return self

    def eq(self, column, value):
        self.filters[column] = ("eq", value)
        return self

    def in_(self, column, values):
        self.filters[column] = ("in", values)
        return self

    def execute(self):
        self.client.queries.append(self)
        return self.client.respond(self)


class StubResult:
    def __init__(self, data=None, count=None):
        self.data = data
        self.count = count


class StubClient:
    """Minimal Supabase stand-in. `tables` maps name -> list of row dicts."""

    def __init__(self, tables, missing=()):
        self.tables = tables
        self.missing = set(missing)
        self.queries = []

    def table(self, name):
        return StubQuery(name, self)

    def respond(self, q):
        if q.table in self.missing:
            raise RuntimeError(f"relation {q.table} does not exist")

        rows = list(self.tables.get(q.table, []))
        for column, (op, value) in q.filters.items():
            if op == "eq":
                rows = [r for r in rows if r.get(column) == value]
            else:
                rows = [r for r in rows if r.get(column) in value]

        if q.count_mode == "exact":
            # A real exact count is computed server-side and is never capped.
            return StubResult(data=[] if q.head else rows[:ROW_CAP], count=len(rows))

        # A plain select IS capped — this is the bug being guarded against.
        return StubResult(data=rows[:ROW_CAP])


def _corpus(per_topic):
    """Build a stub DB with `per_topic` = {issue_id: (claims, scored, sources)}."""
    issues, claims, composites, sources = [], [], [], []
    for iid, (n_claims, n_scored, n_sources) in per_topic.items():
        issues.append({"id": iid, "slug": iid, "title": iid, "quality_review_status": "approved"})
        for i in range(n_claims):
            cid = f"{iid}-c{i}"
            claims.append({"id": cid, "issue_id": iid})
            if i < n_scored:
                composites.append({"claim_id": cid})
        for i in range(n_sources):
            sources.append({"id": f"{iid}-s{i}", "issue_id": iid})
    return {
        "signal_issues": issues,
        "signal_claims": claims,
        "signal_claim_composites": composites,
        "signal_sources": sources,
    }


# The shape of the real corpus when the bug was found: 9 topics, ~1,600 claims.
PER_TOPIC = {
    "social-media": (211, 202, 41),
    "glp1": (153, 152, 41),
    "crispr": (190, 188, 44),
    "car-t": (160, 158, 38),
    "mrna": (130, 130, 32),
    "mmr": (96, 96, 21),
    "climate": (150, 148, 35),
    "diet-breast": (155, 151, 36),
    "breast-therapies": (240, 236, 52),
}
TOTAL_CLAIMS = sum(v[0] for v in PER_TOPIC.values())


def _view_rows(per_topic):
    return [
        {
            "issue_id": iid,
            "claim_count": c,
            "scored_count": s,
            "source_count": src,
        }
        for iid, (c, s, src) in per_topic.items()
    ]


def test_corpus_is_large_enough_to_trip_the_row_cap():
    """Guard the guard: if this ever drops below the cap the tests prove nothing."""
    assert TOTAL_CLAIMS > ROW_CAP


def test_counts_from_view_are_not_truncated():
    tables = _corpus(PER_TOPIC)
    tables["signal_topic_counts"] = _view_rows(PER_TOPIC)
    sb = StubClient(tables)

    counts = _topic_counts(sb, list(PER_TOPIC))

    assert sum(c["claim_count"] for c in counts.values()) == TOTAL_CLAIMS
    for iid, (claims, scored, sources) in PER_TOPIC.items():
        assert counts[iid] == {
            "claim_count": claims,
            "scored_count": scored,
            "source_count": sources,
        }


def test_counts_fall_back_to_exact_counts_when_view_is_missing():
    """A backend deployed ahead of migration 070 must still count correctly."""
    sb = StubClient(_corpus(PER_TOPIC), missing={"signal_topic_counts"})

    counts = _topic_counts(sb, list(PER_TOPIC))

    assert sum(c["claim_count"] for c in counts.values()) == TOTAL_CLAIMS
    for iid, (claims, _scored, sources) in PER_TOPIC.items():
        assert counts[iid]["claim_count"] == claims
        assert counts[iid]["source_count"] == sources
        # scored_count needs the view's join; the fallback reports it as unknown
        # rather than guessing.
        assert counts[iid]["scored_count"] is None


def test_fallback_never_issues_an_uncapped_row_select():
    """The regression itself: counting must not read rows back."""
    sb = StubClient(_corpus(PER_TOPIC), missing={"signal_topic_counts"})

    _topic_counts(sb, list(PER_TOPIC))

    counting = [q for q in sb.queries if q.table != "signal_topic_counts"]
    assert counting, "expected fallback queries"
    for q in counting:
        assert q.count_mode == "exact", f"{q.table} counted by reading rows"
        assert q.head is True, f"{q.table} pulled a row payload it does not need"


def test_naive_row_counting_would_have_been_wrong():
    """Reproduces the original bug so the test suite documents it."""
    sb = StubClient(_corpus(PER_TOPIC))
    rows = sb.table("signal_claims").select("id, issue_id").execute().data

    tally = {}
    for row in rows:
        tally[row["issue_id"]] = tally.get(row["issue_id"], 0) + 1

    assert sum(tally.values()) == ROW_CAP
    assert sum(tally.values()) != TOTAL_CLAIMS


def test_exact_count_handles_tables_without_an_id_column():
    """signal_claim_composites is keyed on claim_id, so select("id") would fail."""
    sb = StubClient(_corpus(PER_TOPIC))

    total_scored = sum(v[1] for v in PER_TOPIC.values())
    assert _exact_count(sb, "signal_claim_composites") == total_scored


def test_exact_count_returns_zero_on_error_instead_of_raising():
    sb = StubClient({}, missing={"nope"})
    assert _exact_count(sb, "nope") == 0


def test_approved_issues_filters_to_approved():
    tables = _corpus(PER_TOPIC)
    tables["signal_issues"].append(
        {"id": "draft-topic", "slug": "draft", "title": "Draft", "quality_review_status": "pending"}
    )
    sb = StubClient(tables)

    approved = _approved_issues(sb)

    assert len(approved) == len(PER_TOPIC)
    assert "draft-topic" not in {i["id"] for i in approved}


def test_approved_issues_falls_back_when_column_is_not_in_schema_cache():
    class NoColumnClient(StubClient):
        def respond(self, q):
            if "quality_review_status" in q.filters:
                raise RuntimeError("column does not exist in schema cache")
            return super().respond(q)

    sb = NoColumnClient(_corpus(PER_TOPIC))
    assert len(_approved_issues(sb)) == len(PER_TOPIC)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
