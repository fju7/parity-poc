"""The check-an-answer pipeline (study/whu-reliability/check_pilot/pipeline.py), offline.

One recorded answer (fixtures/whu_check/answer_claude_sources.md, a constructed answer: the
study's own answers are private), one recorded source (an excerpt of a CC BY review) and
recorded judge replies. No network and no model call: licence, retrieval, token counting and
the judge are passed in. Design: docs/whu-check-an-answer-pilot.md."""
import hashlib
import importlib.util
import json
import random
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1].parent
FIX = Path(__file__).resolve().parent / "fixtures" / "whu_check"
sys.path.insert(0, str(ROOT / "study" / "whu-reliability" / "check_pilot"))
import pipeline as P  # noqa: E402

SOURCE_URL = "https://pmc.ncbi.nlm.nih.gov/articles/PMC10771715/"
NEWS_URL = "https://uea.ac.uk/about/news/article/technology-assisted-therapy-example"


def fake_licence(url):
    if "PMC10771715" in url:
        return {"licence": "cc by", "by": "Europe PMC license field (recorded)", "ids": {"pmcid": "PMC10771715"}}
    return {"licence": None, "by": "no identifier in the address", "ids": {}}


def fake_retrieve(url, work):
    text = (FIX / "source_PMC10771715.txt").read_text(encoding="utf-8")
    sid = "S" + hashlib.sha256(url.encode()).hexdigest()[:12]
    (work / "sources").mkdir(parents=True, exist_ok=True)
    (work / "sources" / (sid + ".txt")).write_text(text, encoding="utf-8")
    return {"url": url, "source_id": sid, "extent": "full text", "extent_why": "recorded", "abstract_only": False,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest()}


def count(text):
    return len(text) // 4


class FakeMessages:
    def __init__(self, replies, refuse_first=False):
        self.replies, self.calls, self.refuse_first = replies, [], refuse_first

    def create(self, **kw):
        prompt = "".join(b["text"] for b in kw["messages"][0]["content"])
        self.calls.append(prompt)
        if self.refuse_first and len(self.calls) == 1:
            return SimpleNamespace(content=[SimpleNamespace(text="")], model=kw["model"], stop_reason="refusal",
                                   usage=SimpleNamespace(input_tokens=100, output_tokens=0))
        claim = prompt.split("<<<CLAIM", 1)[1].split("CLAIM>>>", 1)[0]
        key = next(k for k in self.replies if not k.startswith("_") and k in claim)
        return SimpleNamespace(content=[SimpleNamespace(text=json.dumps(self.replies[key]))], model=kw["model"],
                               stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=2000, output_tokens=120,
                                                     cache_creation_input_tokens=0, cache_read_input_tokens=0))


def client(**kw):
    return SimpleNamespace(messages=FakeMessages(json.loads((FIX / "replies.json").read_text()), **kw))


def run(tmp_path, **kw):
    text = (FIX / "answer_claude_sources.md").read_text(encoding="utf-8")
    prep = P.prepare(text, tmp_path, licence_fn=fake_licence, retrieve_fn=fake_retrieve, count=count)
    c = client(**kw)
    return prep, P.judge(prep["planned"], c), c


def test_the_recorded_answer_is_read_in_claudes_sources_format():
    text = (FIX / "answer_claude_sources.md").read_text(encoding="utf-8")
    md, cited, fmt = P.adapt_answer(text)
    assert fmt == "claude_sources"
    assert cited == [SOURCE_URL, NEWS_URL]
    assert "## Sources" not in md


def test_one_full_check_on_recorded_sources(tmp_path):
    prep, results, c = run(tmp_path)
    by = {r["claim"][:40]: r for r in results}
    labels = [r["label"] for r in results]
    assert len(results) == 4, [r["claim"] for r in results]
    assert labels.count(P.BACKED) == 1 and labels.count(P.NOT_BACKED) == 1
    assert labels.count(P.NO_SOURCE) == 1 and labels.count(P.COULDNT) == 1
    news = next(r for r in results if "news release" in r["claim"])
    assert news["label"] == P.COULDNT and "no open-licence copy" in news["reason"]
    over = next(r for r in results if "clearly better than every other" in r["claim"])
    assert over["label"] == P.NOT_BACKED and over["reason"].startswith("Overstates")
    assert over["span_verbatim"] is True
    # two claims judged, one call each; the news source was never fetched
    assert len(c.messages.calls) == 2
    assert prep["manifest"][NEWS_URL]["extent"] == "unreachable"
    assert not list((tmp_path / "sources").glob("S%s*" % hashlib.sha256(NEWS_URL.encode()).hexdigest()[:12]))
    t = P.totals(results)
    assert t["claims"] == 4 and t["usd"] > 0


def test_the_prompt_sent_is_the_frozen_m1_v3(tmp_path):
    _prep, _results, c = run(tmp_path)
    frozen = P.J.PROMPT.read_text(encoding="utf-8")
    head = frozen.split("{documents}", 1)[0]
    assert hashlib.sha256(P.J.PROMPT.read_bytes()).hexdigest() == P.J.PROMPT_SHA256
    assert all(call.startswith(head) for call in c.messages.calls)


def test_a_refusal_is_asked_once_more_unchanged(tmp_path):
    _prep, results, c = run(tmp_path, refuse_first=True)
    assert len(c.messages.calls) == 3 and c.messages.calls[0] == c.messages.calls[1]
    judged = [r for r in results if r.get("attempts")]
    assert len(judged[0]["attempts"]) == 2


def test_a_claim_is_never_judged_on_part_of_its_sources(tmp_path):
    text = (FIX / "answer_claude_sources.md").read_text(encoding="utf-8").replace(
        "6435 participants found", "6435 participants \\[2\\] found")
    prep = P.prepare(text, tmp_path, licence_fn=fake_licence, retrieve_fn=fake_retrieve, count=count)
    first = next(p for p in prep["planned"] if "6435" in p["claim"])
    assert first["label"] == P.COULDNT and NEWS_URL in first["reason"]


def test_the_cap_check_runs_before_each_call(tmp_path):
    text = (FIX / "answer_claude_sources.md").read_text(encoding="utf-8")
    prep = P.prepare(text, tmp_path, licence_fn=fake_licence, retrieve_fn=fake_retrieve, count=count)
    c = client()

    def over(_worst):
        raise P.Stop("over the cap")
    with pytest.raises(P.Stop):
        P.judge(prep["planned"], c, over)
    assert c.messages.calls == []


def test_the_claim_limit(tmp_path):
    text = (FIX / "answer_claude_sources.md").read_text(encoding="utf-8")
    prep = P.prepare(text, tmp_path, max_claims=2, licence_fn=fake_licence, retrieve_fn=fake_retrieve, count=count)
    assert len(prep["claims"]) == 2 and len(prep["beyond_limit"]) == 2


def test_study_labels_map_as_the_study_counts_them():
    assert P.study_label_to_check("Supported") == P.BACKED
    for lab in ("Overstates", "Understates", "Absent", "Wrong source", "Contradicted"):
        assert P.study_label_to_check(lab) == P.NOT_BACKED
    assert P.study_label_to_check("UNCITED") == P.NO_SOURCE
    for lab in ("Unreachable", "NOT_VERIFIABLE_ABSTRACT", "INCOMPLETE_SOURCES", "REFUSED", "NO_SOURCE_HELD", None):
        assert P.study_label_to_check(lab) == P.COULDNT


def test_format_detection():
    assert P.detect_format("<!DOCTYPE html><html>") == "gemini_html"
    assert P.detect_format("Claim 【46†L181-L190】.") == "chatgpt_lenticular"
    assert P.detect_format("Claim [[1]](https://a.org/x).") == "chatgpt_bracketed"
    assert P.detect_format("Claim [^1].\n\n## References\n1. [t](https://a.org)") == "perplexity_sources"
    assert P.detect_format("Claim 1.\n\n#### **Works cited**\n1. x https://a.org") == "gemini_works_cited"
    assert P.detect_format("Claim \\[1\\].\n\n## Sources\n1. [t](https://a.org)") == "claude_sources"
    assert P.detect_format("Claim [a.org](https://a.org).") == "report_section"


def test_the_pilot_sample_draw():
    spec = importlib.util.spec_from_file_location("run_pilot_t", ROOT / "study" / "whu-reliability" / "check_pilot" / "run_pilot.py")
    R = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R)
    rng = random.Random("%d/check-pilot" % int("5d83e9b8025312923f3fb8ea2d5de3b47c212362", 16))
    want = [(q, s) for s in ("Claude", "ChatGPT", "Gemini", "Perplexity")
            for q in sorted(rng.sample(["WHU-S01", "WHU-S02", "WHU-S03", "WHU-S04"], 2))]
    assert R.draw() == want
    assert [s for _q, s in want] == ["Claude"] * 2 + ["ChatGPT"] * 2 + ["Gemini"] * 2 + ["Perplexity"] * 2
