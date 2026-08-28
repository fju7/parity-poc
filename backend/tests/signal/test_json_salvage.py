"""_first_json_value: recover a role's answer from a response wrapped in prose.

WHY
---
On 2026-08-28 a MONALEESA-2 source check burned three API calls -- the first
and two retries -- and returned nothing. The error line printed the tail of the
response it had rejected, and the tail was a well-formed JSON array followed by
a closing code fence. The model had answered correctly, three times, and the
parser threw all three away.

The cause: the salvage scanned for the first '{' or '[' anywhere in the text
and committed to it. Responses in this file are about hazard ratios and
confidence intervals, so their prose is full of brackets -- "[0.63, 0.93]",
"[1]", "```json". One bracket in a preamble and the salvage started at the
wrong character.

The second failure was subtler and is the one these tests exist for: a
preamble like "Per the paper [1], the result:" contains a VALID JSON array.
Returning [1] is worse than returning nothing. Nothing makes the caller retry;
[1] is accepted as "this role found no findings" and the gate reports a clean
pass on a check that never happened.

Run: python3 backend/tests/signal/test_json_salvage.py
"""

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
GATE = HERE.parents[1] / "scripts" / "signal" / "factcheck_draft.py"

_spec = importlib.util.spec_from_file_location("factcheck_draft", GATE)
fc = importlib.util.module_from_spec(_spec)
sys.modules["factcheck_draft"] = fc
_spec.loader.exec_module(fc)

CASES = [
    ("a bare array",
     '[{"a": 1}]',
     [{"a": 1}]),
    ("a fenced array",
     'Here you go:\n```json\n[{"a": 1}]\n```',
     [{"a": 1}]),
    ("an unlabelled fence",
     '```\n{"a": 1}\n```',
     {"a": 1}),
    ("a confidence interval in the preamble",
     'See the interval [0.63, 0.93] below.\n```json\n[{"hr": 0.76}]\n```',
     [{"hr": 0.76}]),
    ("a citation marker that is itself valid JSON",
     'Per the paper [1], the result:\n[{"p": 0.008}]',
     [{"p": 0.008}]),
    ("a brace in the preamble",
     'The set {a,b} matters. Result: [{"x": 2}]',
     [{"x": 2}]),
    ("prose after the fence",
     '```json\n[{"z": 9}]\n```\nThat is all.',
     [{"z": 9}]),
    ("brackets inside a string value",
     '[{"note": "range [1,2] and {x}"}]',
     [{"note": "range [1,2] and {x}"}]),
    ("an empty result, which is a real answer",
     'No findings.\n```json\n[]\n```',
     []),
    ("an empty array before the real one",
     'Checked [] so far. Result:\n[{"q": 1}]',
     [{"q": 1}]),
    ("an array of scalars is not an answer",
     'Values [1, 2, 3] and nothing else.',
     None),
    ("no JSON at all",
     'I could not complete this.',
     None),
    ("the response that actually failed on 2026-08-28",
     'Verified against NEJM.\n```json\n[\n  {"claim": "HR 0.76", "verdict": "VERIFIED",\n'
     '   "url": "https://www.nejm.org/doi/full/10.1056/NEJMoa2114663", "note": null}\n]\n```',
     [{"claim": "HR 0.76", "verdict": "VERIFIED",
       "url": "https://www.nejm.org/doi/full/10.1056/NEJMoa2114663", "note": None}]),
]


def main() -> int:
    ok = bad = 0
    for name, raw, want in CASES:
        got = fc._first_json_value(raw)
        parsed = json.loads(got) if got else None
        if parsed == want:
            print("  ok   " + name)
            ok += 1
        else:
            print("  FAIL " + name)
            print("         got  %r" % (parsed,))
            print("         want %r" % (want,))
            bad += 1
    print("\n  %d passed, %d failed" % (ok, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
