"""The orchestrator's step table (docs/whu-orchestrator.md §2.1). Fixed in code: the order, what each step
owns, the models it may call, and its limits. Nothing here is chosen at run time.

`cmds(ctx)` lists the existing stages a step runs, each as an argv list the step builds itself (no command is
typed by anyone); `code` names the orchestrator function that does the rest (orchestrator.py, STEP_CODE).
"""
from __future__ import annotations

from dataclasses import dataclass, field

GATE_MODEL = "claude-sonnet-4-6"       # factcheck_draft's (signal_model.DEFAULT_MODEL)
CURRENT = "claude-opus-5-5"            # ruling.MODEL, audit_stage.MODEL, lean.CURRENT
SMALL = "claude-sonnet-5-5"            # lean.SMALL
GOOGLE = "gemini-4-argon"              # the overstatement check
DRAFT_MODEL = CURRENT                  # the new model steps that replace the drafting agent
STEP_MODEL = SMALL


@dataclass(frozen=True)
class Step:
    name: str
    kind: str                          # "code" | "model" | "stage" (existing paid stages) | "mixed"
    owns: tuple = ()
    models: tuple = ()
    max_calls: int = 0                 # 0: no model call at all
    cap_usd: float = 0.0
    repeat_group: bool = False         # steps 12-18: re-run in order when a later step changed the page
    cmds: tuple = field(default_factory=tuple)   # argv templates; {slug} {page} {gate} {cap} {first} {stamp}
    code: str = ""


PY = "backend/venv/bin/python3"
W = "backend/scripts/whatholdsup/"
RULINGS = ("rulings/*",)
PAGE = ("draft/{slug}.html", "draft/page.json")

# Reply limits (max output tokens) of the steps that replace the drafter, set by the advisor's ruling of 2026-11-07:
# each at least the largest matching output in the stored lean records (Q1-01c/02b/03b/04c) plus 50%, and here about
# twice it, since the first real premise reply (orchestrator trial 1) passed 1,500 against a 1,012-token basis.
# Basis: study/whu-reliability/next_phase/results/orchestrator/reply_limits.json (3 characters per token).
# Since the design review of 2026-11-26 (advisor's ruling 1) these come from the one table, reply_limits.LIMITS,
# with its measured basis; the keys below are kept for the steps that read them.
import reply_limits as _RL  # noqa: E402
REPLY_LIMITS = {
    "premise": _RL.limit("premise"),
    "discover": _RL.limit("fc:discover"),
    "draft": _RL.limit("draft"),
    "coverage": _RL.limit("coverage"),
    "judgement_sentence": _RL.limit("judgement-sentence"),
    "overstatement": _RL.limit("overstatement"),
    "belief": _RL.limit("fc:belief-outlet"),
    "premise_reading": _RL.limit("premise-reading"),
}

# Field length limits (characters, whitespace collapsed) of the same steps' replies: each the larger of the first build's
# limit and twice the longest matching value in the stored lean records (Q1-01c/02b/03b/04c) and trial 1's real premise
# reply, rounded up to 100 (advisor's ruling 2026-11-07; attempt 2 stopped on 'measured' at 434 against 400).
# Basis: study/whu-reliability/next_phase/results/orchestrator/field_limits.json.
FIELD_LIMITS = {
    "premise.belief": 700,
    "premise.kill_condition": 1000,
    "premise.reader_with_a_decision": 700,
    "premise.scope_covers": 1400,
    "premise.scope_out.what": 400,
    "premise.scope_out.why": 300,
    "premise.measured": 900,
    "premise.assessed": 800,
    "premise.weighs": 40,
    "discover.title": 400,
    "discover.first_author": 120,
    "discover.container": 200,
    "discover.url": 500,
    "discover.why": 300,
    "draft.title": 200,
    "draft.heading": 200,
    "draft.sentence": 1000,
    "coverage.why": 700,
    "coverage.element": 400,
    "coverage.sentence": 1000,
    "judgement.sentence": 1000,
}

STEPS: tuple[Step, ...] = (
    Step("provenance", "code", code="provenance"),
    Step("premise", "model", models=(DRAFT_MODEL,), max_calls=2, cap_usd=0.20,
         cmds=((PY, W + "premise.py", "init", "{slug}"),), code="premise"),
    Step("discover", "model", models=(GATE_MODEL,), max_calls=3, cap_usd=1.50,
         code="discover"),
    # advisor's ruling 1 after attempt 24: discovery's registry lookups are their own step, so a resume after a
    # registry outage repeats them alone and reuses the saved proposals (orchestrator.code_confirm)
    Step("confirm", "code", code="confirm"),
    # --open-copies: a source whose own copy cannot be held falls back to a permitted open copy (ruling on P107)
    Step("acquire", "code", cmds=((PY, W + "acquire_sources.py", "{slug}", "--landing-pdfs", "--open-copies", "--out", "{case}/orchestrator/acquire.json"), (PY, W + "source_store.py", "{slug}", "status"),
               (PY, W + "errata.py", "{slug}"), (PY, W + "sweep_sources.py", "resolve", "{slug}", "--write"),
               (PY, W + "canary.py", "{slug}")), code="acquire"),
    Step("draft", "model", models=(DRAFT_MODEL,), max_calls=2, cap_usd=2.50, code="draft"),
    Step("bind", "code", cmds=((PY, W + "bindings.py", "{slug}", "scan"),), code="bind"),
    Step("judgements", "mixed", models=(SMALL, CURRENT, STEP_MODEL), max_calls=400, cap_usd=3.00,
         cmds=((PY, W + "ruling.py", "judgements", "{slug}", "--cap", "{cap}"),), code="judgements"),
    # Fred's terms B3 / B4 after attempt 23: the premise rows filled after reading, by bounded model steps checked by
    # code (orch/premise_reading.py). belief: one web-search call (+ one re-ask), and once more for different outlets
    # if none is confirmed (ruling D on P117); premise_reading: one call (+ one).
    # ruling D on P117: one re-ask for different outlets when round 1 confirms none (round 2 + its re-ask: 4 calls)
    Step("belief", "model", models=(GATE_MODEL,), max_calls=4, cap_usd=2.00, code="belief"),
    Step("premise_reading", "model", models=(CURRENT,), max_calls=2, cap_usd=0.40, code="premise_reading"),
    # Advisor's ruling 4 on P140: coverage runs AFTER premise_reading (and judgements), so every source those make
    # relied on -- named in what_the_sources_show, or bound by judgement sentences -- has its headline units decided
    # (02za's S003 and 02zc's S004 were named at premise_reading after coverage had run, and stayed undecided).
    Step("coverage", "model", models=(STEP_MODEL,), max_calls=240, cap_usd=1.20, code="coverage"),   # 60 units: an element retry, each try re-asked once if malformed (ruling 1)
    Step("corrections_3b", "code", models=(CURRENT,), max_calls=20, cap_usd=0.50, code="corrections"),   # CURRENT: ruling.py dangling
    Step("commit_3b", "code", code="commit"),
    Step("gate", "stage", models=(GATE_MODEL,),
         max_calls=40, cap_usd=3.00,
         cmds=((PY, "backend/scripts/signal/factcheck_draft.py", "{page}", "--dry-run"),
               (PY, "backend/scripts/signal/factcheck_draft.py", "{page}", "--report", "{gate}"))),
    Step("advocate", "stage", models=(SMALL, GATE_MODEL, CURRENT), max_calls=120, cap_usd=2.50,
         cmds=((PY, W + "source_advocate.py", "run", "{slug}", "--page", "{page}"),
               (PY, W + "ruling.py", "advocate", "{slug}")), code="apply"),
    Step("omissions", "stage", models=(CURRENT, GATE_MODEL), max_calls=120, cap_usd=2.50,  # GATE_MODEL: source_advocate.reask_omission's re-asks (fc.call)
         cmds=((PY, W + "ruling.py", "omissions", "{slug}"),), code="apply"),
    Step("findings", "stage", models=(CURRENT,),
         max_calls=200, cap_usd=2.50, repeat_group=True,
         cmds=((PY, W + "findings.py", "{slug}", "--report", "{gate}", "--scan"),
               (PY, W + "ruling.py", "gate", "{slug}")), code="apply"),
    Step("conclusions", "stage", models=(GATE_MODEL, CURRENT), max_calls=60, cap_usd=1.00, repeat_group=True,  # GATE_MODEL: conclusion_judge.JUDGE_MODEL (fc.call)
         cmds=((PY, W + "conclusion_judge.py", "{slug}"), (PY, W + "ruling.py", "conclusions", "{slug}")),
         code="apply"),
    Step("audit", "stage", models=(SMALL, CURRENT),
         max_calls=600, cap_usd=4.00, repeat_group=True,
         cmds=((PY, W + "audit_stage.py", "run", "{slug}", "--cap", "{cap}"),), code="audit"),
    Step("overstatement", "model", models=(GOOGLE, CURRENT), max_calls=420, cap_usd=2.50, repeat_group=True,
         code="overstatement"),                                     # CURRENT: ruling.py dangling (20 calls, $0.50)
    Step("corrections", "code", models=(CURRENT,), max_calls=20, cap_usd=0.50, repeat_group=True,
         code="corrections"),                                                       # CURRENT: ruling.py dangling
    Step("final_gate", "stage", models=(GATE_MODEL, CURRENT), max_calls=200, cap_usd=2.00, repeat_group=True,
         cmds=((PY, "backend/scripts/signal/factcheck_draft.py", "{page}", "--changed-since", "{gate}",
                "--dry-run"),
               (PY, "backend/scripts/signal/factcheck_draft.py", "{page}", "--changed-since", "{gate}",
                "--report", "{gate}"),
               (PY, W + "findings.py", "{slug}", "--report", "{gate}", "--scan"),
               (PY, W + "ruling.py", "gate", "{slug}")), code="apply"),
    Step("commit_8", "code", repeat_group=True, code="commit"),
    Step("changecheck", "stage", models=(GATE_MODEL, CURRENT), max_calls=60, cap_usd=1.00, repeat_group=True,  # GATE_MODEL: changecheck.py's review (fc.call)
         cmds=((PY, W + "changecheck.py", "{slug}", "--page", "{page}", "--before", "{first}"),
               (PY, W + "ruling.py", "changecheck", "{slug}"),
               (PY, W + "changecheck_coverage.py", "{slug}", "--first", "{first}", "--out",
                "{case}/orchestrator/changecheck_coverage.json")), code="apply"),
    # Fred's term B2 after attempt 23: every quoted passage on the final page matched verbatim in held text, by code.
    Step("quotations", "code", code="quotations"),
    Step("preflight", "code", cmds=((PY, W + "publish.py", "check", "{slug}"),), code="preflight"),
    Step("archive", "code", code="archive"),
)

# Exit codes (advisor's rulings 2026-11-07, (a) and after attempt 6). For each stage script, what each exit means to
# the run: "ok" continues; "proof" continues only with positive proof the command completed (PROOF below: an output
# file written in this step, parseable, whose content matches the exit -- an uncaught exception also exits 1);
# "rerun" runs the command once more, and a second such exit stops the run Not Ready. Any exit not listed stops.
# (The preflight's `publish.py check` is read by its output, Ready or Not Ready, as before.)
EXITS = {
    "acquire_sources.py": {0: "ok", 1: "proof"},         # 1: a source not held (ruling (a)); proof since attempt 8
    "factcheck_draft.py": {0: "ok", 1: "proof"},         # 1: --report wrote findings ("BLOCKED")
    "changecheck_coverage.py": {0: "ok", 1: "proof"},    # 1: changed sentences changecheck never read
    "ruling.py": {0: "ok", 4: "rerun"},                  # 4: some rulings failed, findings left open
}
DEFAULT_EXITS = {0: "ok"}

# Ownership is DERIVED (advisor's ruling after attempt 8): what each step's commands and code write, from
# orch/writes.py (traced in the paid attempts and the $0 replay, plus the code). Nothing is written by hand above.
from dataclasses import replace as _replace  # noqa: E402
from orch.writes import derive_owns  # noqa: E402
STEPS = tuple(_replace(s, owns=derive_owns(s)) for s in STEPS)

NAMES = tuple(s.name for s in STEPS)
BY_NAME = {s.name: s for s in STEPS}
MAX_REPEATS = 2                       # steps 12-18 re-run at most twice in all
# Human records no step owns: a write to any of them stops the chain (no person takes part).
NEVER_WRITTEN = ("human_reads.jsonl", "person_decisions.md", "protected_signoffs.json")


def owns_for(step: Step, slug: str) -> tuple:
    return tuple(p.replace("{slug}", slug) for p in step.owns)


def allow_for(step: Step) -> dict:
    return {"models": list(step.models), "roles": []}
