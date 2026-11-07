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
REPLY_LIMITS = {
    "premise": 4000,             # basis 1,012 (Q1-01c premise.json's fixed rows in the reply schema); ruled ~4,000
    "discover": 4000,            # basis 1,792 (Q1-02b's 3 sources = 672, scaled to the prompt's maximum of 8)
    "draft": 30000,              # basis 14,824 (Q1-03b: 143 prose sentences, two passage ids each)
    "coverage": 600,             # basis 281 (Q1-04c: longest recorded reason plus the longest page sentence)
    "judgement_sentence": 500,   # basis 165 (Q1-04c: the longest prose sentence)
    "overstatement": 2800,       # basis 1,375 (largest gemini-4-argon judging output in the ledger, 1,286 thinking)
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
    Step("provenance", "code", owns=("orchestrator/manifest.json",), code="provenance"),
    Step("premise", "model", owns=("premise.json",), models=(DRAFT_MODEL,), max_calls=2, cap_usd=0.20,
         cmds=((PY, W + "premise.py", "init", "{slug}"),), code="premise"),
    Step("discover", "model", owns=("sources.json",), models=(GATE_MODEL,), max_calls=3, cap_usd=1.50,
         code="discover"),
    Step("acquire", "code", owns=("sources.json", "errata.json", "sweeps.json", "canary.json", "library:*",
                                  "corrections/*"),
         cmds=((PY, W + "acquire_sources.py", "{slug}", "--out", "{case}/orchestrator/acquire.json"), (PY, W + "source_store.py", "{slug}", "status"),
               (PY, W + "errata.py", "{slug}"), (PY, W + "sweep_sources.py", "resolve", "{slug}", "--write"),
               (PY, W + "canary.py", "{slug}")), code="acquire"),
    Step("draft", "model", owns=PAGE, models=(DRAFT_MODEL,), max_calls=2, cap_usd=2.50, code="draft"),
    Step("bind", "code", owns=PAGE + ("bindings.json", "quotations.json", "attributions.json"),
         cmds=((PY, W + "bindings.py", "{slug}", "scan"),), code="bind"),
    Step("coverage", "model", owns=PAGE + ("coverage.json", "bindings.json", "rulings/coverage_in_scope.jsonl"),
         models=(STEP_MODEL,), max_calls=120, cap_usd=1.20, code="coverage"),   # 60 units, each re-asked at most once
    Step("judgements", "mixed", owns=PAGE + ("judgements.json", "bindings.json", "coverage.json") + RULINGS,
         models=(SMALL, CURRENT, STEP_MODEL), max_calls=400, cap_usd=3.00,
         cmds=((PY, W + "ruling.py", "judgements", "{slug}", "--cap", "{cap}"),), code="judgements"),
    Step("corrections_3b", "code", owns=PAGE + ("bindings.json", "rulings/corrections.jsonl",
                                                 "rulings/lean_removed.jsonl") + RULINGS,
         models=(CURRENT,), max_calls=20, cap_usd=0.50, code="corrections"),   # CURRENT: ruling.py dangling
    Step("commit_3b", "code", code="commit"),
    Step("gate", "stage", owns=("draft/{slug}.html.gate.json*", "gate-findings.json"), models=(GATE_MODEL,),
         max_calls=40, cap_usd=3.00,
         cmds=((PY, "backend/scripts/signal/factcheck_draft.py", "{page}", "--dry-run"),
               (PY, "backend/scripts/signal/factcheck_draft.py", "{page}", "--report", "{gate}"))),
    Step("advocate", "stage", owns=PAGE + ("advocate/*", "bindings.json", "attributions.json") + RULINGS,
         models=(SMALL, GATE_MODEL, CURRENT), max_calls=120, cap_usd=2.50,
         cmds=((PY, W + "source_advocate.py", "run", "{slug}", "--page", "{page}"),
               (PY, W + "ruling.py", "advocate", "{slug}")), code="apply"),
    Step("omissions", "stage", owns=PAGE + ("omissions.json", "bindings.json", "coverage.json") + RULINGS,
         models=(CURRENT, GATE_MODEL), max_calls=120, cap_usd=2.50,  # GATE_MODEL: source_advocate.reask_omission's re-asks (fc.call)
         cmds=((PY, W + "ruling.py", "omissions", "{slug}"),), code="apply"),
    Step("findings", "stage", owns=PAGE + ("gate-findings.json", "bindings.json") + RULINGS, models=(CURRENT,),
         max_calls=200, cap_usd=2.50, repeat_group=True,
         cmds=((PY, W + "findings.py", "{slug}", "--report", "{gate}", "--scan"),
               (PY, W + "ruling.py", "gate", "{slug}")), code="apply"),
    Step("conclusions", "stage", owns=PAGE + ("conclusion-review.json", "bindings.json") + RULINGS,
         models=(GATE_MODEL, CURRENT), max_calls=60, cap_usd=1.00, repeat_group=True,  # GATE_MODEL: conclusion_judge.JUDGE_MODEL (fc.call)
         cmds=((PY, W + "conclusion_judge.py", "{slug}"), (PY, W + "ruling.py", "conclusions", "{slug}")),
         code="apply"),
    Step("audit", "stage", owns=PAGE + ("audit/*", "bindings.json") + RULINGS, models=(SMALL, CURRENT),
         max_calls=600, cap_usd=4.00, repeat_group=True,
         cmds=((PY, W + "audit_stage.py", "run", "{slug}", "--cap", "{cap}"),), code="audit"),
    Step("overstatement", "model", owns=PAGE + ("rulings/overstatement.jsonl", "rulings/lean_removed.jsonl"),
         models=(GOOGLE, CURRENT), max_calls=420, cap_usd=2.50, repeat_group=True,
         code="overstatement"),                                     # CURRENT: ruling.py dangling (20 calls, $0.50)
    Step("corrections", "code", owns=PAGE + ("bindings.json", "rulings/corrections.jsonl",
                                              "rulings/lean_removed.jsonl") + RULINGS,
         models=(CURRENT,), max_calls=20, cap_usd=0.50, repeat_group=True,
         code="corrections"),                                                       # CURRENT: ruling.py dangling
    Step("final_gate", "stage", owns=PAGE + ("draft/{slug}.html.gate.json*", "gate-findings.json",
                                             "bindings.json") + RULINGS,
         models=(GATE_MODEL, CURRENT), max_calls=200, cap_usd=2.00, repeat_group=True,
         cmds=((PY, "backend/scripts/signal/factcheck_draft.py", "{page}", "--changed-since", "{gate}",
                "--dry-run"),
               (PY, "backend/scripts/signal/factcheck_draft.py", "{page}", "--changed-since", "{gate}",
                "--report", "{gate}"),
               (PY, W + "findings.py", "{slug}", "--report", "{gate}", "--scan"),
               (PY, W + "ruling.py", "gate", "{slug}")), code="apply"),
    Step("commit_8", "code", repeat_group=True, code="commit"),
    Step("changecheck", "stage", owns=PAGE + ("change-reviews.json", "bindings.json") + RULINGS,
         models=(GATE_MODEL, CURRENT), max_calls=60, cap_usd=1.00, repeat_group=True,  # GATE_MODEL: changecheck.py's review (fc.call)
         cmds=((PY, W + "changecheck.py", "{slug}", "--page", "{page}", "--before", "{first}"),
               (PY, W + "ruling.py", "changecheck", "{slug}"),
               (PY, W + "changecheck_coverage.py", "{slug}", "--first", "{first}", "--out",
                "{case}/orchestrator/changecheck_coverage.json")), code="apply"),
    Step("preflight", "code", cmds=((PY, W + "publish.py", "check", "{slug}"),), code="preflight"),
    Step("archive", "code", owns=("private_manifest.txt",), code="archive"),
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

NAMES = tuple(s.name for s in STEPS)
BY_NAME = {s.name: s for s in STEPS}
MAX_REPEATS = 2                       # steps 12-18 re-run at most twice in all
# Human records no step owns: a write to any of them stops the chain (no person takes part).
NEVER_WRITTEN = ("human_reads.jsonl", "person_decisions.md", "protected_signoffs.json")


def owns_for(step: Step, slug: str) -> tuple:
    return tuple(p.replace("{slug}", slug) for p in step.owns)


def allow_for(step: Step) -> dict:
    return {"models": list(step.models), "roles": []}
