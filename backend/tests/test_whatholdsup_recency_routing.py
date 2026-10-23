"""A recency finding is ruled on the body sentences that use the source (2026-10-22).

The gate's recency role names a study, not a sentence. ruling.py used to look
the name up among the page's sentences, and the sentence that carries a study's
name is its title line in the source list: on WHU-S02, rec-1 was ruled on the
source-list line, with no bound passage, while the body sentences printing the
study's figures went unexamined. Now findings.recency_targets attaches the
finding to every body sentence whose binding rests on the study's source (span,
premise or also_rests_on), never to a source-list line, and ruling.py rules
each with the recency result and that sentence's bound passages.

A synthetic issue: the source's title appears in the source list, and its
figures in two body sentences (one bound by its span, one by a premise). The
model is a stub; nothing is spent.
"""
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

import ruling as R  # noqa: E402

DOC1 = ("Long-term survival in the FOOBAR trial of a new drug. Methods. At three years, mortality fell "
        "from 12% to 9% with the new drug. Relapse fell by a quarter, from 20% to 15%. More text.")
DOC2 = "A different study. It found that 40% of patients stopped treatment early. Further text."
HELD = {"S1": DOC1, "S2": DOC2}
TITLE_LINE = "Long-term survival in the FOOBAR trial of a new drug."
BODY1 = "Mortality fell from 12% to 9% at three years."
BODY2 = "Relapse fell from 20% to 15%, a drop of a quarter."
BODY3 = "Elsewhere, 40% of patients stopped treatment early."
PAGE = ("<html><head><title>t</title></head><body><p>%s %s %s</p>"
        '<div class="sources"><div class="src"><span class="tag">S1</span>'
        '<a href="https://example.org/foobar">Smith J, Jones K. %s Example Journal 2024.</a></div>'
        '<div class="src"><span class="tag">S2</span>'
        '<a href="https://example.org/other">Lee A. A different study. Other Journal 2023.</a></div>'
        "</div></body></html>" % (BODY1, BODY2, BODY3, TITLE_LINE))
ROWS = {
    "title": {"sentence": TITLE_LINE, "on_page": True, "source_id": "S1",
              "span": "Long-term survival in the FOOBAR trial of a new drug"},
    "b1": {"sentence": BODY1, "on_page": True, "source_id": "S1",
           "span": "At three years, mortality fell from 12% to 9% with the new drug"},
    "b2": {"sentence": BODY2, "on_page": True, "bucket": "judgement",
           "premises": [{"source_id": "S1", "span": "Relapse fell by a quarter, from 20% to 15%"}]},
    "b3": {"sentence": BODY3, "on_page": True, "source_id": "S2",
           "span": "40% of patients stopped treatment early"},
}
STUDY = "Smith, Jones et al. \u2014 Long-term survival in the FOOBAR trial"
REPORT = {"sha256": "ab12cd34" + "0" * 56, "recency": {"studies": [
    {"name": STUDY, "status": "SUPERSEDED", "draft_uses": "the three-year readout",
     "latest_known": "the five-year readout, 2026", "what_changed": "mortality 12% to 10%"}]}}


class Fake:
    def __init__(self, reply):
        self.prompts, self.reply = [], reply

    def __call__(self, prompt, max_tokens, role):
        self.prompts.append(prompt)
        r = self.reply(prompt) if callable(self.reply) else self.reply
        return json.dumps(r), {"input": 10, "output": 5, "usd": 0.0}


@pytest.fixture
def issue(tmp_path, monkeypatch):
    d = tmp_path / "issues" / "WHU-S99-xq"
    d.mkdir(parents=True)
    (d / "issue.json").write_text(json.dumps({"slug": "xq", "study": True}))
    (d / "sources.json").write_text(json.dumps({"sources": [
        {"id": "S1", "type": "primary", "url": "https://example.org/foobar",
         "title": "Long-term survival in the FOOBAR trial of a new drug"},
        {"id": "S2", "type": "primary", "url": "https://example.org/other", "title": "A different study"}]}))
    (d / "bindings.json").write_text(json.dumps({"bindings": ROWS}))
    import source_store
    import bindings
    monkeypatch.setattr(source_store, "case_dir", lambda slug: d)
    monkeypatch.setattr(bindings, "path", lambda slug: d / "bindings.json")
    monkeypatch.setattr(bindings, "_page_html", lambda slug: PAGE)
    monkeypatch.setattr(bindings, "_is_study", lambda slug: True)
    return d, types.SimpleNamespace(is_study=lambda slug: slug == "xq")


def test_the_finding_is_attached_to_both_body_sentences_and_not_the_source_list_line(issue):
    import findings as F
    sids, keys = F.recency_targets("xq", STUDY, ROWS)
    assert sids == ["S1"]
    assert keys == ["b1", "b2"]                     # span and premise; not "title", not b3
    F.scan("xq", REPORT)
    rec = F.load("xq")["findings"][0]
    assert rec["id"] == "fab12cd34-rec-1"
    assert rec["attached_to"] == {"study": STUDY, "sources": ["S1"], "rows": ["b1", "b2"]}


def test_each_body_sentence_is_ruled_with_the_recency_result_and_its_own_passages(issue):
    d, P = issue
    import findings as F
    F.scan("xq", REPORT)
    fake = Fake({"ruling": "reject", "text": None, "reason": "Quotation 1 is current.", "quotation": 1})
    done = R.rule_gate("xq", fake, P=P, report=REPORT, rows=ROWS, held=HELD)
    assert len(fake.prompts) == 2
    p1, p2 = fake.prompts
    assert BODY1 in p1 and "mortality fell from 12% to 9%" in p1
    assert BODY2 in p2 and "Relapse fell by a quarter" in p2
    for p in fake.prompts:
        assert TITLE_LINE not in p.split("Quotation")[0]     # the source-list line is not the sentence
        assert "SUPERSEDED" in p and "the three-year readout" in p and "five-year" in p
        assert "S1" not in p and "S2" not in p                # no source id travels
        assert "40% of patients" not in p                     # S2's sentence is not involved
    f = F.load("xq")["findings"][0]
    assert [x["row"] for x in f["sentence_rulings"]] == ["b1", "b2"]
    assert f["decision"] == "rejected" and f["source_id"] == "S1" and f["quote"]
    assert done == [f]
    logs = [json.loads(l) for l in (d / "rulings" / "rulings.jsonl").read_text().splitlines()]
    assert [x["row"] for x in logs] == ["b1", "b2"]
    assert all(x["inputs"]["sentence"] in (BODY1, BODY2) for x in logs)


def test_an_amended_sentence_settles_the_finding_as_accepted_with_its_own_text(issue):
    d, P = issue
    import findings as F
    F.scan("xq", REPORT)
    new = "Mortality fell from 12% to 10% at five years."
    fake = Fake(lambda pr: ({"ruling": "amend", "text": new, "reason": "five-year readout", "quotation": 1}
                            if BODY1 in pr else {"ruling": "reject", "text": None, "reason": "r",
                                                 "quotation": 1}))
    R.rule_gate("xq", fake, P=P, report=REPORT, rows=ROWS, held=HELD)
    f = F.load("xq")["findings"][0]
    assert f["decision"] == "accepted"
    by_row = {x["row"]: x for x in f["sentence_rulings"]}
    assert by_row["b1"]["ruling_text"] == new and by_row["b2"]["ruling"] == "reject"
    rec = [json.loads(l) for l in (d / "rulings" / "rulings.jsonl").read_text().splitlines()]
    assert [(x["row"], x["ruling"], x.get("text")) for x in rec] == [("b1", "amend", new), ("b2", "reject", None)]


def test_a_sentence_left_unruled_keeps_the_finding_open_and_is_ruled_next_run(issue):
    d, P = issue
    import findings as F
    import audit_stage as A
    F.scan("xq", REPORT)

    def reply(pr):
        if BODY2 in pr:
            raise A.ReplyCutOff("cut off", {"usd": 0.0})
        return {"ruling": "reject", "text": None, "reason": "r", "quotation": 1}

    class Cut(Fake):
        def __call__(self, prompt, max_tokens, role):
            self.prompts.append(prompt)
            return json.dumps(self.reply(prompt)), {"usd": 0.0}
    R.rule_gate("xq", Cut(reply), P=P, report=REPORT, rows=ROWS, held=HELD, failed=[])
    f = F.load("xq")["findings"][0]
    assert f["decision"] == "" and [x["row"] for x in f["sentence_rulings"]] == ["b1"]
    again = Fake({"ruling": "reject", "text": None, "reason": "r", "quotation": 1})
    R.rule_gate("xq", again, P=P, report=REPORT, rows=ROWS, held=HELD)
    assert len(again.prompts) == 1 and BODY2 in again.prompts[0]          # only the one left
    f = F.load("xq")["findings"][0]
    assert f["decision"] == "rejected" and [x["row"] for x in f["sentence_rulings"]] == ["b1", "b2"]


def test_pending_counts_one_call_per_body_sentence(issue, monkeypatch):
    d, P = issue
    import findings as F
    import bindings
    F.scan("xq", REPORT)
    page = d / "draft" / "p.html"
    page.parent.mkdir()
    page.write_text(PAGE)
    page.with_suffix(".html.gate.json").write_text(json.dumps(REPORT))
    monkeypatch.setattr(bindings, "load", lambda slug: {"bindings": ROWS})
    P2 = types.SimpleNamespace(ROOT=d, issue_cfg=lambda slug: {"page": "draft/p.html"}, is_study=lambda s: True)
    assert R.pending("gate", "xq", P=P2) == 2
