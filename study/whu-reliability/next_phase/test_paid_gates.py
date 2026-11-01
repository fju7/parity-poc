#!/usr/bin/env python3
"""Offline tests for the estimate gates and resumption (advisor rulings 2026-11-01).

keys2.py draft, judge_m2.py and judge_google.py print likely and worst-case estimates and exit non-zero, calling
nothing, only when spend so far + the LIKELY estimate passes --cap; a worst case over the cap alone does not stop
them. judge_m2.py and judge_google.py never call again for an item whose reply is saved. No network: every client,
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
import judge_google as G  # noqa: E402
import keys2 as K  # noqa: E402

_spec = importlib.util.spec_from_file_location("judge_m2_under_test", HERE.parent / "scripts" / "judge_m2.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)
S = K.S


class Boom(AssertionError):
    pass


def no_call(*_a, **_k):
    raise Boom("a paid call was attempted")


def ledger(module, rows):
    # Each runner loads its own copy of spend_ledger by file path (judge_m1.py), so the copy it reads is replaced.
    return mock.patch.object(module.S, "entries", lambda: rows)


class KeysDraftGate(unittest.TestCase):
    TOKENS = 10

    def run_draft(self, cap: float, tokens: int | None = None):
        tokens = self.TOKENS if tokens is None else tokens
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

    def bounds(self):
        with mock.patch.object(K, "given", lambda q, gc: {"files": [], "text": "t", "tokens": self.TOKENS, "cut": None}):
            likely, worst, _ = K.estimate(list(K.KEYS1))
        self.assertLess(likely, worst)
        return likely, worst

    def test_likely_over_cap_stops_before_any_call(self):
        likely, _ = self.bounds()
        rc, out, written = self.run_draft(cap=likely / 2)
        self.assertNotEqual(rc, 0)
        self.assertIn("ESTIMATE keys", out)
        self.assertIn("worst $", out)
        self.assertIn("nothing was called", out)
        self.assertEqual(written, [])

    def test_worst_over_cap_alone_runs(self):
        likely, worst = self.bounds()
        with self.assertRaises(Boom):                 # the gate passes; the next step is the preflight (stubbed)
            self.run_draft(cap=(likely + worst) / 2)


def m2_run(tmp: str) -> Path:
    run = Path(tmp)
    (run / "a.txt").write_text("An answer.", encoding="utf-8")
    concl = {"id": "C1", "statement": "s", "direction": "d", "size": "z", "certainty": "c", "scope": "p", "quote": "q"}
    (run / "items.json").write_text(json.dumps({
        "answers": {"A-1": {"file": "a.txt"}}, "conclusions": [concl],
        "items": [{"item": "M2-1", "answer": "A-1", "conclusion": "C1"},
                  {"item": "M2-2", "answer": "A-1", "conclusion": "C1"}]}))
    return run


def save_reply(run: Path, judge: str, item: str) -> None:
    f = run / "replies" / judge / (item + ".json")
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({"item": item, "judge": judge, "label": "Matches"}))


class JudgeM2Gate(unittest.TestCase):
    N_IN = 400_000

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = m2_run(self.tmp.name)
        self.created = []
        created, n_in = self.created, self.N_IN

        class FakeMessages:
            def count_tokens(self, **_k):
                return types.SimpleNamespace(input_tokens=n_in)

            def create(self, **k):
                created.append(k)
                raise Boom("a paid Claude call was attempted")

        class FakeAnthropic:
            def __init__(self, **_k):
                self.messages = FakeMessages()

        self.fake_anthropic = types.SimpleNamespace(Anthropic=FakeAnthropic)

    def tearDown(self):
        self.tmp.cleanup()

    def main(self, *args, rows=()):
        argv = ["judge_m2.py", str(self.run), "--consistency-share", "0", "--ledger-issue", "test-gate", *args]
        with mock.patch.dict(sys.modules, {"anthropic": self.fake_anthropic}), \
                mock.patch.object(sys, "argv", argv), \
                mock.patch.object(M.J1, "env_keys", lambda: {"ANTHROPIC_API_KEY": "x", "OPENAI_API_KEY": "x"}), \
                mock.patch.object(M.J1, "spent", lambda issue: 0.0), \
                mock.patch.object(M.J1, "day_cap_stop", lambda worst: None), \
                mock.patch.object(M.J1, "post_openai", no_call), \
                mock.patch.object(M.S, "metered", lambda raw, **_k: raw), \
                mock.patch.object(M.time, "sleep", lambda s: None), \
                ledger(M, list(rows)):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = M.main()
            return rc, out.getvalue()

    def bounds(self):
        likely = 2 * (M.call_likely("claude", self.N_IN) + M.call_likely("openai", self.N_IN))
        worst = 2 * (M.call_worst("claude", self.N_IN) + M.call_worst("openai", self.N_IN))
        self.assertLess(likely, worst)
        return likely, worst

    def test_likely_over_cap_stops_before_any_call(self):
        likely, _ = self.bounds()
        rc, out = self.main("--cap", str(likely / 2))
        self.assertNotEqual(rc, 0)
        self.assertIn("ESTIMATE M2: 4 calls", out)
        self.assertIn("nothing was called", out)
        self.assertEqual(self.created, [])
        self.assertFalse((self.run / "replies").exists())

    def test_worst_over_cap_alone_runs(self):
        likely, worst = self.bounds()
        with self.assertRaises(Boom):
            self.main("--cap", str((likely + worst) / 2))

    def test_measured_likely_is_used_and_stated(self):
        rows = [{"role": "m2-judge-claude", "issue": "src", "usd": 0.01},
                {"role": "m2-judge-openai", "issue": "src", "usd": 0.03},
                {"role": "m2-judge-openai", "issue": "other", "usd": 99.0}]
        rc, out = self.main("--cap", "0.05", "--likely-from", "src", rows=rows)   # 2 x 0.01 + 2 x 0.03 = 0.08
        self.assertNotEqual(rc, 0)
        self.assertIn("likely $0.08 (measured, src: claude $0.0100 a call (1 calls), openai $0.0300 a call (1 calls))",
                      out)
        self.assertEqual(self.created, [])
        # Under the cap the gate passes; the per-call check then stops before a call whose worst case would pass it.
        rc, out = self.main("--cap", "1", "--likely-from", "src", rows=rows)
        self.assertEqual(rc, 3)
        self.assertNotIn("nothing was called", out)
        self.assertIn("could cost up to", out)
        self.assertEqual(self.created, [])
        with self.assertRaises(Boom):                                             # with room, it calls
            self.main("--cap", "100", "--likely-from", "src", rows=rows)

    def test_estimate_only_calls_nothing(self):
        rc, out = self.main("--cap", "1e9", "--estimate")
        self.assertEqual(rc, 0)
        self.assertIn("ESTIMATE M2", out)
        self.assertEqual(self.created, [])

    def test_saved_replies_are_not_called_again(self):
        for jd in ("claude", "openai"):
            for item in ("M2-1", "M2-2"):
                save_reply(self.run, jd, item)
        rc, out = self.main("--cap", "1e9")
        self.assertEqual(rc, 0)
        self.assertIn("ESTIMATE M2: 0 calls", out)
        self.assertEqual(self.created, [])

    def test_resume_counts_only_unsaved(self):
        save_reply(self.run, "claude", "M2-1")
        save_reply(self.run, "openai", "M2-1")
        rc, out = self.main("--cap", "1e9", "--estimate")
        self.assertEqual(rc, 0)
        self.assertIn("ESTIMATE M2: 2 calls", out)


class JudgeGoogleGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.run = m2_run(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def main(self, *args, rows=()):
        argv = ["judge_google.py", "m2", str(self.run), "--ledger-issue", "test-gate", *args]
        with mock.patch.object(sys, "argv", argv), \
                mock.patch.object(G, "client", no_call), \
                mock.patch.object(G.J1, "spent", lambda issue: 0.0), \
                ledger(G.J2, list(rows)):
            out = io.StringIO()
            with redirect_stdout(out):
                rc = G.main()
            return rc, out.getvalue()

    def bounds(self):
        answers, concl, items = G.J2.load_run(self.run)
        ns = [int(G.approx_tokens("".join(G.J2.build(answers[i["answer"]], concl[i["conclusion"]])))) for i in items]
        likely = sum((n * S.rates(G.MODEL, n)["input"] + 2000 * S.rates(G.MODEL, n)["output"]) / 1e6 for n in ns)
        worst = sum(G.worst_usd(n) for n in ns)
        self.assertLess(likely, worst)
        return likely, worst

    def test_likely_over_cap_stops_before_any_call(self):
        likely, _ = self.bounds()
        rc, out = self.main("--cap", str(likely / 2))
        self.assertNotEqual(rc, 0)
        self.assertIn("ESTIMATE M2: 2 calls", out)
        self.assertIn("nothing was called", out)
        self.assertFalse((self.run / "replies").exists())

    def test_worst_over_cap_alone_runs(self):
        likely, worst = self.bounds()
        with self.assertRaises(Boom):                 # the gate passes; the next step is the preflight (stubbed)
            self.main("--cap", str((likely + worst) / 2))

    def test_measured_likely_is_used_and_stated(self):
        rows = [{"role": "m2-judge-google", "issue": "src", "usd": 0.02}]
        rc, out = self.main("--cap", "0.03", "--likely-from", "src", rows=rows)   # 2 x 0.02 = 0.04
        self.assertNotEqual(rc, 0)
        self.assertIn("likely $0.04 (measured, src: $0.0200 a call (1 calls))", out)

    def test_saved_replies_are_not_called_again(self):
        save_reply(self.run, "google", "M2-1")
        save_reply(self.run, "google", "M2-2")
        rc, out = self.main("--cap", "1e9")
        self.assertEqual(rc, 0)
        self.assertIn("ESTIMATE M2: 0 calls", out)
        self.assertIn("nothing to call", out)

    def test_resume_counts_only_unsaved(self):
        save_reply(self.run, "google", "M2-1")
        rc, out = self.main("--cap", "1e9", "--estimate")
        self.assertEqual(rc, 0)
        self.assertIn("ESTIMATE M2: 1 calls", out)


if __name__ == "__main__":
    unittest.main()
