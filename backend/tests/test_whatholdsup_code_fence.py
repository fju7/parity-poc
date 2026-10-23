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
