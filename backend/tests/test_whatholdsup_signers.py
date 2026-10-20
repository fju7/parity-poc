"""Who may be named in a signed field (process doc §8).

On 18-19 October 2026 an agent wrote "Fred Ugast" into 979 signed fields on 437
deskilling binding rows that Fred had not read. Nothing read the field, so
nothing stopped it. These tests hold the rule: an agent's name passes; a
person's name passes only with a signature citing a committed acceptance line
from a commit with no Claude trailer.

The acceptance cases run against a real git repository in tmp_path, because
the rule is about commits and a fake that returns whatever the test wants
cannot see a trailer.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("signers", WHU / "signers.py")
S = importlib.util.module_from_spec(spec)
spec.loader.exec_module(S)

ACCEPTANCE = "review/2026-10-20-acceptance.md"


def _doc(**verdict):
    return {"bindings": {"k1": {"sentence": "A sentence.", "verdicts": {
        "locatable": verdict or None, "faithful": None, "warranted": None}}}}


def _repo(tmp_path, trailer: bool) -> Path:
    def git(*a):
        subprocess.run(["git", "-C", str(tmp_path), *a], check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.name", "Fred Ugast")
    git("config", "user.email", "fred@example.invalid")
    git("config", "commit.gpgsign", "false")
    (tmp_path / "review").mkdir()
    (tmp_path / ACCEPTANCE).write_text(
        "# Acceptance\n\nThe rows of batch 1 were read against held text.\n\n"
        "Accepted by Fred Ugast, operator, 20 October 2026, stated in session.\n")
    git("add", ACCEPTANCE)
    msg = "acceptance of batch 1"
    if trailer:
        msg += "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
    git("commit", "-q", "-m", msg)
    return tmp_path


SIG = {"statement": "I read batch 1 against the held text.", "source": ACCEPTANCE + ":5"}


def test_an_agent_writing_a_persons_name_fails(tmp_path):
    bad = S.failures({}, _doc(by="Fred Ugast", on="2026-10-20"), tmp_path)
    assert len(bad) == 1 and "no signature object" in bad[0]


def test_an_agents_name_passes_with_or_without_a_session(tmp_path):
    for name in ("Claude Code", "Claude (advisor)",
                 "Claude Code (session 187dcad4-6322-4fa2-928f-614c638a40c4)"):
        assert S.failures({}, _doc(by=name, on="2026-10-20"), tmp_path) == [], name
    # An agent name followed by anything but a session is not an agent's name.
    assert S.failures({}, _doc(by="Claude Code and Fred Ugast"), tmp_path)


def test_a_person_citing_an_acceptance_from_a_trailer_free_commit_passes(tmp_path):
    root = _repo(tmp_path, trailer=False)
    assert S.failures({}, _doc(by="Fred Ugast", signature=SIG), root) == []


def test_the_same_acceptance_committed_with_the_claude_trailer_fails(tmp_path):
    root = _repo(tmp_path, trailer=True)
    bad = S.failures({}, _doc(by="Fred Ugast", signature=SIG), root)
    assert len(bad) == 1 and "Claude Co-Authored-By trailer" in bad[0]


def test_a_source_that_is_not_an_acceptance_line_fails(tmp_path):
    root = _repo(tmp_path, trailer=False)
    sig = dict(SIG, source=ACCEPTANCE + ":3")
    bad = S.failures({}, _doc(by="Fred Ugast", signature=sig), root)
    assert len(bad) == 1 and "not an acceptance line" in bad[0]


def test_an_acceptance_for_someone_else_fails(tmp_path):
    root = _repo(tmp_path, trailer=False)
    bad = S.failures({}, _doc(by="Someone Else", signature=SIG), root)
    assert len(bad) == 1 and "accepts for" in bad[0]


def test_a_blank_value_is_unchanged_behaviour(tmp_path):
    assert S.failures({}, _doc(by="", on="2026-10-20"), tmp_path) == []


def test_a_value_already_in_head_is_not_rejudged(tmp_path):
    old = _doc(by="Fred Ugast", on="2026-10-18")
    assert S.failures(old, old, tmp_path) == []


def test_every_signer_field_is_seen():
    row = {"verdicts": {"locatable": {"by": "a"}, "faithful": None},
           "scope_words": [{"word": "only", "by": "b"}],
           "hedge_dispositions": [{"word": "may", "by": "c"}],
           "framing": {"why": "w", "by": "d"},
           "attested_by": "e", "deferred_by": "f"}
    assert {k: v[0] for k, v in S.slots(row).items()} == {
        "verdicts.locatable": "a", "scope_words[only#0]": "b",
        "hedge_dispositions[may#0]": "c", "framing": "d",
        "attested_by": "e", "deferred_by": "f"}


def test_no_staged_bindings_change_names_a_person_without_an_acceptance():
    """The live check: every staged bindings.json against HEAD."""
    assert S.staged_failures() == []
