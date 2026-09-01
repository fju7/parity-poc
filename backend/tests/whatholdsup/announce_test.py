"""The announce path must never record a send that did not happen.

Run:  python3 backend/tests/whatholdsup/announce_test.py

WHY THIS EXISTS
On 2026-08-28 cmd_announce appended an "announce" row to published.json and
then printed "Now run send_broadcast.py to perform the send." From a terminal
that is an instruction. From the board's button it is invisible, and the
publication record — the file that answers "what have we sent" — carried a
broadcast that was never transmitted. The operator found out because no email
arrived.

Every case below drives the real function with the real record file redirected
to a temporary path, and a stubbed sender. Nothing is mailed.
"""
import importlib.util, json, pathlib, sys, tempfile, types
from argparse import Namespace

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[3]
spec = importlib.util.spec_from_file_location(
    "pub", ROOT / "backend" / "scripts" / "whatholdsup" / "publish.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

pas = fail = 0
def t(name, ok):
    global pas, fail
    print(("  ok   " if ok else "  FAIL ") + name)
    if ok: pas += 1
    else: fail += 1

def run_with(stdout, code):
    """Run cmd_announce against a stubbed sender and a throwaway record."""
    tmp = pathlib.Path(tempfile.mkdtemp()) / "published.json"
    tmp.write_text(json.dumps({"what_this_is": "test", "published": []}))
    real_record, real_run, real_preflight, real_show = (
        m.RECORD, m.subprocess.run, m.preflight, m.show)
    m.RECORD = tmp
    m.subprocess.run = lambda *a, **k: types.SimpleNamespace(
        returncode=code, stdout=stdout, stderr="")
    m.preflight = lambda slug, *, for_email: [("stub", m.OK, "ok")]
    m.show = lambda rows, waive=None, unwaivable=(): True
    try:
        rc = m.cmd_announce(Namespace(slug="melanoma", yes=True, waive=None,
                                      subject="Test subject", dry_run=False))
    finally:
        m.RECORD, m.subprocess.run, m.preflight, m.show = (
            real_record, real_run, real_preflight, real_show)
    return rc, json.loads(tmp.read_text())["published"]

print()
rc, rows = run_with("SENT     : to segment abc  (broadcast bc_123)", 0)
t("a real send records exactly one row", rc == 0 and len(rows) == 1)
t("and the row is an announce", bool(rows) and rows[0]["action"] == "announce")
t("and it captures the broadcast id", bool(rows) and "bc_123" in rows[0].get("note", ""))
t("and it states the basis it was sent on", bool(rows) and rows[0].get("gate_basis"))

rc, rows = run_with("[BLOCKED] The gate report records a FAILED run.", 1)
t("a sender that exits non-zero records NOTHING", rc == 1 and rows == [])

rc, rows = run_with("segment : abc\nsubject : x\n(no send line)", 0)
t("a sender that exits 0 without saying SENT records NOTHING", rc == 1 and rows == [])

rc, rows = run_with("SENT : to segment abc", 0)
t("a send with no broadcast id still records", rc == 0 and len(rows) == 1)

# --- the credential the sender needs, and only that one --------------------
import os
before = set(os.environ)
env = m.sender_env()
added = set(env) - before
t("the sender's key is resolved for it", bool(env.get(m.SENDER_KEY)))
t("and nothing else from the .env comes with it", added <= {m.SENDER_KEY})
os.environ[m.SENDER_KEY] = "exported-value-wins"
t("an exported value takes precedence over the file",
  m.sender_env()[m.SENDER_KEY] == "exported-value-wins")
del os.environ[m.SENDER_KEY]
t("the key value is never in the record we write",
  all(m.SENDER_KEY not in json.dumps(r) for r in
      json.loads(pathlib.Path(ROOT / "backend/data/whatholdsup/published.json")
                 .read_text())["published"]))

print("\n  %d passed, %d failed\n" % (pas, fail))
sys.exit(1 if fail else 0)
