#!/usr/bin/env python3
"""Lean WHU: one switch, default off.

Plan doc "WHU next phase: validity checks and a leaner WHU", Part B (claude.ai
artifact VQUwahJeiW3Dh5NpPXdZ2x). Every lean change is behind `enabled()`:
the environment variable WHU_LEAN=1, or `--lean` on a command that takes it
(which calls `enable()`). With neither, every WHU stage runs exactly as it did
before lean WHU existed, so the current WHU stays runnable for comparison.

WHAT THE SWITCH TURNS ON
  1. passage retrieval (passage_index.py): the audit is sent the bound passages
     plus the top-k retrieved passages, never a whole source;
  2. incremental re-audit (reaudit.py);
  3. generated protected sentences (lean_sentences.py);
  4. the lean coverage rules (lean_coverage.py);
  5. model tiering (this file: STAGE_MODELS, model_for, escalation rules in
     audit_stage / ruling);
  6. prompt caching of source text within a run (cache_blocks).

MODEL TIERING. A model per stage, overridable with WHU_LEAN_MODELS (a JSON
object {stage: model}). Every model named must be in spend_ledger.PRICES:
prices are read from the ledger's own table, never guessed, and a model the
table does not price is refused before any call (check_models). On
2026-10-30 the table prices claude-opus-5-5 (the current WHU model),
claude-opus-4-6, claude-fable-5-1 and claude-sonnet-4-6; the only one cheaper
than the current model is claude-sonnet-4-6, so it is the lean default for the
smaller tier. A cheaper model becomes usable here only when someone adds its
checked price to spend_ledger.PRICES.
"""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ENV = "WHU_LEAN"
ENV_MODELS = "WHU_LEAN_MODELS"

CURRENT = "claude-opus-5-5"          # audit_stage.MODEL and ruling.MODEL today
SMALL = "claude-sonnet-4-6"          # the cheapest model spend_ledger.PRICES prices
# The model each stage runs on under lean WHU. "audit_first" is the audit's
# first read; a sentence it flags or is unsure about is read again on
# "audit_escalate", whose verdict decides. Rulings of findings, the second
# reader and every ruling.py mode not named here stay on the current model.
STAGE_MODELS = {
    "audit_first": SMALL,
    "audit_escalate": CURRENT,
    "audit_rule": CURRENT,
    "audit_second": CURRENT,
    "advocate": SMALL,               # the gate (factcheck_draft) already runs on this model
    "judgements": SMALL,
    "judgements_escalate": CURRENT,
    "rulings": CURRENT,
}

_forced: bool | None = None


def enable(on: bool = True) -> None:
    """What `--lean` calls. Also sets WHU_LEAN so a child process sees it."""
    global _forced
    _forced = on
    if on:
        os.environ[ENV] = "1"
    else:
        os.environ.pop(ENV, None)


def enabled() -> bool:
    if _forced is not None:
        return _forced
    return os.environ.get(ENV, "").strip() in ("1", "true", "yes", "on")


def strip_flag(argv: list[str] | None) -> list[str] | None:
    """Remove `--lean` from ARGV, turning the switch on if it was there."""
    if argv is None:
        import sys
        argv = sys.argv[1:]
    if "--lean" in argv:
        enable(True)
        return [a for a in argv if a != "--lean"]
    return argv


def _ledger():
    sp = importlib.util.spec_from_file_location("spend_ledger", ROOT / "backend" / "scripts" / "spend_ledger.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def prices() -> dict:
    """spend_ledger.PRICES, the ledger's own table (US dollars per million tokens)."""
    return _ledger().PRICES


def stage_models() -> dict:
    out = dict(STAGE_MODELS)
    raw = os.environ.get(ENV_MODELS, "").strip()
    if raw:
        got = json.loads(raw)
        if not isinstance(got, dict):
            raise ValueError("%s must be a JSON object {stage: model}" % ENV_MODELS)
        unknown = [k for k in got if k not in STAGE_MODELS]
        if unknown:
            raise ValueError("%s names unknown stage(s): %s" % (ENV_MODELS, ", ".join(unknown)))
        out.update(got)
    return out


class UnpricedModel(RuntimeError):
    pass


def check_models(models: dict | None = None, table: dict | None = None) -> None:
    """Refuse any configured model that spend_ledger.PRICES does not price."""
    table = table if table is not None else prices()
    bad = sorted({m for m in (models or stage_models()).values() if m not in table})
    if bad:
        raise UnpricedModel("model(s) %s are not in spend_ledger.PRICES; their cost cannot be "
                            "established, so lean WHU will not use them" % ", ".join(bad))


def model_for(stage: str, default: str = CURRENT) -> str:
    """The model STAGE runs on: the lean table's when the switch is on, else DEFAULT."""
    if not enabled():
        return default
    m = stage_models().get(stage, default)
    check_models({stage: m})
    return m


def usd(model: str, input_tokens: int = 0, output_tokens: int = 0, cache_write: int = 0,
        cache_read: int = 0, table: dict | None = None) -> float:
    """Price token counts from the ledger's table (as spend_ledger.price does)."""
    p = (table if table is not None else prices())[model]
    return (input_tokens * p["input"] + output_tokens * p["output"]
            + cache_write * p["cache_write"] + cache_read * p["cache_read"]) / 1e6


# --------------------------------------------------------------------------
# Prompt caching (item 6)
# --------------------------------------------------------------------------
#
# The API caches a prompt PREFIX (prompt-caching docs: any byte change in the
# prefix invalidates what follows; at most 4 breakpoints; a prefix shorter
# than the model's minimum silently does not cache). The audit's reading
# prompt puts its documents first, so the prefix up to the end of a batch's
# stable document block is what repeats within a run: the next batch of the
# same source group, the re-quote of a batch, the escalation re-read. Only the
# split into content blocks changes; the prompt text is byte for byte the one
# a caller built.
CACHE_MIN_TOKENS = {CURRENT: 512, SMALL: 1024}   # documented minimums; others: assume the largest
CACHE_MIN_DEFAULT = 4096


def cache_blocks(prompt: str, prefix: str | None) -> list[dict] | str:
    """PROMPT as user content: two text blocks with a cache breakpoint after
    PREFIX when PROMPT starts with it, else PROMPT unchanged (a plain string)."""
    if not prefix or not prompt.startswith(prefix) or len(prefix) == len(prompt):
        return prompt
    return [{"type": "text", "text": prefix, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": prompt[len(prefix):]}]


def worth_caching(prefix_tokens: int, model: str, expected_reuses: int) -> bool:
    """A cache write costs more than plain input (spend_ledger.PRICES:
    cache_write > input), so a prefix is cached only when it is long enough to
    cache at all and at least one reuse within the run is expected."""
    return expected_reuses >= 1 and prefix_tokens >= CACHE_MIN_TOKENS.get(model, CACHE_MIN_DEFAULT)
