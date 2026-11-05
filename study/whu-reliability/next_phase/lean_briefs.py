#!/usr/bin/env python3
"""Lean four-question test: the drafting prompts, made from round 1's briefs.

    python3 lean_briefs.py            write next_phase/lean_briefs.md

Advisor's ruling 2 of 2026-11-05: one fresh subagent per question, given only
round 1's brief for that question (quarterly/round1_briefs.md, unchanged) plus
the lean switch. The changes are mechanical and listed here, in SUBS, each
asserted to apply exactly once per brief, so the prompt is round 1's brief
except where this list says. lean_test_rule.md §1 points here.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "quarterly" / "round1_briefs.md"
OUT = HERE / "lean_briefs.md"

LEAN_SWITCH = """LEAN SWITCH (lean four-question test, "lean + machine scope notes"; added to round 1's brief)
- Every command runs with WHU_LEAN=1 in its environment: write `WHU_LEAN=1 py ...` for every `py` command. A command run without it is not this run.
- Read docs/whatholdsup-process.md §4.6 and §4.6.1 as well as §4.5. Where they differ from §4.5, §4.6 and §4.6.1 govern.
- Protected sentences are GENERATED, never written by hand: the question restatement and what we held, read and did not read come from issue.json and sources.json (`access.state`, `access.sections`, `access.not_read`); what we searched and did not search comes from a top-level `"search": {{"searched": [...], "not_searched": [...]}}` in sources.json. Fill those records, then paste the output of `WHU_LEAN=1 py backend/scripts/whatholdsup/lean_sentences.py {slug} render`. The readers' list is pasted from `WHU_LEAN=1 py backend/scripts/whatholdsup/coverage_check.py {slug} render`. A protected sentence written by hand is cut by the audit and stops the preflight.
- No person takes part in this run. Wherever this brief says a person, Fred or OPERATOR STEPS is needed, you STOP instead: record in study_log.md exactly which step needed a person and why, and end with the REPORT. Never write human_reads.jsonl, person_decisions.md, protected_signoffs.json or any signed field naming a person.
"""

# Advisor ruling, 2026-11-05 (after Q1-01's drafter grepped two study issues' sources.json):
# added explicitly to the prompts for Q1-02, Q1-03 and Q1-04, before each starts.
ADDED_AFTER_Q1_01 = ("- Do not open, search, list or grep inside any issues/ folder other than your own; for format "
                     "examples use the process doc and backend/scripts only.\n")
ADDED_ANCHOR = "- Tests or fixtures that name a round-1 question. Running the suite through the pre-commit hook is allowed.\n"

CAPS_R1 = re.compile(r"CAPS \(never.*?\n(?=- A stage that prints NOT STARTED)", re.S)
CAPS_LEAN = """CAPS (never --no-verify, --waive, --past-cap, --past-issue-cap or WHU_SPEND_OVERRIDE)
- Run cap: $10 for this issue (lean test, validity_plan.md §10). Where a stage takes --cap, pass ($10 minus this issue's spend: `py backend/scripts/spend_ledger.py --issue {slug}`). Hitting it is a result, not a reason to raise it.
- Day cap (caps.json default_per_day): $60 per UTC day, covering EVERY ledger line, including other sessions. Never edit caps.json yourself. Before every paid stage, check that today's ledger total plus the stage's printed estimate is at most $50; if not, do not start it: record it and stop.
"""


def subs(n: str, r1: str, lean: str, nid: str | None = None) -> list[tuple[str, str]]:
    """(old, new) pairs for question n (01..04); each must occur in round 1's brief.
    NID: the lean folder's number (n, or n + "r" for a re-run)."""
    nid = nid or n
    return [
        ("You are a FRESH drafting session: What Holds Up (WHU) quarterly round 1, question WHU-Q1-%s." % n,
         "You are a FRESH drafting session: What Holds Up (WHU) lean four-question test (\"lean + machine scope "
         "notes\"), question WHU-Q1-%s." % n),
        ("issues/WHU-Q1-%s-%s/" % (n, r1), "issues/WHU-L1-%s-%s/" % (nid, lean)),
        ("It is a quarterly-round question, outside the reliability study.",
         "It is a lean-test question (round 1's question, asked again of lean WHU), outside the reliability study."),
        ("- Any other issue's case folder, including the three other round-1 questions (issues/WHU-Q1-*), and their git history.",
         "- Any other issue's case folder, including all four round-1 questions (issues/WHU-Q1-*, this question's "
         "round-1 folder too) and the other lean-test questions (issues/WHU-L1-*), and their git history."),
        ("If you open one of the paths above by accident, stop and tell Fred which one.",
         "If you open one of the paths above by accident, stop and report which one."),
        ("WHU-Q1-%s (quarterly round 1): <what>" % n, "WHU-L1-%s (lean test): <what>" % nid),
        ("~/Projects/whu-study-private/WHU-Q1-%s-%s/" % (n, r1), "~/Projects/whu-study-private/WHU-L1-%s-%s/" % (nid, lean)),
        ("- spend on %s and on all five round-1 ledger issues;" % r1,
         "- spend on %s and on all four lean-test ledger issues (whu-lean-q1-01 to -04);" % lean if nid == n else
         "- spend on %s and on all lean-test ledger issues (whu-lean-q1-01 to -04 and %s);" % (lean, lean)),
        ("   - Write the protected sentences (§4.5, fix 1) plainly: the question restatement and what we held, read, searched or did not read.",
         "   - Protected sentences: GENERATED (see LEAN SWITCH): fill the records and paste `lean_sentences.py %s render`." % lean),
    ]


# Advisor ruling, 2026-11-05 (option 2): Q1-02 is re-run with a fresh drafter in a new
# folder, on the code frozen at 4abcab6; the earlier attempt is named as forbidden.
RERUN_LINE = ("- The earlier lean attempt at this question: issues/WHU-L1-{n}-whu-lean-q1-{n}/, its private archive "
              "~/Projects/whu-study-private/WHU-L1-{n}-whu-lean-q1-{n}/, its library record "
              "backend/data/whatholdsup/library/issues/whu-lean-q1-{n}.json, and its git history.\n")


# Advisor's rulings of 5 November 2026 after Q1-04 (4, 5): all four questions are
# re-run with fresh drafters on the second freeze, in new folders ("b"). The
# prompt is the lean prompt except the slug/folder, the line forbidding every
# earlier lean attempt at the question, and these two lines.
SECOND_FREEZE_LINES = (
    "- Never run a stage twice in parallel: start a paid stage only after the previous run of every stage has "
    "finished, and never start a second copy of a stage that is still running.\n"
    "- Never fetch, add or switch to another edition of a source yourself, and never rebind a sentence to one: "
    "a gate recency finding about a newer edition is settled by code (process doc §4.6.1, rule 3b).\n")
EARLIER = {"01": ["01"], "02": ["02", "02r"], "03": ["03"], "04": ["04"]}


def earlier_line(n: str) -> str:
    """The DO NOT READ line naming every earlier lean attempt at question N."""
    xs = EARLIER[n]
    return ("- The earlier lean attempts at this question: %s; their private archives %s; their library records %s; "
            "and their git history.\n"
            % (", ".join("issues/WHU-L1-%s-whu-lean-q1-%s/" % (x, x) for x in xs),
               ", ".join("~/Projects/whu-study-private/WHU-L1-%s-whu-lean-q1-%s/" % (x, x) for x in xs),
               ", ".join("backend/data/whatholdsup/library/issues/whu-lean-q1-%s.json" % x for x in xs)))


def make(n: str, r1_block: str, suffix: str = "", second: bool = False) -> tuple[str, list[str]]:
    r1, lean = "whu-quarterly-r1-%s" % n, "whu-lean-q1-%s%s" % (n, suffix)
    out, log = r1_block, []
    for old, new in subs(n, r1, lean, n + suffix):
        c = out.count(old)
        assert c >= 1, (n, old[:70])
        out = out.replace(old, new)
        log.append("%d x %r -> %r" % (c, old[:80], new[:80]))
    assert len(CAPS_R1.findall(out)) == 1, n
    out = CAPS_R1.sub(lambda m: CAPS_LEAN.format(slug=lean), out)
    log.append("CAPS block -> lean caps ($10 run cap, $60 day cap, $50 room rule)")
    c = out.count(r1)
    out = out.replace(r1, lean)
    log.append("%d x slug %s -> %s" % (c, r1, lean))
    anchor = "\nTHE SEQUENCE\n"
    assert out.count(anchor) == 1
    switch = LEAN_SWITCH.format(slug=lean) + (SECOND_FREEZE_LINES if second else "")
    out = out.replace(anchor, "\n" + switch + anchor)
    log.append("LEAN SWITCH block inserted before THE SEQUENCE")
    if second:
        log.append("LEAN SWITCH: two lines added (advisor's rulings after Q1-04, 4): %r" % SECOND_FREEZE_LINES.strip())
    if n != "01" or second:
        assert out.count(ADDED_ANCHOR) == 1
        out = out.replace(ADDED_ANCHOR, ADDED_ANCHOR + ADDED_AFTER_Q1_01)
        log.append("DO NOT READ: one line added (advisor ruling 2026-11-05, after Q1-01): %r" % ADDED_AFTER_Q1_01.strip())
    if second:
        line = earlier_line(n)
        out = out.replace(ADDED_AFTER_Q1_01, ADDED_AFTER_Q1_01 + line)
        log.append("DO NOT READ: the line forbidding every earlier lean attempt (advisor's rulings after Q1-04, 5): %r"
                   % line.strip())
        if n == "01":
            log.append("DO NOT READ: Q1-01's re-run also carries the line added for Q1-02 to Q1-04 after Q1-01 "
                       "(no other issues/ folder): it forbids the earlier attempt's folder too")
    elif suffix:
        line = RERUN_LINE.format(n=n)
        out = out.replace(ADDED_AFTER_Q1_01, ADDED_AFTER_Q1_01 + line)
        log.append("DO NOT READ: one line added for the re-run (advisor ruling 2026-11-05, option 2): %r" % line.strip())
    assert "quarterly-r1" not in out and "$250" not in out and "$25 per" not in out, n
    return out, log


def main() -> int:
    text = SRC.read_text(encoding="utf-8")
    blocks = re.findall(r"## Brief: WHU-Q1-(\d\d) \([^)]*\)\n\n```text\n(.*?)```", text, re.S)
    assert [b[0] for b in blocks] == ["01", "02", "03", "04"]
    parts = ["# Lean four-question test: drafting prompts\n",
             "Made by `lean_briefs.py` from `quarterly/round1_briefs.md` (sha256 %s), advisor's ruling 2 of 2026-11-05. "
             "Each prompt below is given verbatim to one fresh subagent; its model and the time it started are in "
             "`lean_test_log.md`. A drafting subagent never reads this file.\n" % hashlib.sha256(text.encode()).hexdigest()]
    for n, block in blocks:
        prompt, log = make(n, block)
        parts.append("## WHU-Q1-%s (whu-lean-q1-%s)\n\nChanges from round 1's brief:\n\n%s\n\nPrompt sha256: `%s`\n\n```text\n%s```\n"
                     % (n, n, "\n".join("- " + x for x in log), hashlib.sha256(prompt.encode()).hexdigest(), prompt))
    # the re-run of Q1-02 (advisor ruling 2026-11-05, option 2), on the code frozen at 4abcab6
    n, block = blocks[1]
    prompt, log = make(n, block, "r")
    parts.append("## WHU-Q1-%sr (whu-lean-q1-%sr): re-run with a fresh drafter on the frozen code (4abcab6)\n\n"
                 "Changes from round 1's brief:\n\n%s\n\nPrompt sha256: `%s`\n\n```text\n%s```\n"
                 % (n, n, "\n".join("- " + x for x in log), hashlib.sha256(prompt.encode()).hexdigest(), prompt))
    # all four re-run on the second freeze (advisor's rulings after Q1-04, 4-5)
    for n, block in blocks:
        prompt, log = make(n, block, "b", second=True)
        parts.append("## WHU-Q1-%sb (whu-lean-q1-%sb): re-run with a fresh drafter on the second freeze\n\n"
                     "Changes from round 1's brief:\n\n%s\n\nPrompt sha256: `%s`\n\n```text\n%s```\n"
                     % (n, n, "\n".join("- " + x for x in log), hashlib.sha256(prompt.encode()).hexdigest(), prompt))
    OUT.write_text("\n".join(parts), encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
