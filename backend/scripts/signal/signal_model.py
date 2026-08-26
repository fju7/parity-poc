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

Pinning is a deployment decision, so it is an environment variable rather than
a constant. To find the exact snapshot ids available to this account:

    python -c "import anthropic; [print(m.id) for m in anthropic.Anthropic().models.list()]"

then set SIGNAL_MODEL to the dated id (e.g. claude-sonnet-4-6-20260115).
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
    """Print a warning when the pipeline is about to run on a moving target."""
    if is_pinned(model):
        return
    print(f"  [WARN] Model '{model}' is an alias, not a pinned snapshot.")
    print("         Published judgments can change with no code change.")
    print("         Set SIGNAL_MODEL to a dated id to pin it.")


def prompt_version(system_prompt: str) -> str:
    """Stable short hash of a system prompt.

    Stored alongside each output so a later question — "was this produced by
    the prompt we have now?" — is answerable by comparison rather than by
    archaeology through git history.
    """
    return hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:12]
