#!/usr/bin/env python3
"""Offline tests for the estimate gates (advisor ruling 2026-11-01): keys2.py draft and judge_m2.py print their
estimate and exit non-zero, calling nothing, when the worst case would pass --cap. No network: every client,
key reader and ledger read is replaced.

    backend/venv/bin/python study/whu-reliability/next_phase/test_paid_gates.py
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import keys2 as K  # noqa: E402

_spec = importlib.util.spec_from_file_location("judge_m2_under_test", HERE.parent / "scripts" / "judge_m2.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)


class Boom(AssertionError):
    pass


def no_call(*_a, **_k):
    raise Boom("a paid call was attempted")


class KeysDraftGate(unittest.TestCase):
    def run_draft(self, cap: float, tokens: int):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(K, "OUT", Path(tmp)), \
                mock.patch.object(K, "given", lambda q, gc: {"files": ["x.txt"], "text": "t", "tokens": tokens,
                                                              "cut": None}), \
                mock.patch.object(K.J1, "spent", lambda issue: 0.0), \
                mock.patch.object(K.G, "client", no_call), \
                mock.patch.object(K, "generate", no_call):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = K.draft(cap)
            return rc, out.getvalue(), list(Path(tmp).iterdir())

    def test_worst_over_cap_stops_before_any_call(self):
        rc, out, written = self.run_draft(cap=1.0, tokens=500_000)
        self.assertNotEqual(rc, 0)
        self.assertIn("ESTIMATE keys", out)
        self.assertIn("nothing was called", out)
        self.assertEqual(written, [])

    def test_estimate_printed_before_preflight(self):
        # Under the cap the gate passes and the next step is the preflight (here refused by the stub).
        with self.assertRaises(Boom):
            self.run_draft(cap=10_000.0, tokens=10)


class JudgeM2Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        run = Path(self.tmp.name)
        (run / "a.txt").write_text("An answer.", encoding="utf-8")
        concl = {"id": "C1", "statement": "s", "direction": "d", "size": "z", "certainty": "c", "scope": "p",
                 "quote": "q"}
        (run / "items.json").write_text(json.dumps({
            "answers": {"A-1": {"file": "a.txt"}}, "conclusions": [concl],
            "items": [{"item": "M2-1", "answer": "A-1", "conclusion": "C1"},
                      {"item": "M2-2", "answer": "A-1", "conclusion": "C1"}]}))
        self.run = run
        self.created = []
        created = self.created

        class FakeMessages:
            def count_tokens(self, **_k):
                return types.SimpleNamespace(input_tokens=400_000)

            def create(self, **k):
                created.append(k)
                raise Boom("a paid Claude call was attempted")

        class FakeAnthropic:
            def __init__(self, **_k):
                self.messages = FakeMessages()

        self.fake_anthropic = types.SimpleNamespace(Anthropic=FakeAnthropic)

    def tearDown(self):
        self.tmp.cleanup()

    def main(self, *args):
        argv = ["judge_m2.py", str(self.run), "--consistency-share", "0", "--ledger-issue", "test-gate", *args]
        with mock.patch.dict(sys.modules, {"anthropic": self.fake_anthropic}), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(M.J1, "env_keys", lambda: {"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "x"}), \
                mock.patch.object(M.J1, "spent", lambda issue: 0.0), \
                mock.patch.object(M.J1, "post_openai", no_call), \
                mock.patch.object(M.S, "metered", lambda raw, **_k: raw), \
                mock.patch.object(M.time, "sleep", lambda s: None):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = M.main()
            return rc, out.getvalue()

    def test_worst_over_cap_stops_before_any_call(self):
        rc, out = self.main("--cap", "1")
        self.assertNotEqual(rc, 0)
        self.assertIn("ESTIMATE M2: 4 calls", out)
        self.assertIn("nothing was called", out)
        self.assertEqual(self.created, [])
        self.assertFalse((self.run / "replies").exists())

    def test_estimate_only_calls_nothing(self):
        rc, out = self.main("--cap", "10000", "--estimate")
        self.assertEqual(rc, 0)
        self.assertIn("ESTIMATE M2", out)
        self.assertEqual(self.created, [])

    def test_under_cap_goes_on_to_call(self):
        with self.assertRaises(Boom):
            self.main("--cap", "10000")


if __name__ == "__main__":
    unittest.main()
