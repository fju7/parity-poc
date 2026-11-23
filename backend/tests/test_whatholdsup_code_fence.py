"""A model's JSON reply inside a code fence (WHU-S03, 2026-10-22).

The source advocate's re-ask for WHU-S03's S002 was reported as failing on a
reply that was JSON inside a ```json fence. Every parser of a model's JSON reply
now strips a surrounding fence first with one function, jsonio.strip_code_fence:
factcheck_draft.call (every advocate, premise and counterexample call),
audit_stage.parse_json and ruling.parse. The Signal pipeline scripts and the
study judges already stripped fences and are unchanged.

The S002 reply's printed tail also shows an unescaped double quote inside the
quoted passage. That is not JSON with or without a fence, and the last test
records that the fence strip does not rescue it: the re-ask still fails and the
objection keeps QUOTE_NOTE, as before.
"""
import importlib.util
import json
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

import jsonio  # noqa: E402
import ruling as R  # noqa: E402
import source_advocate as SA  # noqa: E402

spec = importlib.util.spec_from_file_location("audit_stage_fence_t", WHU / "audit_stage.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
fc = SA.fc

HELD = ("The panel met four times. A majority of respondents favoured a citizens' assembly with "
        "a right of veto on the texts voted in Parliament (68% in W1, 63% in W2). Turnout fell.")
QUOTE = "a right of veto on the texts voted in Parliament (68% in W1, 63% in W2)"
REPLY = {"source_says": QUOTE, "locator": "Section 'The general public's perception'", "could_not_find": ""}


@pytest.mark.parametrize("text,want", [
    ('```json\n{"a": 1}\n```', '{"a": 1}'),
    ('```JSON\r\n{"a": 1}\r\n```', '{"a": 1}'),
    ('```\n[{"a": 1}]\n```', '[{"a": 1}]'),
    ('  ```json\n{"a": 1}\n```  \n', '{"a": 1}'),
    ('```json {"a": 1}```', '{"a": 1}'),
    ('```json\n{"a": 1}', '{"a": 1}'),                         # no closing fence
    ('```json\n{"a": "```"}\n```', '{"a": "```"}'),            # a fence inside a string survives
    ('{"a": 1}', '{"a": 1}'),
    ('Here it is: ```json\n{"a": 1}\n```', 'Here it is: ```json\n{"a": 1}\n```'),  # not surrounding
    ("", ""),
    (None, ""),
])
def test_strip_code_fence(text, want):
    assert jsonio.strip_code_fence(text) == want


# --- factcheck_draft.call, through the advocate's re-ask -----------------------

class FakeClient:
    def __init__(self, text):
        self.text, self.calls = text, 0
        self.messages = self

    def create(self, **kw):
        self.calls += 1
        return types.SimpleNamespace(
            model=fc.SIGNAL_MODEL, stop_reason="end_turn",
            usage=types.SimpleNamespace(input_tokens=10, output_tokens=5, cache_creation_input_tokens=0,
                                        cache_read_input_tokens=0, server_tool_use=None),
            content=[types.SimpleNamespace(type="text", text=self.text)])

    def stream(self, **kw):                     # max_tokens above STREAM_ABOVE streams
        import contextlib
        msg = self.create(**kw)
        return contextlib.nullcontext(types.SimpleNamespace(get_final_message=lambda: msg))


@pytest.fixture
def model(monkeypatch, tmp_path):
    def use(text):
        client = FakeClient(text)
        monkeypatch.setattr(fc, "_get_client", lambda: client)
        monkeypatch.setattr(fc, "_spend", None)                  # no ledger, no cap file
        monkeypatch.setattr(fc, "_LEDGER_ISSUE", "fence-test")
        monkeypatch.setattr(fc.time, "sleep", lambda s: None)
        return client
    return use


def _brief():
    return {"source": "S002", "mode": "objections", "principal": "the authors",
            "objections": [{"claim_quoted": "c", "objection": "o", "source_says": "not in the text at all"}]}


@pytest.mark.parametrize("wrap", ["```json\n%s\n```", "```\n%s\n```", "%s"])
def test_a_fenced_reply_is_parsed_on_the_first_call(model, wrap):
    client = model(wrap % json.dumps(REPLY, indent=2))
    assert fc.call("s", "u", search=False, label="advocate-requote:S002") == REPLY
    assert client.calls == 1                                       # no re-ask for the fence


def test_the_advocate_re_ask_takes_a_fenced_reply(model):
    client = model("```json\n%s\n```" % json.dumps(REPLY))
    b = _brief()
    out = SA.check_quotations("x", [b], {"S002": HELD})
    o = b["objections"][0]
    assert out[0]["result"] == "in the held text after one re-ask"
    assert o["source_says"] == QUOTE and o["quotation_check"] == {"in_held_text": True, "asked": 2}
    assert client.calls == 1


def test_the_s002_shape_an_unescaped_quote_is_still_not_json(model):
    # The tail printed on 2026-10-23 ended '...Parliament" (68% in W1, 63% in W2).",
    # "locator": ...}\n```': a double quote inside the string, unescaped.
    bad = ('```json\n{"source_says": "chosen citizens, with a right of veto on the texts voted in '
           'Parliament" (68% in W1, 63% in W2).", "locator": "x", "could_not_find": ""}\n```')
    client = model(bad)
    b = _brief()
    out = SA.check_quotations("x", [b], {"S002": HELD})
    assert out[0]["result"] == SA.QUOTE_NOTE and out[0]["re_ask"] == ""
    assert client.calls == fc.JSON_RETRIES + 1                     # as on S002: three attempts


# --- the audit and the ruling parsers -----------------------------------------

def test_audit_parse_json_strips_a_fence():
    v = {"verdicts": [{"id": "u1", "verdict": "holds"}]}
    for wrap in ("```json\n%s\n```", "```JSON\n%s\n```", "```\n%s\n```", "%s"):
        assert A.parse_json(wrap % json.dumps(v)) == v


def test_ruling_parse_strips_a_fence():
    r = {"ruling": "reject", "text": None, "reason": "the source says so", "quotation": 1}
    for wrap in ("```json\n%s\n```", "```JSON\n%s\n```", "%s"):
        assert R.parse("gate", wrap % json.dumps(r), 1)["ruling"] == "reject"


# Ruling 1 (2026-11-23): raw=True hands the orchestrator the text, never a salvaged pick among several values.

def test_raw_call_returns_the_text_unparsed_with_no_retry(model):
    two = '{"decision": "out_of_scope"}\n\nWait. Reclassifying:\n\n{"decision": "not_material"}'
    client = model(two)
    assert fc.call("s", "u", search=False, label="discover", raw=True) == two
    assert client.calls == 1
    client = model(two)
    assert isinstance(fc.call("s", "u", search=False, label="x"), dict)     # the default path still salvages


def test_discover_paid_path_reasks_a_two_object_reply(model, tmp_path, monkeypatch):
    sys.path.insert(0, str(WHU))
    from orch import model_steps as M
    replies = iter(['{"sources": []}\n\nWait:\n\n{"sources": []}', '{"sources": []}'])

    class Seq(FakeClient):
        def create(self, **kw):
            self.text = next(replies)
            return FakeClient.create(self, **kw)
    client = Seq("")
    monkeypatch.setattr(fc, "_get_client", lambda: client)
    monkeypatch.setattr(fc, "_spend", None)
    monkeypatch.setattr(fc, "_LEDGER_ISSUE", "fence-test")
    ask = lambda p, m, r: fc.call("s", p, search=False, label=r, max_tokens=m, raw=True)
    events = []
    ask.note_malformed = lambda role, ev, text: events.append(ev)
    assert M.ask_json(ask, "P", 100, "discover") == {"sources": []}
    assert client.calls == 2 and events == ["malformed", "reask"]


# Ruling 3 after attempt 11 (2026-11-23): lean / orchestrated mode takes exactly one JSON value of the type the
# prompt asks for, re-asks once, then None; non-lean behaviour unchanged.

TWO = '{"label": "a"}\n\nWait, reconsidering:\n\n{"label": "b"}'


def _seq(monkeypatch, texts):
    texts = list(texts)
    seen = []

    class Seq(FakeClient):
        def create(self, **kw):
            seen.append(kw["messages"][0]["content"])
            self.text = texts[min(len(seen), len(texts)) - 1]
            return FakeClient.create(self, **kw)
    client = Seq("")
    monkeypatch.setattr(fc, "_get_client", lambda: client)
    monkeypatch.setattr(fc, "_spend", None)
    monkeypatch.setattr(fc, "_LEDGER_ISSUE", "fence-test")
    monkeypatch.setattr(fc.time, "sleep", lambda s: None)
    monkeypatch.setattr(fc, "MALFORMED_EVENTS", [])
    return client, seen


def test_lean_two_objects_reasked_once_then_none(monkeypatch, tmp_path):
    monkeypatch.setenv("WHU_LEAN", "1")
    log = tmp_path / "m.jsonl"
    monkeypatch.setenv("WHU_ORCH_MALFORMED_LOG", str(log))
    client, seen = _seq(monkeypatch, [TWO, TWO, '{"label": "never"}'])
    assert fc.call("s", "U", search=False, label="conclusions") is None
    assert client.calls == 2 and seen[1] == "U" + fc.REASK_ONE % "object"
    assert "Return exactly one JSON object and nothing else." in seen[1]
    assert [e["event"] for e in fc.MALFORMED_EVENTS] == ["malformed", "reask", "malformed"]
    assert [json.loads(l)["event"] for l in log.read_text().splitlines()] == ["malformed", "reask", "malformed"]


def test_lean_reask_then_a_good_reply_is_taken(monkeypatch):
    monkeypatch.setenv("WHU_LEAN", "1")
    client, _ = _seq(monkeypatch, [TWO, '```json\n{"label": "b"}\n```'])
    assert fc.call("s", "U", search=False, label="x") == {"label": "b"} and client.calls == 2


def test_strict_mode_is_on_in_lean_or_inside_an_orchestrator_step(monkeypatch):
    for k in ("WHU_LEAN", "WHU_ORCH_STEP"):
        monkeypatch.delenv(k, raising=False)
    assert not fc.strict_json_mode()
    monkeypatch.setenv("WHU_ORCH_STEP", "advocate")
    assert fc.strict_json_mode()
    monkeypatch.delenv("WHU_ORCH_STEP")
    monkeypatch.setenv("WHU_LEAN", "1")
    assert fc.strict_json_mode()


def test_lean_array_prompt_takes_one_array_and_refuses_an_object(monkeypatch):
    monkeypatch.setenv("WHU_LEAN", "1")
    sysmsg = "RETURN ONLY a JSON array. One object per objection:"
    client, seen = _seq(monkeypatch, ['[{"a": 1}, {"a": 2}]'])
    assert fc.call(sysmsg, "U", search=False, label="advocate") == [{"a": 1}, {"a": 2}] and client.calls == 1
    client, seen = _seq(monkeypatch, ['{"a": 1}', '[{"a": 1}]'])
    assert fc.call(sysmsg, "U", search=False, label="advocate") == [{"a": 1}]
    assert seen[1].endswith("Return exactly one JSON array and nothing else.")


def test_lean_prose_around_one_object_is_malformed(monkeypatch):
    monkeypatch.setenv("WHU_LEAN", "1")
    client, _ = _seq(monkeypatch, ['Here you go: {"label": "a"}', 'Sure {"label": "a"}'])
    assert fc.call("s", "U", search=False, label="x") is None and client.calls == 2


def test_non_lean_behaviour_is_unchanged(monkeypatch):
    for k in ("WHU_LEAN", "WHU_ORCH_STEP"):
        monkeypatch.delenv(k, raising=False)
    client, _ = _seq(monkeypatch, [TWO])
    assert isinstance(fc.call("s", "U", search=False, label="x"), dict) and client.calls == 1   # salvaged, as before
    assert fc.MALFORMED_EVENTS == []


def test_every_prompt_that_asks_for_an_array_is_read_as_one():
    import re
    srcs = [(ROOT / "backend/scripts/signal/factcheck_draft.py"), WHU / "source_advocate.py", WHU / "counterexample.py"]
    for p in srcs:
        for line in p.read_text().splitlines():
            if re.search(r"(?i)return only a json array", line):
                assert fc.expected_kind(line, "") == "array"
            if re.search(r"(?i)return only (a )?json( object)?:", line):
                assert fc.expected_kind(line, "") == "object"
