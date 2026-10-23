"""Store and gate records are dated in UTC (2026-10-22).

They were dated with date.today() (and time.strftime), the date where the
machine is. On Fred's Mac a WHU-S03 run at 21:05 New York time on 22 October,
01:05 UTC on the 23rd, the date in every run directory's stamp, wrote the
22nd. Now: source_store.utc_today() for every date the store writes, and for
acquire_sources, find_access and findings; ruling.py and factcheck_draft (the
gate's checked_at and the recency sweep's "today") take the UTC date too.
"""
import ast
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "backend" / "scripts"
WHU = SCRIPTS / "whatholdsup"
sys.path.insert(0, str(WHU))

import source_store as store  # noqa: E402

INSTANT = datetime(2026, 10, 23, 1, 5, tzinfo=timezone.utc)      # 21:05 on the 22nd in New York


class Clock(datetime):
    """datetime.now() at INSTANT: aware when asked with a zone, else New York wall time."""

    @classmethod
    def now(cls, tz=None):
        return INSTANT.astimezone(tz) if tz else INSTANT.astimezone(ZoneInfo("America/New_York")).replace(tzinfo=None)


def test_utc_today_is_the_utc_date_not_the_local_one(monkeypatch):
    monkeypatch.setattr(store, "datetime", Clock)
    assert Clock.now().date().isoformat() == "2026-10-22"          # what a local date would write
    assert store.utc_today() == "2026-10-23"


def test_a_held_document_is_recorded_with_the_utc_date(tmp_path, monkeypatch):
    case = tmp_path / "issues" / "WHU-999-t"
    case.mkdir(parents=True)
    (case / "sources.json").write_text(json.dumps({"sources": [{"id": "S001", "url": "https://example.org/a",
                                                                "title": "t"}]}))
    monkeypatch.setattr(store, "CASES", tmp_path / "issues")
    monkeypatch.setattr(store, "LIB", tmp_path / "library")
    monkeypatch.setattr(store, "datetime", Clock)
    row = store.put("t", "S001", b"%PDF-1.4 hello", url="https://example.org/a", via="test")
    assert row["retrieved"] == "2026-10-23"
    held = store.load_issue_index("t")["sources"]["S001"]
    assert held["held"] == "2026-10-23"
    assert store.load_index()["docs"][row["sha256"]]["first_held"] == "2026-10-23"


# --- no local date is left in the store and gate modules ---------------------

FILES = [WHU / "source_store.py", WHU / "acquire_sources.py", WHU / "find_access.py", WHU / "findings.py",
         WHU / "ruling.py", SCRIPTS / "signal" / "factcheck_draft.py"]


def _local_date_calls(path):
    out = []
    for n in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Attribute):
            continue
        f, base = n.func.attr, n.func.value
        name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
        if (name == "date" and f == "today") or (name == "datetime" and f == "today") \
                or (name == "time" and f in ("strftime", "localtime")) \
                or (name == "datetime" and f == "now" and not n.args and not n.keywords):
            out.append("%s:%d %s.%s()" % (path.name, n.lineno, name, f))
    return out


@pytest.mark.parametrize("path", FILES, ids=lambda p: p.name)
def test_no_local_date_in_store_and_gate_records(path):
    found = _local_date_calls(path)
    if path.name == "factcheck_draft.py":
        # _days_since compares a stored date with the clock; it writes nothing
        found = [f for f in found if not f.startswith("factcheck_draft.py:%d " % _days_since_line(path))]
    assert found == []


def _days_since_line(path):
    src = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, l in enumerate(src) if l.startswith("def _days_since"))
    return next(i + 1 for i in range(start, len(src)) if "datetime.now()" in src[i])
