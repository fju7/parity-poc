"""Every model each orchestrator step may call, and where it comes from, read from the code it runs (advisor's
follow-up after attempt 8). The run manifest records it (orch/manifest.py "model_sources"); a test fails if a step
does not declare a model its commands can call (orch/steps.py `models`, enforced at every paid call by orch_guard).

claude-sonnet-4-6 appears through the gate helper, factcheck_draft.call, whose model is signal_model.DEFAULT_MODEL.
Lean WHU (lean.STAGE_MODELS) moved the rulings, the audit, the advocate's reading and the judgements to the 5.5 models;
it did not change the gate helper's default, and no ruling chose 4-6 for the lean test or this build: the gate, the
discover search, changecheck's review and the omission re-asks run on it by inheritance. The conclusion judge is the
exception: conclusion_judge.JUDGE_MODEL pins 4-6 in its own code and refuses any other model.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[0] / "signal"))


def command_models() -> dict:
    """{command key: {model: where it comes from}}; a ruling.py command is keyed "ruling.py <mode>"."""
    import lean
    import conclusion_judge as CJ
    import signal_model as SM
    gate = SM.DEFAULT_MODEL
    G = "the gate helper (factcheck_draft.call), signal_model.DEFAULT_MODEL; inherited, not changed by lean WHU"
    R = "ruling.py under lean WHU, lean.STAGE_MODELS['rulings']"
    return {
        "factcheck_draft.py": {gate: G},
        "source_advocate.py": {lean.STAGE_MODELS["advocate"]: "the advocate's reading, lean.STAGE_MODELS['advocate']",
                               gate: G + " (the advocate's re-quote and question calls)"},
        "ruling.py advocate": {lean.STAGE_MODELS["rulings"]: R},
        "ruling.py gate": {lean.STAGE_MODELS["rulings"]: R},
        "ruling.py conclusions": {lean.STAGE_MODELS["rulings"]: R},
        "ruling.py changecheck": {lean.STAGE_MODELS["rulings"]: R},
        "ruling.py dangling": {lean.STAGE_MODELS["rulings"]: R},
        "ruling.py omissions": {lean.STAGE_MODELS["rulings"]: R,
                                gate: G + " (source_advocate.reask_omission's re-asks)"},
        "ruling.py judgements": {lean.STAGE_MODELS["judgements"]: "lean.STAGE_MODELS['judgements']",
                                 lean.STAGE_MODELS["judgements_escalate"]: "lean.STAGE_MODELS['judgements_escalate']"},
        "conclusion_judge.py": {CJ.JUDGE_MODEL: "conclusion_judge.JUDGE_MODEL, pinned in its own code (deliberate)"},
        "changecheck.py": {gate: G + " (changecheck's review)"},
        "audit_stage.py": {lean.STAGE_MODELS["audit_first"]: "lean.STAGE_MODELS['audit_first']",
                           lean.STAGE_MODELS["audit_escalate"]: "lean.STAGE_MODELS['audit_escalate']"},
        "consistency.py": {lean.CURRENT: "consistency.py audit, audit_stage.Caller's default model"},
        "findings.py": {}, "changecheck_coverage.py": {}, "bindings.py": {}, "premise.py": {},
        "acquire_sources.py": {}, "source_store.py": {}, "errata.py": {}, "sweep_sources.py": {}, "canary.py": {},
        "publish.py": {},
    }


def in_process_models() -> dict:
    """{step: {model: where}} for the calls the orchestrator itself makes inside a step."""
    from orch import steps as ST
    import signal_model as SM
    return {
        "premise": {ST.DRAFT_MODEL: "orch/model_steps.premise, steps.DRAFT_MODEL"},
        "discover": {SM.DEFAULT_MODEL: "the gate helper's web search (factcheck_draft.call, search on), "
                                       "signal_model.DEFAULT_MODEL; inherited"},
        "draft": {ST.DRAFT_MODEL: "orch/model_steps draft, steps.DRAFT_MODEL"},
        "coverage": {ST.STEP_MODEL: "orch/model_steps.coverage_decision, steps.STEP_MODEL"},
        "judgements": {ST.STEP_MODEL: "orch/model_steps.judgement_sentence, steps.STEP_MODEL"},
        "audit": {},
        "overstatement": {ST.GOOGLE: "orch/overstatement via orch/google.Gateway"},
    }


def _key(argv) -> str:
    script = Path(argv[1]).name
    return "%s %s" % (script, argv[2]) if script == "ruling.py" else script


def step_models(steps) -> dict:
    """{step: {model: [where it comes from, ...]}} for every step; raises KeyError on a command it does not know."""
    cm, ip = command_models(), in_process_models()
    out = {}
    for s in steps:
        got: dict = {}
        for m, why in (ip.get(s.name) or {}).items():
            got.setdefault(m, []).append(why)
        for argv in s.cmds:
            for m, why in cm[_key(argv)].items():
                got.setdefault(m, []).append("%s: %s" % (_key(argv), why))
        if s.code == "audit":       # code_audit runs consistency.py audit itself
            for m, why in cm["consistency.py"].items():
                got.setdefault(m, []).append("consistency.py: %s" % why)
        if s.code in ("apply", "audit", "overstatement", "corrections"):
            # these steps' code runs code_apply, which may run `ruling.py dangling` once (GAP-016)
            for m, why in cm["ruling.py dangling"].items():
                got.setdefault(m, []).append("ruling.py dangling (code_apply, GAP-016): %s" % why)
        out[s.name] = got
    return out
