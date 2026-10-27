"""Protected sentences (post-study fix 1, 2026-10-27).

The question restatement and the statements of what WHU held, read or did not
read are never put to a source-support ruling, and the preflight stops if one
left the page without a person's sign-off. The cases are WHU-S08's: its first
full draft (790f830, fixtures/whatholdsup/whu_s08_first_draft_790f830.html)
replayed against the rulings that rewrote or cut those sentences --
conclusion rulings b6caee39a4c1249d and 125d538dde6fcc01, audit units u45,
u46, u47 and u14 -- with u5 (the standfirst's conclusion, not a protected
sentence) as the control that must still be ruled.

No model is called. The fakes answer from the prompt they are sent and never
choose which sentences reach them: the real selection code (judged_rows,
_conclusion_items, the audit's queue) does, so a broken filter shows up as a
prompt the fake should never have seen.
"""
import importlib.util
import json
import re
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


import bindings as B                                   # noqa: E402
import conclusion_judge as CJ                          # noqa: E402
import protected as PR                                 # noqa: E402
A = _load("audit_stage_protected_t", WHU / "audit_stage.py")
R = _load("ruling_protected_t", WHU / "ruling.py")

SLUG = "settlement-planning-climate-resilience"
FIRST_HTML = (ROOT / "backend" / "tests" / "fixtures" / "whatholdsup" /
              "whu_s08_first_draft_790f830.html").read_text(encoding="utf-8")
FINAL_PAGE = ROOT / "issues" / "WHU-S08-settlement-planning-climate-resilience" / "draft" / \
    "settlement-planning-climate-resilience.html"

# The first draft's sentences, as page_sentences splits them.
FIRST = B.page_sentences(SLUG, html=FIRST_HTML)


def _first(prefix: str) -> str:
    [s] = [s for s in FIRST if s.startswith(prefix)]
    return s


QUESTION = _first("The question is whether taking climate change")          # b6caee39a4c1249d
LIMITS = _first("We did not search the grey literature")                    # 125d538d; audit u47
IPCC_READ = _first("Of the IPCC chapter, we drew on")                       # audit u46, u45
STOCKTAKE = _first("This stocktake covers adaptation of every kind")         # audit u14
STANDFIRST = _first("In our reading, the reviews and assessment we read")    # audit u5 (control)
LARGEST = _first("Very little, in the largest stocktake")                   # 7b2ff781 (control)

# What the S08 rulings put in their place (rulings.jsonl and audit rulings).
RULED = {
    QUESTION: "The question is whether implemented adaptation responses to climate change are effective.",
    LIMITS: "The stocktake's authors say the grey literature may hold more evidence of risk reduction.",
    IPCC_READ: "Of the IPCC chapter, we cite its section on land use planning (6.3.3.1).",
    STOCKTAKE: ("This stocktake focuses on observed and implemented adaptation responses rather than "
                "processes of decision-making, adaptation governance and planning."),
    STANDFIRST: STANDFIRST.replace("evidence about people’s wellbeing is thinner still",
                                   "evidence about effects on people's health is also scarce"),
    LARGEST: ("Very little, in a systematic and comprehensive global stocktake of adaptation that has "
              "actually been implemented."),
}
PROTECTED = (QUESTION, LIMITS, IPCC_READ, STOCKTAKE)
CONTROLS = (STANDFIRST, LARGEST)


# ----------------------------------------------------------------- the class

def test_the_s08_question_and_reading_statements_are_protected():
    assert B.protected_kind(QUESTION) == "question"
    for s in (LIMITS, IPCC_READ, STOCKTAKE):
        assert B.protected_kind(s) == "reading", s
    # the holdings sentences B21 already knew
    assert B.protected_kind("We hold four documents: two systematic reviews, one assessment chapter "
                            "and one evaluation.") == "reading"
    assert B.protected_kind("Two widely cited meta-analyses of the built environment and travel were "
                            "behind paywalls we could not pass.") == "reading"


def test_conclusions_that_merely_say_we_read_are_not_protected():
    for s in CONTROLS + ("On what we read, the belief is a reasonable expectation rather than a "
                         "demonstrated result.",
                         "The reviews we read find the benefit mostly assumed rather than measured.",
                         "The assessment we read supports combining zoning with other measures."):
        assert B.protected_kind(s) is None, s


def test_a_row_marker_protects_what_the_phrasing_misses_and_nothing_else_does():
    assert B.protected_kind(STANDFIRST, {"protected": "question"}) == "question"
    assert B.protected_kind(STANDFIRST, {"protected": "yes"}) is None


def test_b21_routing_is_unchanged():
    # HOLDINGS is not widened: B21 still routes only what it routed before.
    assert not B.is_holdings(LIMITS) and not B.is_holdings(QUESTION) and not B.is_holdings(IPCC_READ)


# ----------------------------------------------------------------- the conclusion judge

def _rows(sentences):
    return {B.fingerprint(s): {"sentence": s, "on_page": True, "bucket": "judgement",
                               "premises": [{"source_id": "S001", "span": "x"}]} for s in sentences}


def test_the_conclusion_judge_never_selects_a_protected_sentence():
    rows = _rows(FIRST)
    judged = {r["sentence"] for _k, r in CJ.judged_rows({"bindings": rows})}
    for s in PROTECTED:
        assert s not in judged, s
    for s in CONTROLS:
        assert s in judged, s


class RulingFake:
    """Replies to a ruling prompt with what S08's ruling model ruled for the
    sentence in it. Records every prompt."""

    def __init__(self):
        self.prompts = []

    def __call__(self, prompt, max_tokens, role):
        self.prompts.append(prompt)
        hit = [s for s in RULED if s in prompt]
        assert len(hit) == 1, "the fake was sent a sentence it has no S08 ruling for"
        return json.dumps({"ruling": "amend", "text": RULED[hit[0]], "reason": "replayed"}), \
            {"input": 10, "output": 5, "usd": 0.0}


@pytest.fixture
def study(tmp_path, monkeypatch):
    d = tmp_path / ("WHU-S99-%s" % SLUG)
    d.mkdir()
    import source_store
    monkeypatch.setattr(source_store, "case_dir", lambda slug: d)
    return d, types.SimpleNamespace(is_study=lambda slug: True)


def test_replayed_conclusion_rulings_b6caee39_and_125d538d_rewrite_nothing_protected(study):
    d, P = study
    targets = (QUESTION, LIMITS) + CONTROLS
    CJ.save_review(SLUG, {"sentences": {B.fingerprint(s): {
        "sentence_sha": CJ.fingerprint(s), "sentence": s, "label": "NOT_IN_EVIDENCE", "reason": "replayed",
        "flagged": True, "decision": CJ.empty_decision()} for s in targets}})
    fake = RulingFake()
    R.rule_conclusions(SLUG, fake, P=P, rows=_rows(targets), held={})
    sent = "\n".join(fake.prompts)
    assert QUESTION not in sent and LIMITS not in sent
    assert len(fake.prompts) == 2 and all(s in sent for s in CONTROLS)
    review = CJ.load_review(SLUG)["sentences"]
    for s in (QUESTION, LIMITS):
        e = review[B.fingerprint(s)]
        assert not CJ.decided(e), "a protected sentence was decided by the ruling model"
    for s in CONTROLS:
        assert CJ.decided(review[B.fingerprint(s)])
    logged = [json.loads(l) for l in (d / "rulings" / "rulings.jsonl").read_text().splitlines()]
    assert {r["inputs"]["sentence"] for r in logged} == set(CONTROLS)


# ----------------------------------------------------------------- the audit

DOC = ("A systematic global stocktake of evidence on human adaptation. Of 1,682 articles, 58 formally "
       "assessed risk reduction outcomes after implementation. Grey literature may hold more.")
SPAN = "58 formally assessed risk reduction outcomes"
HELD = {"%s:S001" % SLUG: DOC}


def _unit(i, s):
    return {"id": "u%d" % i, "part": "page", "sentence": s, "sha": A.fingerprint(s),
            "row": {"source_id": "S001", "span": SPAN}}


class AuditFake:
    """Reads every sentence it is sent as a finding (quoting the document
    verbatim) and rules every finding with S08's text for that sentence, then
    "" (a cut) for any later round. Records every prompt."""

    def __init__(self):
        self.prompts = []

    def __call__(self, prompt, max_tokens):
        self.prompts.append(prompt)
        if "THE SENTENCES TO READ" in prompt:
            ids = re.findall(r"^\[(u\d+)\]", prompt, re.M)
            return json.dumps({"verdicts": [{
                "id": i, "verdict": "finding", "kind": "Misattributed or misdescribed",
                "evidence": [{"source": "S001", "quote": SPAN}], "proposed_text": None,
                "reason": "the source does not say this"} for i in ids]}), {"input": 100, "output": 50, "usd": 0.0}
        hit = [s for s in RULED if s in prompt]
        text = RULED[hit[0]] if hit else ""
        return json.dumps({"ruling": "amend", "text": text, "reason": "replayed"}), \
            {"input": 50, "output": 20, "usd": 0.0}


def test_replayed_audit_units_u45_u46_u47_u14_leave_protected_sentences_unchanged(tmp_path):
    us = [_unit(i, s) for i, s in enumerate(PROTECTED + (STANDFIRST,), 1)]
    fake = AuditFake()
    m = A.run(SLUG, out_dir=tmp_path, ask=fake, held=HELD, unit_list=us, cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    read_ids = {i for p in fake.prompts if "THE SENTENCES TO READ" in p
                for i in re.findall(r"^\[(u\d+)\]", p, re.M)}
    rule_prompts = "\n".join(p for p in fake.prompts if "THE SENTENCES TO READ" not in p)
    rulings = [json.loads(l) for l in (tmp_path / "rulings.jsonl").read_text().splitlines()]
    cuts = [json.loads(l) for l in (tmp_path / "cuts.jsonl").read_text().splitlines()]
    for u in us[:-1]:
        # It may stand as the context around another sentence; it is never
        # given to the reader to read, nor to the ruling model to rule.
        assert u["id"] not in read_ids, "a protected sentence was read: %r" % u["sentence"][:60]
        assert u["sentence"] not in rule_prompts, "a protected sentence was ruled: %r" % u["sentence"][:60]
        assert m["state"][u["sha"]] == A.HUMAN_READ_REQUIRED
        assert not [r for r in rulings if r["unit"] == u["id"]]
        assert not [c for c in cuts if c["unit"] == u["id"]]
        assert m["progress"]["done"][u["id"]]["sentence"] == u["sentence"]
    verdicts = [json.loads(l) for l in (tmp_path / "verdicts.jsonl").read_text().splitlines()]
    assert {v["protected"] for v in verdicts if v.get("protected")} == {"question", "reading"}
    # The control is read and ruled as before: the filter, not the fake, spared the others.
    control = us[-1]
    assert control["id"] in read_ids and control["sentence"] in rule_prompts
    assert [r for r in rulings if r["unit"] == control["id"]]
    assert m["state"][control["sha"]] == "must_leave_page"


def test_a_protected_sentence_awaits_a_persons_read_in_the_audit_preflight(tmp_path):
    u = _unit(1, IPCC_READ)
    m = A.run(SLUG, out_dir=tmp_path, ask=AuditFake(), held=HELD, unit_list=[u], cap=1.0, licensed=set())
    assert m["state"][u["sha"]] == A.HUMAN_READ_REQUIRED
    row = A.preflight_rows(SLUG, [], current=[u], run_dir=tmp_path)[0]
    assert row[1] == A.BAD and "protected sentence" in row[2]
    (tmp_path / "human_reads.jsonl").write_text(json.dumps(
        {"sha": u["sha"], "verdict": "holds", "by": "Fred Ugast", "at": "2026-10-27T18:00:00Z"}) + "\n")
    assert A.preflight_rows(SLUG, [], current=[u], run_dir=tmp_path)[0][1] == A.OK


# ----------------------------------------------------------------- the preflight

def _without(html: str, sentence: str) -> str:
    # The sentence as written in the HTML: page_sentences folds whitespace only.
    pat = r"\s+".join(re.escape(w) for w in sentence.split()).replace("’", "(?:’|&rsquo;)")
    out, n = re.subn(pat, "", html)
    assert n == 1, sentence
    return out


def test_preflight_passes_on_the_first_draft_itself():
    [row] = PR.preflight_rows(SLUG, [], first_html=FIRST_HTML, now_html=FIRST_HTML, signoffs={}, rows={})
    assert row[0] == PR.ROW_LABEL and row[1] == PR.OK, row


def test_preflight_stops_on_a_simulated_unsigned_removal():
    now = _without(FIRST_HTML, IPCC_READ)
    [row] = PR.preflight_rows(SLUG, [], first_html=FIRST_HTML, now_html=now, signoffs={}, rows={})
    assert row[1] == PR.BAD and "1 protected sentence" in row[2] and "Of the IPCC chapter" in row[2]


def test_preflight_stops_on_the_s08_page_as_it_ended():
    [row] = PR.preflight_rows(SLUG, [], first_html=FIRST_HTML, now_html=FINAL_PAGE.read_text(encoding="utf-8"),
                              signoffs={}, rows={})
    assert row[1] == PR.BAD and row[2].startswith("4 protected sentence(s)")


def test_a_typographic_change_is_not_a_change():
    now = FIRST_HTML.replace("stocktake&rsquo;s authors say may hold", "stocktake's authors say may hold")
    assert now != FIRST_HTML
    [row] = PR.preflight_rows(SLUG, [], first_html=FIRST_HTML, now_html=now, signoffs={}, rows={})
    assert row[1] == PR.OK, row


def _repo(tmp_path, line: str, trailer: bool) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    git = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True)
    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    (root / "accept.md").write_text("# Acceptance\n%s\n" % line)
    git("add", "accept.md")
    git("commit", "-q", "-m", "acceptance" + ("\n\nCo-Authored-By: Claude <noreply@anthropic.com>" if trailer else ""))
    return root


def _signoff(by: str, sentence: str = IPCC_READ, why: str = "the chapter's reading is stated elsewhere"):
    return {"signoffs": [{"sentence_sha": B.fingerprint(sentence), "first_draft": sentence, "now": None,
                          "why": why, "by": by,
                          "signature": {"statement": "Accepted.", "source": "accept.md:2"}}]}


ACCEPT = "Accepted by Fred Ugast, 27 October 2026, stated in session"


def test_a_persons_committed_sign_off_lets_the_removal_pass(tmp_path):
    root = _repo(tmp_path, ACCEPT, trailer=False)
    now = _without(FIRST_HTML, IPCC_READ)
    [row] = PR.preflight_rows(SLUG, [], first_html=FIRST_HTML, now_html=now,
                              signoffs=_signoff("Fred Ugast"), rows={}, root=root)
    assert row[1] == PR.OK and "each with a person's sign-off" in row[2], row


def test_an_agent_a_trailer_commit_or_no_reason_is_not_a_sign_off(tmp_path):
    now = _without(FIRST_HTML, IPCC_READ)
    good = _repo(tmp_path, ACCEPT, trailer=False)
    for doc, root in ((_signoff("Claude Code"), good),
                      (_signoff("Fred Ugast", why=""), good)):
        [row] = PR.preflight_rows(SLUG, [], first_html=FIRST_HTML, now_html=now, signoffs=doc, rows={}, root=root)
        assert row[1] == PR.BAD, doc
    bad = tmp_path / "second"
    bad.mkdir()
    root = _repo(bad, ACCEPT, trailer=True)
    [row] = PR.preflight_rows(SLUG, [], first_html=FIRST_HTML, now_html=now,
                              signoffs=_signoff("Fred Ugast"), rows={}, root=root)
    assert row[1] == PR.BAD and "trailer" in row[2]


def test_a_sign_off_covers_only_the_sentence_it_names(tmp_path):
    root = _repo(tmp_path, ACCEPT, trailer=False)
    now = _without(_without(FIRST_HTML, IPCC_READ), LIMITS)
    [row] = PR.preflight_rows(SLUG, [], first_html=FIRST_HTML, now_html=now,
                              signoffs=_signoff("Fred Ugast"), rows={}, root=root)
    assert row[1] == PR.BAD and "We did not search" in row[2]


def test_an_issue_published_before_adoption_is_skipped_by_name():
    [row] = PR.preflight_rows("x", [{"issue": "x", "action": "publish", "at": "2026-09-01T00:00:00+00:00"}])
    assert row[1] == PR.OK and row[2].startswith("SKIPPED")


def test_publish_preflight_carries_the_row():
    src = (WHU / "publish.py").read_text(encoding="utf-8")
    assert 'protected = _sibling("protected")' in src
    assert "protected.preflight_rows(slug, load_record())" in src
    assert "(protected.ROW_LABEL, BAD," in src


# ----------------------------------------------------------------- review of fix 1 (2026-10-27)

def test_absence_of_evidence_claims_stay_audited_and_reading_statements_stay_protected():
    for s in ("We could not find any trial showing X.",
              "We searched PubMed and found no trials.",
              "We hold two reviews, and none of them reports cure.",
              "We did not read the appendix, which shows no effect."):
        assert B.protected_kind(s) is None, s
    for s in ("We did not search the grey literature.",
              "Of the IPCC chapter, we drew on its executive summary."):
        assert B.protected_kind(s) == "reading", s
    # A person may still protect a finding-bearing sentence by hand.
    assert B.protected_kind("We searched PubMed and found no trials.", {"protected": "reading"}) == "reading"


ADVOCATE_TEXT = (   # S08 advocate ruling 8ae1718065708594 (rulings.jsonl:5)
    "This stocktake covers implemented adaptation responses and explicitly excludes processes of "
    "decision-making, adaptation governance and planning; we read it for what it says about how outcomes "
    "are measured among implemented responses, not as evidence about planning studies.")


def _advocate_case(d, monkeypatch, claims):
    import source_advocate as SA
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: d)
    briefs = [{"source": "S001", "title": "t", "principal": "p", "state": "full_text_held", "mode": "objections",
               "objections": [{"severity": "SERIOUS", "claim_quoted": c, "objection": "replayed",
                               "why": "w", "source_says": "", "locator": "l"} for c in claims]}]
    (d / "advocate").mkdir(exist_ok=True)
    (d / "advocate" / "2026-10-25-briefs.json").write_text(json.dumps(briefs))
    SA.write_template(SLUG, "2026-10-25", briefs)
    return SA


def test_replayed_advocate_ruling_8ae17180_leaves_the_stocktake_sentence_to_a_person(study, monkeypatch):
    d, P = study
    SA = _advocate_case(d, monkeypatch, [STOCKTAKE, LARGEST])

    class Fake:
        prompts = []

        def __call__(self, prompt, max_tokens, role):
            self.prompts.append(prompt)
            text = ADVOCATE_TEXT if STOCKTAKE in prompt else RULED[LARGEST]
            return json.dumps({"ruling": "amend", "text": text, "reason": "replayed"}), \
                {"input": 10, "output": 5, "usd": 0.0}
    fake = Fake()
    done = R.rule_advocate(SLUG, fake, P=P, rows=_rows([STOCKTAKE, LARGEST]), held={}, case=d)
    # Only the control reached the ruling model, and only it was closed.
    assert len(fake.prompts) == 1 and LARGEST in fake.prompts[0] and STOCKTAKE not in fake.prompts[0]
    assert [x["item"] for x in done] == ["S001-02"]
    still_open = [it["objection"]["claim_quoted"] for it in R.advocate_items(SLUG, d)]
    assert still_open == [STOCKTAKE]
    assert ADVOCATE_TEXT not in (d / "advocate" / "2026-10-25-adjudication.md").read_text()
    [rec] = [json.loads(l) for l in (d / "rulings" / R.FOR_PERSON).read_text().splitlines()]
    assert rec["mode"] == "advocate" and rec["protected"] == "reading" and rec["sentence"] == STOCKTAKE
    assert len(R.by_sentence(R.split_protected(R._advocate_items(SLUG, _rows([STOCKTAKE]), {}, d),
                                               _rows([STOCKTAKE]))[0])) == 0


def test_a_gate_finding_on_a_protected_sentence_is_left_open_for_a_person(study):
    d, P = study
    import findings as F
    F.save(SLUG, {"findings": [{"id": "obj-1", "kind": "fairness", "gate_said": "x", "decision": ""}]})
    report = {"objections": [{"quote": "We did not search the grey literature", "severity": "SERIOUS"}]}

    def fake(prompt, max_tokens, role):
        raise AssertionError("a protected sentence reached the ruling model")
    assert R.rule_gate(SLUG, fake, P=P, report=report, rows=_rows([LIMITS]), held={}) == []
    assert F.load(SLUG)["findings"][0]["decision"] == ""
    [rec] = [json.loads(l) for l in (d / "rulings" / R.FOR_PERSON).read_text().splitlines()]
    assert rec["mode"] == "gate" and rec["sentence"] == LIMITS


def test_changecheck_and_dangling_items_on_protected_sentences_are_split_off():
    # Both modes key an item by its row when the sentence has one, else by text.
    items = [{"key": ("text", "q"), "sentence": QUESTION, "kind": "dangling reference"},
             {"key": ("row", B.fingerprint(IPCC_READ)), "sentence": IPCC_READ, "kind": "changecheck: CONTRADICTION"},
             {"key": ("text", "c"), "sentence": LARGEST, "kind": "changecheck: CONTRADICTION"}]
    keep, person = R.split_protected(items, _rows([IPCC_READ]))
    assert [i["sentence"] for i in keep] == [LARGEST]
    assert [(i["sentence"], i["protected"]) for i in person] == [(QUESTION, "question"), (IPCC_READ, "reading")]
