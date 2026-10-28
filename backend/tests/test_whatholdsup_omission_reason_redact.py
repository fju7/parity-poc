"""omissions.json holds locations and hashes only: a ruling reason that quotes
the source is stored with the quotation replaced by its location.

Post-study, mid-rerun tool fix (2026-10-28). On WHU-S01r/S07r the omission
ruling's reason quoted the finding back, record() wrote it to omissions.json
verbatim, and the preflight leak guard (omissions.leaks_source_text, in the row
"omission objections ruled") blocked. The public reason now carries
"[S003@start-end]" (offsets in the held text) in place of any run of six or more
held-text words; the reason as written goes to rulings/omissions.jsonl, which is
never committed. Committed files are not rewritten.

The decision is made by the real omission ruling (ruling.rule_omissions, a fake
model whose reason quotes the finding), and the real preflight row is asked.

COUNTERFACTUAL. Stop passing held_text in ruling.py (or make redact return the
reason unchanged) and t_end_to_end goes red, on the leak guard and the row.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))
sys.path.insert(0, str(ROOT / "backend" / "tests"))

import omissions as O                       # noqa: E402
import test_whatholdsup_fix2_ruling as T    # noqa: E402

QUOTED = "investment in public transport can further support a shift to less intensive modes"
REASON = ('Step 1: in scope. The finding says "%s", which answers how layout and pricing '
          'interact; it is "high confidence" in the source.' % QUOTED)


def test_redact_replaces_a_quoted_run_with_its_location():
    out = O.redact(REASON, "S003", T.TEXT)
    assert QUOTED not in out.lower()
    [(a, b)] = [tuple(map(int, m)) for m in re.findall(r'"\[S003@(\d+)-(\d+)\]"', out)]
    assert T.TEXT[a:b].lower().startswith("investment in public transport")
    assert T.TEXT[a:b].rstrip(".").lower().endswith("less intensive modes")
    # short phrases and WHU's own words stay
    assert '"high confidence"' in out and "answers how layout and pricing interact" in out


def test_redact_leaves_a_reason_with_no_source_run_alone():
    r = "The page already states the transport finding in its own words."
    assert O.redact(r, "S003", T.TEXT) == r


def test_end_to_end_the_ruled_record_holds_no_source_text(tmp_path, monkeypatch):
    T._case(tmp_path, monkeypatch, [T._obj(T.OMITTED)])
    [d] = T._run(tmp_path, T.Fake(dict(T.ADD, reason=REASON)))
    assert d["outcome"] == "ADD"
    [e] = O.load(tmp_path)["omissions"]
    assert "[S003@" in e["reason"] and QUOTED not in e["reason"].lower()
    assert O.leaks_source_text(tmp_path, T.HELD) == []
    [row] = O.preflight_rows(T.SLUG, [], case=tmp_path, held=T.HELD)
    assert row[1] == "ok", row
    # the reason as written is kept privately
    priv = [json.loads(l) for l in (tmp_path / "rulings" / O.PRIVATE).read_text().splitlines()]
    assert priv[-1]["reason"] == REASON


def test_the_preflight_row_still_blocks_on_source_text(tmp_path, monkeypatch):
    T._case(tmp_path, monkeypatch, [T._obj(T.OMITTED)])
    T._run(tmp_path, T.Fake(dict(T.ADD, reason=REASON)))
    doc = O.load(tmp_path)
    doc["omissions"][0]["reason"] = REASON          # as a writer without redaction would leave it
    (tmp_path / O.RECORD).write_text(json.dumps(doc))
    [row] = O.preflight_rows(T.SLUG, [], case=tmp_path, held=T.HELD)
    assert row[1] == "BLOCKED" and "source text" in row[2]
