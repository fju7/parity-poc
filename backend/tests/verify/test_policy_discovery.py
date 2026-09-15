"""The discovering test: the AST-derived set of model surfaces must equal the
keys of verify.policy.POLICY, both ways, and `import anthropic` may appear
only in approved modules.

WHY THIS EXISTS
---------------
POLICY is a hand-maintained table -- the exact structure that let Provider's
APPEAL_SYSTEM_PROMPT diverge from Health's. A table nothing reconciles is a
gap rebuilt in Python. This test is the propagation mechanism: a new function
that reaches the model without a POLICY entry fails the build; a POLICY entry
whose function no longer reaches the model fails the build; a module that
imports anthropic outside the approved wrappers fails the build.

The walk resolves calls through each file's import table (a name-only match
put `claim_review.analyze_837` on the first inventory because it calls
utils.parse_837, not the router endpoint of the same name). `.messages.create`
receivers that are not the Anthropic SDK are listed in NOT_A_MODEL and the
named token must appear in that function's source, so the exclusion cannot
rot (routers.auth._send_sms_otp is Twilio).

It has been seen to fail: test_discovery_fails_on_an_ungated_surface adds a
surface in a scratch module and asserts the reconciliation reports it, then
tiers it and asserts the report is clean. A test that has never been seen to
fail is not a gate.
"""
from __future__ import annotations

import ast
import collections
import os
import sys
import textwrap

import pytest

BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, BACKEND)

from verify import policy  # noqa: E402

SKIP_DIRS = {"venv", "__pycache__", "tests", "test_data", "migrations", "data", "static"}
SDK_TAILS = ("messages.create", "messages.stream", "beta.messages.create")
# Files that cannot be parsed and therefore cannot run; each with the reason.
KNOWN_UNPARSEABLE = {
    "scripts.signal.resend_pipeline_emails": "one-off script truncated in 3cb74a3; SyntaxError, never runnable",
}


def _module_id(path: str, root: str) -> str:
    rel = os.path.relpath(path, root)[:-3]
    return rel.replace(os.sep, ".")


def _attr_chain(node) -> str:
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr); node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def discover(root: str = BACKEND, extra_files: list[str] | None = None) -> dict:
    """Walk root; return {"surfaces": {key: [(kind, line)]}, "sdk_direct": {...},
    "anthropic_importers": set, "unparseable": {module: err}}."""
    files = []
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if d not in SKIP_DIRS]
        files += [os.path.join(dp, f) for f in fns if f.endswith(".py")]
    files += list(extra_files or [])

    funcs = {}                                   # key -> {"sdk": [...], "calls": [(name, line)], "src": str}
    imports = collections.defaultdict(dict)      # module -> local name -> (from_module, name)
    importers = set()
    unparseable = {}
    sources = {}

    for fn in files:
        mod = _module_id(fn, root)
        src = open(fn, encoding="utf-8").read()
        sources[mod] = src
        try:
            tree = ast.parse(src, fn)
        except SyntaxError as e:
            unparseable[mod] = str(e); continue
        stack = []

        class V(ast.NodeVisitor):
            def visit_Import(self, n):
                if any(a.name == "anthropic" or a.name.startswith("anthropic.") for a in n.names):
                    importers.add(mod)
            def visit_ImportFrom(self, n):
                if (n.module or "").split(".")[0] == "anthropic":
                    importers.add(mod)
                for a in n.names:
                    imports[mod][a.asname or a.name] = (n.module or "", a.name)
            def visit_FunctionDef(self, n):
                key = f"{mod}::{'.'.join(stack + [n.name])}"
                funcs[key] = {"sdk": [], "calls": [], "lineno": n.lineno,
                              "src": ast.get_source_segment(src, n) or ""}
                stack.append(n.name); self.generic_visit(n); stack.pop()
            visit_AsyncFunctionDef = visit_FunctionDef
            def visit_ClassDef(self, n):
                stack.append(n.name); self.generic_visit(n); stack.pop()
            def visit_Call(self, n):
                chain = _attr_chain(n.func)
                key = f"{mod}::{'.'.join(stack)}" if stack else None
                if key in funcs:
                    if chain.endswith(SDK_TAILS):
                        funcs[key]["sdk"].append((n.lineno, chain))
                    funcs[key]["calls"].append((chain.split(".")[-1] if chain else "", n.lineno))
                self.generic_visit(n)
        V().visit(tree)

    def resolve(mod: str, name: str) -> str | None:
        """Where does `name`, called inside `mod`, resolve? Same-module def first,
        then the import table. None when neither."""
        if f"{mod}::{name}" in funcs:
            return f"{mod}::{name}"
        if name in imports[mod]:
            from_mod, orig = imports[mod][name]
            cand = f"{from_mod}::{orig}"
            if cand in funcs:
                return cand
        return None

    wrappers = policy.WRAPPERS
    not_model = policy.NOT_A_MODEL
    surfaces = collections.defaultdict(list)
    for key, d in funcs.items():
        mod = key.split("::")[0]
        if d["sdk"] and key not in wrappers and key not in not_model:
            surfaces[key].append(("sdk", d["sdk"][0][0]))
        for name, line in d["calls"]:
            tgt = resolve(mod, name)
            if tgt in wrappers and key not in wrappers:
                surfaces[key].append((f"wrapper:{tgt}", line))
    return {"surfaces": dict(surfaces), "funcs": funcs, "anthropic_importers": importers,
            "unparseable": unparseable, "sources": sources}


def reconcile(found: dict, table: dict) -> dict:
    disc = set(found["surfaces"])
    keys = set(table)
    return {"missing_policy": sorted(disc - keys), "stale_policy": sorted(keys - disc)}


# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def found():
    return discover()


def test_every_discovered_surface_has_a_policy_entry(found):
    r = reconcile(found, policy.POLICY)
    assert not r["missing_policy"], (
        "model surfaces with no POLICY entry (add a SurfacePolicy in verify/policy.py):\n  "
        + "\n  ".join(f"{k}  <- {found['surfaces'][k]}" for k in r["missing_policy"]))


def test_no_policy_entry_is_stale(found):
    r = reconcile(found, policy.POLICY)
    assert not r["stale_policy"], "POLICY entries whose function no longer reaches a model:\n  " + "\n  ".join(r["stale_policy"])


def test_anthropic_is_imported_only_where_approved(found):
    rogue = sorted(found["anthropic_importers"] - policy.APPROVED_ANTHROPIC_IMPORTERS)
    assert not rogue, "modules importing anthropic outside APPROVED_ANTHROPIC_IMPORTERS:\n  " + "\n  ".join(rogue)
    # and the approved list carries no dead weight
    dead = sorted(policy.APPROVED_ANTHROPIC_IMPORTERS - found["anthropic_importers"])
    assert not dead, "APPROVED_ANTHROPIC_IMPORTERS lists modules that no longer import anthropic:\n  " + "\n  ".join(dead)


def test_every_wrapper_exists_and_contains_the_sdk_call(found):
    for w in policy.WRAPPERS:
        assert w in found["funcs"], f"WRAPPERS names {w}, which does not exist"
        assert found["funcs"][w]["sdk"], f"{w} is listed as a wrapper but contains no SDK call"


def test_not_a_model_exclusions_are_still_true(found):
    for key, token in policy.NOT_A_MODEL.items():
        assert key in found["funcs"], f"NOT_A_MODEL names {key}, which does not exist"
        assert token in found["funcs"][key]["src"], f"{key}: {token!r} no longer appears in the function; re-examine"


def test_a_file_that_cannot_be_parsed_is_accounted_for(found):
    unknown = {m: e for m, e in found["unparseable"].items() if m not in KNOWN_UNPARSEABLE}
    assert not unknown, "unparseable modules could hide a surface: " + repr(unknown)
    gone = set(KNOWN_UNPARSEABLE) - set(found["unparseable"])
    assert not gone, f"KNOWN_UNPARSEABLE lists modules that now parse (remove them): {gone}"


def test_unwired_gates_are_declared_and_only_shrink():
    """A GATE with wired=False is a declared, unenforced tier. The set is
    pinned here so it can only shrink deliberately.

    Drain plan (docs/shared-assertion-policy-phase-a-inventory.md, 2026-09-15):
      batch 1 by 2026-09-17: generate_plain_summary, analyze_denial,
                             broker_claims_upload, broker_scorecard_upload,
                             generate_notification_text            (-> 26 left)
      batch 2 by 2026-09-22: H1 x5, E3-E8                          (-> 14 left)
      batch 3 by 2026-09-29: P3, P4 x2, P5, P6 x2, P7, P8           (-> 6 left)
      batch 4 by 2026-10-06: the Signal pipeline writers            (-> 0 left)
      2026-09-15: the four prose surfaces wired ahead of schedule (pre-flip)
    Remove entries from `expected` as they are wired; never add."""
    expected = {
        "routers.broker::broker_claims_upload", "routers.broker::broker_scorecard_upload",
        "routers.employer_claims::employer_claims_check", "routers.employer_claims::employer_contract_parse",
        "routers.employer_claims::employer_rbp_calculate", "routers.employer_pharmacy::employer_pharmacy_analyze",
        "routers.employer_scorecard::employer_scorecard", "routers.employer_trends::_generate_trend_narrative",
        "routers.health_analyze::analyze_text", "routers.health_analyze::analyze_image",
        "routers.ai_parse::parse_with_ai", "routers.eob_parse::parse_eob", "routers.eob_parse::parse_eob_text",
        "routers.health_analyze::analyze_sbc", "routers.health_analyze::analyze_denial",
        "routers.provider_audit::analyze_contract", "routers.provider_audit::_run_coding_analysis_from_835",
        "routers.provider_audit::analyze_coding", "routers.provider_audit::parse_837",
        "routers.provider_audit::analyze_denials", "routers.provider_shared::_run_analysis_for_payer",
        "routers.provider_audit::generate_audit_report", "routers.provider_trends::_generate_trend_narrative",
        "routers.signal_metrics::generate_plain_summary",
        "scripts.signal.extract_claims::extract_from_source",
        "scripts.signal.generate_notifications::generate_notification_text",
    }
    actual = set(policy.unwired_gates())
    assert actual <= expected, "a GATE surface lost its wiring or a new unwired GATE was added: " + repr(sorted(actual - expected))
    # (shrinking is progress; update `expected` when a surface is wired)


# ---------------------------------------------------------------------------
# The gate seen failing, then passing.
# ---------------------------------------------------------------------------

def test_discovery_fails_on_an_ungated_surface(tmp_path):
    scratch = tmp_path / "routers"
    scratch.mkdir()
    (scratch / "__init__.py").write_text("")
    f = scratch / "scratch_surface.py"
    f.write_text(textwrap.dedent('''
        from routers.provider_shared import _call_claude

        def brand_new_narrative(x):
            return _call_claude(system_prompt="s", user_content=x, max_tokens=10)
    '''))
    # Discover the real tree plus the scratch file, reported under its own module id.
    found = discover(extra_files=[str(f)])
    # module id of the scratch file is derived from its path relative to BACKEND,
    # so normalise: find the key by function name
    keys = [k for k in found["surfaces"] if k.endswith("::brand_new_narrative")]
    assert keys, "the walk did not see the scratch surface at all -- the discovery is blind"
    key = keys[0]
    r = reconcile(found, policy.POLICY)
    assert key in r["missing_policy"], "an ungated surface was not reported; the reconciliation is not a gate"

    # Now tier it, and the report is clean for that surface.
    table = dict(policy.POLICY)
    table[key] = policy.SurfacePolicy(policy._NARRATIVE, "scratch", note="test")
    r2 = reconcile(found, table)
    assert key not in r2["missing_policy"]
