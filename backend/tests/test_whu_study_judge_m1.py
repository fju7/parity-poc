"""The reliability study's M1 runner: the rules it applies, not the prompt.

Rulings of 19 October 2026 (protocol, "Rulings from prep round 1"): a refusal
is retried once unchanged, then recorded as REFUSED and sent to a person; an
Absent on an abstract-only snapshot is NOT_VERIFIABLE_ABSTRACT; a source over
150,000 tokens is cut to the sections containing the claim's key terms and the
item marked CHUNKED. No API is called here."""
import importlib.util
import json
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
    monkeypatch.setattr(sys, "argv", ["judge_m1.py", str(run)])
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
