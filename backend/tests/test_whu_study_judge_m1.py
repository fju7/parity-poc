"""The reliability study's M1 runner: the rules it applies, not the prompt.

Rulings of 19 October 2026 (protocol, "Rulings from prep round 1"): a refusal
is retried once unchanged, then recorded as REFUSED and sent to a person; an
Absent on an abstract-only snapshot is NOT_VERIFIABLE_ABSTRACT; a source over
150,000 tokens is cut to the sections containing the claim's key terms and the
item marked CHUNKED. No API is called here."""
import importlib.util
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("judge_m1", ROOT / "study" / "whu-reliability" / "scripts" / "judge_m1.py")
J = importlib.util.module_from_spec(spec)
spec.loader.exec_module(J)


def test_absent_on_an_abstract_only_source_is_not_verifiable():
    assert J.final_label("Absent", False, [{"abstract_only": True}]) == J.NOT_VERIFIABLE_ABSTRACT
    assert J.final_label("Absent", False, [{"abstract_only": False}]) == "Absent"
    assert J.final_label("Overstates", False, [{"abstract_only": True}]) == "Overstates"
    assert J.final_label(None, True, [{"abstract_only": True}]) == J.REFUSED


def test_a_long_source_keeps_every_section_with_the_claims_key_terms():
    secs = ["Background on ultra-processed foods and health."] + \
           ["Filler paragraph %d about nothing in particular." % i for i in range(50)] + \
           ["In the cohort, hazard ratio 1.03 per 100 mg of carrageenans."] + \
           ["More filler %d." % i for i in range(50)]
    text = "\n\n".join(secs)
    claim = "Carrageenans raised type 2 diabetes risk (HR 1.03 per 100 mg)."
    out, info = J.chunk(text, claim, limit=10_000, count=lambda t: len(t) // 4)
    assert "hazard ratio 1.03" in out
    assert "Filler paragraph" not in out
    assert info["sections_kept"] >= 1 and info["dropped_for_length"] == 0


def test_chunking_drops_the_weakest_sections_until_it_fits():
    text = "\n\n".join(["1.03 carrageenans %d " % i + "x" * 400 for i in range(20)])
    out, info = J.chunk(text, "HR 1.03 for carrageenans", limit=500, count=lambda t: len(t) // 4)
    assert len(out) // 4 <= 500 and info["dropped_for_length"] > 0


def _run_dir(tmp_path, extent="full text", n_chars=1000):
    run = tmp_path / "run"; (run / "sources").mkdir(parents=True)
    url = "https://example.org/a"
    (run / "items.json").write_text(json.dumps([{"item": "P01", "claim": "Mice did better.", "context": "",
                                                 "urls": [url], "reference": "Supported"}]))
    (run / "sources" / "manifest.json").write_text(json.dumps([{"source_id": "S1", "url": url, "extent": extent,
                                                                "abstract_only": extent == "abstract only",
                                                                "text_sha256": "x"}]))
    (run / "sources" / "S1.txt").write_text("Mice did better in the trial. " * (n_chars // 30))
    return run


class FakeAnthropic:
    def __init__(self, api_key=None):
        self.messages = self

    def count_tokens(self, **kw):
        return type("C", (), {"input_tokens": 1000})()


def _wire(monkeypatch, claude, openai):
    import anthropic
    monkeypatch.setattr(anthropic, "Anthropic", FakeAnthropic)
    monkeypatch.setattr(J, "env_keys", lambda: {"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "y"})
    monkeypatch.setattr(J.S, "metered", lambda raw, **kw: raw)
    monkeypatch.setattr(J, "spent", lambda issue: 0.0)
    monkeypatch.setattr(J, "call_claude", claude)
    monkeypatch.setattr(J, "call_openai", openai)


def test_a_refusal_is_retried_once_unchanged_then_recorded_as_refused(tmp_path, monkeypatch):
    seen = []

    def claude(client, prefix, rest, model):
        seen.append(prefix + rest)
        return "", {"input": 1, "output": 0, "model": model, "stop": "refusal"}, 0.01, True

    def openai(key, prefix, rest, issue):
        return json.dumps({"label": "Supported", "span": "Mice did better in the trial.", "reason": "r"}), \
            {"input": 1, "output": 1, "model": "m"}, 0.01, False
    _wire(monkeypatch, claude, openai)
    run = _run_dir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(run), "--consistency-share", "0"])
    assert J.main() == 0
    assert len(seen) == 2 and seen[0] == seen[1]           # retried once, unchanged
    c = json.loads((run / "replies" / "claude" / "P01.json").read_text())
    o = json.loads((run / "replies" / "openai" / "P01.json").read_text())
    assert c["label"] == J.REFUSED and c["human_review"] is True and len(c["attempts"]) == 2
    assert o["label"] == "Supported"                       # the other judge's label stands


def test_absent_on_abstract_only_is_recorded_not_verifiable_by_the_runner(tmp_path, monkeypatch):
    absent = json.dumps({"label": "Absent", "span": "Mice did better in the trial.", "reason": "r"})
    _wire(monkeypatch,
          lambda c, p, r, m: (absent, {"input": 1, "output": 1, "model": m, "stop": "end_turn"}, 0.0, False),
          lambda k, p, r, i: (absent, {"input": 1, "output": 1, "model": "m"}, 0.0, False))
    run = _run_dir(tmp_path, extent="abstract only")
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(run)])
    J.main()
    for j in ("claude", "openai"):
        rec = json.loads((run / "replies" / j / "P01.json").read_text())
        assert rec["judge_label"] == "Absent" and rec["label"] == J.NOT_VERIFIABLE_ABSTRACT


def test_the_source_block_comes_first_and_is_the_cached_prefix():
    item = {"claim": "CLAIMTEXT", "context": "CTX"}
    prefix, rest = J.build({**item}, [{"extent": "full text", "text": "DOCTEXT"}])
    assert "DOCTEXT" in prefix and "CLAIMTEXT" not in prefix and "CLAIMTEXT" in rest
    assert prefix.index("DOCTEXT") < len(prefix)


def test_a_cited_work_with_no_snapshot_makes_the_item_incomplete_and_no_judge_is_called(tmp_path, monkeypatch):
    called = []
    _wire(monkeypatch, lambda *a: called.append(a), lambda *a: called.append(a))
    run = _run_dir(tmp_path)
    items = json.loads((run / "items.json").read_text())
    items[0]["citations"] = [{"label": "Atzeni et al. (2022)", "url": None, "note": "no link in the answer"},
                             {"label": "Gibney (2018)", "url": "https://example.org/a"}]
    (run / "items.json").write_text(json.dumps(items))
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(run)])
    J.main()
    assert called == []
    for j in ("claude", "openai"):
        rec = json.loads((run / "replies" / j / "P01.json").read_text())
        assert rec["label"] == J.INCOMPLETE_SOURCES and rec["human_review"] is True
        assert rec["unreachable_sources"][0]["label"] == "Atzeni et al. (2022)"


def test_the_author_line_goes_after_the_documents_and_before_the_claim(tmp_path, monkeypatch):
    sent = {}

    def claude(client, prefix, rest, model):
        sent["prefix"], sent["rest"] = prefix, rest
        return json.dumps({"label": "Supported", "span": "Mice did better in the trial.", "reason": "r"}), \
            {"input": 1, "output": 1, "model": model, "stop": "end_turn"}, 0.0, False
    _wire(monkeypatch, claude, lambda *a: (_ for _ in ()).throw(AssertionError("not called")))
    run = _run_dir(tmp_path)
    line = "This sentence was written by an AI chatbot."
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(run), "--judges", "claude", "--author-line", line])
    J.main()
    assert line not in sent["prefix"]                       # the cached block is unchanged
    assert sent["rest"].index(line) < sent["rest"].index("Mice did better.")


def _run_dir_n(tmp_path, n):
    run = tmp_path / "run"; (run / "sources").mkdir(parents=True)
    items, man = [], []
    for k in range(1, n + 1):
        url = "https://example.org/%d" % k
        items.append({"item": "P%02d" % k, "claim": "Mice did better %d." % k, "context": "",
                      "urls": [url], "reference": "Supported"})
        man.append({"source_id": "S%d" % k, "url": url, "extent": "full text", "abstract_only": False,
                    "text_sha256": "x"})
        (run / "sources" / ("S%d.txt" % k)).write_text("Mice did better in trial %d. " % k * 20)
    items.append({"item": "P99", "claim": "Not judged.", "context": "", "reference": "Supported",
                  "citations": [{"label": "No link (2020)", "url": None}]})
    (run / "items.json").write_text(json.dumps(items))
    (run / "sources" / "manifest.json").write_text(json.dumps(man))
    return run


def test_each_judge_reads_each_item_once_and_a_seeded_20_percent_twice(tmp_path, monkeypatch):
    """Budget ruling, protocol rev 26 (20 October 2026)."""
    import random
    calls = {"claude": [], "openai": []}
    reply = json.dumps({"label": "Supported", "span": "Mice did better", "reason": "r"})

    def claude(client, prefix, rest, model):
        calls["claude"].append(re.search(r"Mice did better (\d+)\.", rest).group(1))
        return reply, {"input": 1, "output": 1, "model": model, "stop": "end_turn"}, 0.0, False

    def openai(key, prefix, rest, issue):
        calls["openai"].append(re.search(r"Mice did better (\d+)\.", rest).group(1))
        return reply, {"input": 1, "output": 1, "model": "m"}, 0.0, False
    _wire(monkeypatch, claude, openai)
    run = _run_dir_n(tmp_path, 20)
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(run), "--seed", "777"])
    assert J.main() == 0
    pool = ["P%02d" % k for k in range(1, 21)]                 # P99 is INCOMPLETE_SOURCES: not judged, not drawn
    expected = sorted(random.Random(777).sample(sorted(pool), 4))
    from collections import Counter
    for judge in ("claude", "openai"):
        n = Counter("P%02d" % int(x) for x in calls[judge])
        assert set(n) == set(pool) and len(calls[judge]) == 24             # every item once, 4 of them twice
        assert sorted(i for i, c in n.items() if c == 2) == expected      # exactly the seeded sample again
        assert sorted(p.stem for p in (run / "replies_repeat" / judge).glob("P*.json")) == expected
        # each second read follows its first straight away (the cache is warm)
        seq = ["P%02d" % int(x) for x in calls[judge]]
        for i in expected:
            k = seq.index(i)
            assert seq[k + 1] == i
    s = json.loads((run / "replies" / "consistency_sample.json").read_text())
    assert s["seed"] == 777 and s["share"] == 0.2 and s["items"] == expected and s["pool"] == pool
    # Run again with another seed: the recorded sample stands and nothing is read.
    before = {j: len(c) for j, c in calls.items()}
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(run), "--seed", "778"])
    assert J.main() == 4
    assert {j: len(c) for j, c in calls.items()} == before


def test_the_sample_depends_on_the_seed_and_the_pool_not_the_order():
    ids = ["P%02d" % k for k in range(1, 41)]
    a = J.consistency_sample(ids, 0.2, 5)
    assert a == J.consistency_sample(list(reversed(ids)), 0.2, 5) and len(a) == 8
    assert a != J.consistency_sample(ids, 0.2, 6)
    assert J.consistency_sample(ids, 0, 5) == [] and J.consistency_sample([], 0.2, 5) == []


# --- delivery: what the judge receives must hold what the source holds (2026-10-20) ----

COUNT = lambda t: len(t) // 4


def test_one_matching_section_over_the_limit_is_cut_not_dropped():
    # Returned "" before 2026-10-20: the one matching section was dropped for length.
    text = "Filler.\n\n" + ("Background words here. " * 300) + "Mice did better in the trial with carrageenans. " \
        + ("More background words. " * 300)
    claim = "Mice did better with carrageenans."
    out, info = J.chunk(text, claim, limit=50, count=COUNT)
    assert out and COUNT(out) <= 50 and info["cut_to_limit"]
    assert "carrageenans" in out and "Mice did better" in out            # centred on the terms
    assert J.delivery_problems(text, out, claim) == []


def test_the_cut_is_centred_on_a_cited_span_first():
    text = ("Alpha carrageenans sentence. " * 200) + "The exact cited span sits here in the middle. " \
        + ("Omega carrageenans sentence. " * 200)
    out, _ = J.chunk(text, "carrageenans matter", limit=40, count=COUNT,
                     spans=["The exact cited span sits here in the middle."])
    assert "The exact cited span sits here in the middle." in out


def test_no_matching_section_keeps_the_opening_not_nothing():
    # Returned "" before 2026-10-20: no section carried the claim's key terms.
    text = "\n\n".join("Unrelated paragraph %d about nothing the claim names." % i for i in range(400))
    out, info = J.chunk(text, "Carrageenans raised risk (HR 1.03).", limit=100, count=COUNT)
    assert out and COUNT(out) <= 100 and info["opening_kept"] and text.startswith(out)


def test_a_short_source_goes_to_the_judge_whole_and_unchunked(tmp_path, monkeypatch):
    sent = {}

    def claude(client, prefix, rest, model):
        sent["prefix"] = prefix
        return json.dumps({"label": "Supported", "span": "Mice did better in the trial.", "reason": "r"}), \
            {"input": 1, "output": 1, "model": model, "stop": "end_turn"}, 0.0, False
    _wire(monkeypatch, claude, lambda *a: (_ for _ in ()).throw(AssertionError("not called")))
    run = _run_dir(tmp_path)
    full = (run / "sources" / "S1.txt").read_text()
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(run), "--judges", "claude"])
    J.main()
    assert full in sent["prefix"]
    rec = json.loads((run / "replies" / "claude" / "P01.json").read_text())
    assert rec["sources"][0]["chunked"] is False


def test_a_key_term_or_cited_span_the_source_holds_must_be_delivered():
    full = "The cohort was 1,137 patients. Mice did better in the trial. Ten percent dropped out."
    assert J.delivery_problems(full, full, "Mice did better: 1,137 patients.", ["Mice did better in the trial."]) == []
    bad = J.delivery_problems(full, "Ten percent dropped out.", "Mice did better: 1,137 patients.",
                              ["Mice did better in the trial."])
    assert any("1,137" in b for b in bad) and any("cited span" in b for b in bad)
    # a term the source does not hold at all is the judge's to find, not a delivery problem
    assert J.delivery_problems(full, full, "Rats did worse: 9,999 animals.") == []


def test_an_item_whose_source_is_delivered_empty_is_incomplete_and_no_judge_is_called(tmp_path, monkeypatch):
    called = []
    _wire(monkeypatch, lambda *a: called.append(a), lambda *a: called.append(a))
    monkeypatch.setattr(J, "MAX_SOURCE_TOKENS", 10)                # every source is "long"
    monkeypatch.setattr(J, "chunk", lambda text, claim, limit, count, spans=None: ("", {"planted": True}))
    run = _run_dir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(run), "--allow-incomplete"])
    J.main()
    assert called == []
    for j in ("claude", "openai"):
        rec = json.loads((run / "replies" / j / "P01.json").read_text())
        assert rec["label"] == J.INCOMPLETE_SOURCES and rec["human_review"] is True
        assert "delivered empty" in rec["undelivered_sources"][0]["why"]


def test_the_m1_prompt_is_the_frozen_v3():
    """M1 v3 is pinned by sha256 in its runner, as M2 v2 is (2026-10-22)."""
    import hashlib
    assert J.PROMPT_VERSION == "v3"
    assert hashlib.sha256(J.PROMPT.read_bytes()).hexdigest() == J.PROMPT_SHA256
    v2 = (ROOT / "study" / "whu-reliability" / "prompts" / "m1_citation_support_v2.md").read_bytes()
    assert hashlib.sha256(v2).hexdigest().startswith("73e055cb")          # v2 kept, and not v3


def test_a_changed_m1_prompt_stops_before_any_key_or_call(tmp_path, monkeypatch):
    changed = tmp_path / "m1.md"
    changed.write_text(J.PROMPT.read_text(encoding="utf-8") + "\nOne more instruction.\n")
    monkeypatch.setattr(J, "PROMPT", changed)
    monkeypatch.setattr(J, "env_keys", lambda: (_ for _ in ()).throw(AssertionError("a key was read")))
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(tmp_path / "no-such-run")])
    assert J.main() == 6
