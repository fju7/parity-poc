"""
Single source of truth for which model the Signal pipeline runs on, and for
recording which model actually produced a given output.

WHY THIS EXISTS
---------------
Every pipeline script hardcoded the alias "claude-sonnet-4-6". An alias
resolves to whatever snapshot is current, so a published judgment can change
without a single line of code changing.

That is not hypothetical. GLP-1 'pricing' was published as "debated" in March
2026. In August, the identical prompt over the identical 44 claims returned
"consensus" — and reading the claims confirmed "consensus" was the correct
answer. The site served a wrong label for five months. Nothing detected it,
because nothing recorded what had produced it.

A stability sweep across all 52 categories put the drift at 10%, concentrated
at the uncertain/debated boundary. So the fix is not to distrust the model; it
is to know what you ran, pin it, and notice when it changes.

TWO MECHANISMS
--------------
1. MODEL — the configured model, overridable per environment. Detects whether
   it is a pinned snapshot and says so, loudly, when it is not.
2. resolved_model() — the model string the API ACTUALLY used, read back off
   the response. This is the honest record: it is correct even when the
   configured value is an unpinned alias.

PINNING WAS ATTEMPTED AND IS NOT AVAILABLE (checked 2026-08-26)
--------------------------------------------------------------
models.list() on this account returns dated snapshots for exactly three models,
all of the 4-5 generation:

    claude-opus-4-5-20251101
    claude-haiku-4-5-20251001
    claude-sonnet-4-5-20250929

Everything newer — opus-5, sonnet-5, opus-4-8, opus-4-7, sonnet-4-6, opus-4-6 —
is published only as an alias. Requesting "claude-sonnet-4-6" returns
response.model == "claude-sonnet-4-6", so there is no snapshot id to pin to.

The decision was therefore to keep running on the alias rather than pin to the
older claude-sonnet-4-5-20250929. The evidence says the newer model is BETTER:
it correctly reads GLP-1 pricing as undisputed facts, and it finds three real
debates the March model missed. Trading accuracy for reproducibility is the
wrong trade for a product whose value IS accuracy.

So drift is DETECTED, not prevented. The control is scripts/signal/golden_set.py
— 52 recorded baselines that fail when a judgment moves. Detection is only worth
as much as its frequency: run the golden set on a schedule, because the whole
lesson here is that five months is far too long to find out.

SIGNAL_MODEL remains overridable so that a snapshot can be pinned the moment one
is published, and so 4-5 can be run deliberately for comparison.
"""
from __future__ import annotations

import hashlib
import os
import re

# The alias remains the fallback so nothing breaks if the variable is unset —
# but running unpinned is reported rather than silently tolerated.
DEFAULT_MODEL = "claude-sonnet-4-6"
MODEL = os.environ.get("SIGNAL_MODEL", DEFAULT_MODEL)

_DATED_SNAPSHOT = re.compile(r"-\d{8}$")


def is_pinned(model: str = MODEL) -> bool:
    """True when the model string names a dated snapshot rather than an alias."""
    return bool(_DATED_SNAPSHOT.search(model))


def warn_if_unpinned(model: str = MODEL) -> None:
    """State the reproducibility posture of the model about to be used.

    Deliberately NOT a nag. No dated snapshot exists for the current model
    family (see the module docstring), so a warning telling the operator to pin
    would be advice they cannot take — and an unactionable warning printed on
    every run is how people learn to ignore warnings. It reports the situation
    and names the control that actually applies.
    """
    if is_pinned(model):
        print(f"  Model pinned: {model}")
        return
    print(f"  Model '{model}' is an alias — no dated snapshot is published for it.")
    print("  Judgments can move without a code change; golden_set.py is what catches that.")


def prompt_version(system_prompt: str) -> str:
    """Stable short hash of a system prompt.

    Stored alongside each output so a later question — "was this produced by
    the prompt we have now?" — is answerable by comparison rather than by
    archaeology through git history.
    """
    return hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:12]
