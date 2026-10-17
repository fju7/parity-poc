"""The conclusion-judge stage, without a single paid call.

A model reads each conclusion against its recorded passages; a person decides
every one it flags; publish preflight blocks until they have. These tests pin
what the judge may see (never the writer's step or anything the pipeline already
concluded), which sentences it judges (judgements, never holdings sentences --
the store settles those), the flag rule, how decisions survive a re-run, and
every state of the preflight row, including the exemption for issues that were
already published before the stage existed.
"""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, WHU / ("%s.py" % name))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(WHU))
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.path.pop(0)
    return mod


CJ = _load("conclusion_judge")
SLUG = "fixture-issue"

S85 = ("The evidence does not support choosing between those three on the basis "
       "of age or sex.")
S56 = ("So a reader choosing between the two should pick the pattern they can "
       "sustain, because the evidence says the calorie deficit, not the clock, does "
       "most of the work.")
HOLD = "We hold the abstract of this review, not the full text."


def row(sentence, **kw):
    r = {"sentence": sentence, "bucket": "judgement", "on_page": True,
         "premises": [{"source_id": "S001", "span": "confounding means our "
                       "moderators for age and sex should be interpreted cautiously"}],
         "step": "LEAK-STEP the writer's reasoning",
         "check_flags": [{"check": "B19", "verdict": "evidence hedge dropped",
                          "why": "LEAK-FLAG"}],
         "verdicts": {"locatable": "LEAK-VERDICT"},
         "gate_findings": ["LEAK-GATE"]}
    r.update(kw)
    return r


@pytest.fixture
def issue(tmp_path, monkeypatch):
    """A fixture issue: a bindings doc held in memory, a review file in tmp."""
    doc = {"bindings": {"r85": row(S85), "r56": row(S56), "rhold": row(HOLD),
                        "rctx": row("A context sentence.", bucket="context"),
                        "roff": row("Gone from the page.", on_page=False)}}
    monkeypatch.setattr(CJ, "_bindings_doc", lambda slug: doc)
    monkeypatch.setattr(CJ, "review_path", lambda slug: tmp_path / CJ.REVIEW_FILE)
    monkeypatch.setattr(CJ, "access_states", lambda slug: {"S001": "full_text_held"})
    monkeypatch.setattr(CJ, "page_text",
                        lambda slug: "Before the conclusion. " + S85 + " After it.")
    monkeypatch.syspath_prepend(str(WHU))
    return doc


class Ask:
    """Stands in for factcheck_draft.call; answers by sentence, records calls."""
    def __init__(self, labels):
        self.labels, self.calls = labels, []

    def __call__(self, system, user):
        self.calls.append(user)
        for key, lab in self.labels.items():
            if key in user:
                return lab if not isinstance(lab, str) else {"label": lab,
                                                              "reason": "because"}
        return {"label": "SUPPORTED", "reason": "matches"}


def entries(tmp_review):
    return json.loads(tmp_review.read_text())["sentences"]


# --- which sentences ---------------------------------------------------------

def test_only_on_page_non_holdings_judgements_are_judged(issue):
    assert [k for k, _ in CJ.judged_rows(issue)] == ["r85", "r56"]


def test_holdings_are_excluded_by_the_b21_detector(issue):
    import bindings as B
    assert B.is_holdings(HOLD) and not B.is_holdings(S85)
    assert CJ._is_holdings(HOLD) is True


def test_fingerprint_is_bindings_fingerprint(issue):
    import bindings as B
    for s in (S85, S56, "  spaced \n  out  "):
        assert CJ.fingerprint(s) == B.fingerprint(s)


# --- what the judge sees -----------------------------------------------------

def test_the_step_and_every_pipeline_conclusion_are_absent_from_the_input():
    u = CJ.SYSTEM + CJ.build_user(row(S85), "ctx", {"S001": "full_text_held"})
    assert "LEAK" not in u
    assert "stated reasoning" not in u
    assert "B19" not in u and "hedge dropped" not in u


def test_the_input_is_the_round_two_mode_a_prompt():
    u = CJ.build_user(row(S85), "before … after", {"S001": "abstract_held"})
    lines = u.split("\n")
    assert lines[0] == "Conclusion: " + S85
    assert lines[1] == "Surrounding text: before … after"
    assert lines[2] == "Evidence (source id, how much of the source was read, passage):"
    assert lines[3] == ('(S001, abstract_held, "confounding means our moderators for '
                        'age and sex should be interpreted cautiously")')
    joined = CJ.SYSTEM + "\n\n" + u
    assert joined.startswith("You are checking one conclusion from a research summary")
    assert joined.endswith('Reply with JSON only: {"label": "...", "reason": "one or '
                           'two sentences naming the exact words in the conclusion '
                           'and in the evidence that decide it"}')


def test_the_judge_is_sonnet_only():
    assert CJ.JUDGE_MODEL == "claude-sonnet-4-6"
    src = (WHU / "conclusion_judge.py").read_text(encoding="utf-8")
    assert "claude-opus" not in src


# --- verdicts and the flag rule ----------------------------------------------

@pytest.mark.parametrize("label,flag", [("SUPPORTED", False), ("OVERSTATES", True),
                                        ("UNDERSTATES", True), ("NOT_IN_EVIDENCE", True),
                                        ("CONTRADICTED", True), ("UNPARSEABLE", True)])
def test_flag_rule(label, flag):
    assert CJ.is_flagged(label) is flag


@pytest.mark.parametrize("reply", [None, ["x"], {"label": "FINE", "reason": "x"},
                                   {"label": "SUPPORTED"}, {"label": "SUPPORTED",
                                                            "reason": " "}])
def test_an_unparseable_reply_is_unparseable_and_flagged(reply):
    v = CJ.parse_verdict(reply)
    assert v["label"] == CJ.UNPARSEABLE and CJ.is_flagged(v["label"])


# --- the review and re-runs --------------------------------------------------

def test_judge_writes_the_review_with_empty_decisions_on_flags(issue, tmp_path):
    ask = Ask({"does not support choosing": "OVERSTATES"})
    t = CJ.judge(SLUG, ask=ask, today="2026-10-17")
    assert t == {"judged": 2, "kept": 0, "flagged": 1}
    assert len(ask.calls) == 2 and not any(HOLD in c for c in ask.calls)
    e = entries(tmp_path / CJ.REVIEW_FILE)
    assert e["r85"] == {"sentence_sha": CJ.fingerprint(S85), "sentence": S85,
                        "label": "OVERSTATES", "reason": "because",
                        "model": "claude-sonnet-4-6", "run_on": "2026-10-17",
                        "flagged": True, "decision": {"decision": None, "by": None,
                                                      "on": None, "why": None}}
    assert e["r56"]["flagged"] is False and "decision" not in e["r56"]
    assert "Before the conclusion" in ask.calls[0]       # surrounding text reached it


def test_a_rerun_keeps_decisions_and_does_not_call_again_when_unchanged(issue, tmp_path):
    CJ.judge(SLUG, ask=Ask({"does not support choosing": "OVERSTATES"}), today="2026-10-17")
    CJ.decide(SLUG, CJ.fingerprint(S85)[:8], "rejected", "Fred Ugast",
              "The paper's caution is about moderators, which is what the sentence says.",
              today="2026-10-18")
    again = Ask({})
    t = CJ.judge(SLUG, ask=again, today="2026-10-19")
    assert again.calls == [] and t["kept"] == 2 and t["judged"] == 0
    d = entries(tmp_path / CJ.REVIEW_FILE)["r85"]["decision"]
    assert d["decision"] == "rejected" and d["on"] == "2026-10-18"


def test_a_changed_sentence_is_rejudged_and_its_old_decision_marked_stale(issue, tmp_path):
    CJ.judge(SLUG, ask=Ask({"does not support choosing": "OVERSTATES"}), today="2026-10-17")
    CJ.decide(SLUG, CJ.fingerprint(S85)[:8], "accepted", "Fred Ugast", "fixed below")
    issue["bindings"]["r85"]["sentence"] = S85.replace("does not support",
                                                       "gives little basis for")
    ask = Ask({"gives little basis": "OVERSTATES"})
    CJ.judge(SLUG, ask=ask, today="2026-10-20")
    assert len(ask.calls) == 1
    e = entries(tmp_path / CJ.REVIEW_FILE)["r85"]
    assert e["decision"] == {"decision": None, "by": None, "on": None, "why": None}
    assert e["previous"][0]["decision"]["decision"] == "accepted"
    assert e["previous"][0]["decision"]["stale"] is True
    assert e["previous"][0]["sentence"] == S85


# --- decide ------------------------------------------------------------------

def test_decide_writes_the_date_and_refuses_what_it_must(issue, tmp_path):
    CJ.judge(SLUG, ask=Ask({"does not support choosing": "OVERSTATES"}), today="2026-10-17")
    sha = CJ.fingerprint(S85)
    with pytest.raises(ValueError):
        CJ.decide(SLUG, sha, "fine", "Fred Ugast", "x")                 # not a decision
    with pytest.raises(ValueError):
        CJ.decide(SLUG, sha, "accepted", "  ", "x")                     # nobody named
    with pytest.raises(ValueError):
        CJ.decide(SLUG, sha, "accepted", "Fred Ugast", "")              # no reason
    with pytest.raises(ValueError):
        CJ.decide(SLUG, CJ.fingerprint(S56), "accepted", "Fred Ugast", "x")  # not flagged
    with pytest.raises(ValueError):
        CJ.decide(SLUG, sha[:4], "accepted", "Fred Ugast", "x")         # prefix too short
    e = CJ.decide(SLUG, sha[:8], "judgement", "Fred Ugast", "a call about emphasis",
                  today="2026-10-18")
    assert e["decision"] == {"decision": "judgement", "by": "Fred Ugast",
                             "on": "2026-10-18", "why": "a call about emphasis"}


def test_the_decide_command(issue, tmp_path, capsys):
    CJ.judge(SLUG, ask=Ask({"does not support choosing": "OVERSTATES"}), today="2026-10-17")
    sha = CJ.fingerprint(S85)
    assert CJ.main([SLUG, "decide", sha, "rejected", "--by", "Fred Ugast",
                    "--why", "the caution is preserved"]) == 0
    assert "rejected by Fred Ugast" in capsys.readouterr().out
    with pytest.raises(SystemExit):                    # argparse refuses it first
        CJ.main([SLUG, "decide", sha, "maybe", "--by", "x", "--why", "y"])
    assert CJ.main([SLUG, "decide", sha, "accepted", "--by", " ", "--why", "y"]) == 1


# --- preflight ---------------------------------------------------------------

def states(rows):
    return [(st, d) for _l, st, d in rows]


def test_preflight_blocks_with_no_review(issue):
    [(st, d)] = states(CJ.preflight_rows(SLUG, []))
    assert st == CJ.BAD and "no conclusion-review.json" in d and "conclusion_judge.py" in d


def test_preflight_blocks_when_a_conclusion_has_no_verdict(issue):
    CJ.judge(SLUG, ask=Ask({}), today="2026-10-17")
    issue["bindings"]["rnew"] = row("A conclusion written after the judge ran.")
    [(st, d)] = states(CJ.preflight_rows(SLUG, []))
    assert st == CJ.BAD and "1 of 3" in d and "Re-run" in d


def test_preflight_blocks_when_a_sentence_changed_after_the_run(issue):
    CJ.judge(SLUG, ask=Ask({}), today="2026-10-17")
    issue["bindings"]["r56"]["sentence"] = S56 + " Edited."
    [(st, d)] = states(CJ.preflight_rows(SLUG, []))
    assert st == CJ.BAD and "Re-run" in d


def test_preflight_blocks_an_undecided_flag(issue):
    CJ.judge(SLUG, ask=Ask({"does not support choosing": "OVERSTATES"}), today="2026-10-17")
    [(st, d)] = states(CJ.preflight_rows(SLUG, []))
    assert st == CJ.BAD and "no decision" in d and CJ.fingerprint(S85)[:8] in d


def test_preflight_blocks_a_stale_decision(issue, tmp_path):
    CJ.judge(SLUG, ask=Ask({"does not support choosing": "OVERSTATES"}), today="2026-10-17")
    CJ.decide(SLUG, CJ.fingerprint(S85)[:8], "accepted", "Fred Ugast", "x")
    p = tmp_path / CJ.REVIEW_FILE
    doc = json.loads(p.read_text())
    doc["sentences"]["r85"]["decision"]["stale"] = True
    p.write_text(json.dumps(doc))
    [(st, d)] = states(CJ.preflight_rows(SLUG, []))
    assert st == CJ.BAD and "stale" in d


def test_preflight_ok_with_counts_once_every_flag_is_decided(issue):
    CJ.judge(SLUG, ask=Ask({"does not support choosing": "OVERSTATES"}), today="2026-10-17")
    CJ.decide(SLUG, CJ.fingerprint(S85)[:8], "rejected", "Fred Ugast", "fine as worded")
    [(st, d)] = states(CJ.preflight_rows(SLUG, []))
    assert st == CJ.OK and d == "2 conclusion(s) judged, 1 flagged, 1 decided"


def test_an_issue_published_before_adoption_is_skipped_by_name(issue):
    rec = [{"issue": SLUG, "action": "publish", "at": "2026-08-28T16:05:57+00:00"}]
    [(st, d)] = states(CJ.preflight_rows(SLUG, rec))
    assert st == CJ.OK and d.startswith("SKIPPED") and "2026-08-28" in d


@pytest.mark.parametrize("rec", [
    [],                                                                     # never published
    [{"issue": SLUG, "action": "publish", "at": "2026-11-01T09:00:00+00:00"}],  # after adoption
    [{"issue": SLUG, "action": "announce", "at": "2026-08-28T16:05:57+00:00"}],  # a send is not a publish
    [{"issue": "melanoma", "action": "publish", "at": "2026-08-28T16:05:57+00:00"}],  # another issue
])
def test_no_other_record_exempts_an_issue(issue, rec):
    [(st, _d)] = states(CJ.preflight_rows(SLUG, rec))
    assert st == CJ.BAD


def test_preflight_uses_publish_vocabulary():
    assert (CJ.OK, CJ.BAD, CJ.WARN) == ("ok", "BLOCKED", "warn")


# --- wiring ------------------------------------------------------------------

def test_publish_runs_the_row_and_holds_it_unwaivable_on_a_send():
    src = (WHU / "publish.py").read_text(encoding="utf-8")
    assert 'conclusion_judge = _sibling("conclusion_judge")' in src
    assert "conclusion_judge.preflight_rows(slug, load_record())" in src
    pub = src.split("UNWAIVABLE_ON_SEND = {", 1)[1].split("\n}", 1)[0]
    assert '"%s"' % CJ.ROW_LABEL in pub


def test_importing_the_stage_does_not_load_the_paid_call_module():
    src = (WHU / "conclusion_judge.py").read_text(encoding="utf-8")
    top = src.split('"""', 2)[-1].split("\ndef ")[0]
    assert "factcheck" not in top
