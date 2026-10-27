"""Fix 2, step 4: the omission ruling (post-study, 2026-10-27).

docs/whu-fix2-omission-rulings-design.md, sections 2 and 6. No model is called.
Every fake answers only from the prompt it is sent; what reaches it, and what
is done with its answer, is decided by the code under test (omissions.precheck,
merge, scope_element_ok, the span check, placement, budgets).

The REPLAYS read real study records -- the advocate briefs, binding rows and
held texts of WHU-S07 and WHU-S03, which are never committed (RUN.md ruling 3)
-- and are skipped where those are absent (CI). They copy the briefs into a
temporary case directory; no issue file is written.
"""
import json
import re
import shutil
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))

import bindings as B           # noqa: E402
import consistency as CS       # noqa: E402
import omissions as O          # noqa: E402
import ruling as R             # noqa: E402
import source_advocate as SA   # noqa: E402

TEXT = ("Section 1. Changes in layout could reduce emissions in developed countries (high confidence). "
        "Investment in public transport can further support a shift to less intensive modes (high confidence). "
        "Some changes could lead to induced demand (medium confidence).")
HELD = {"S003": TEXT}
OMITTED = "Investment in public transport can further support a shift to less intensive modes (high confidence)."
BOUND = "Changes in layout could reduce emissions in developed countries (high confidence)."
QUESTION = ("Could changing how cities are laid out, together with measures such as transport pricing, "
            "cut greenhouse gas emissions from transport?")
SCOPE = {"question": QUESTION, "covers": "layout and pricing",
         "out": [{"what": "freight logistics", "why": "the question is about how cities are laid out"}]}
PAGE = ["The question is whether layout and pricing cut transport emissions.",
        "The assessment finds that layout changes could reduce emissions.",
        "Measured effects come mostly from pricing.",
        "We did not search the grey literature."]
for i in range(16):
    PAGE.append("Filler sentence number %d about pricing." % i)
ROWS = {B.fingerprint(PAGE[1]): {"sentence": PAGE[1], "on_page": True, "source_id": "S003", "span": BOUND}}
P = types.SimpleNamespace(is_study=lambda slug: True)
SLUG = "fix2-demo"


def _case(tmp_path, monkeypatch, objections, source="S003", name="2026-10-27"):
    import source_store
    monkeypatch.setattr(SA.sl, "case_dir", lambda slug: tmp_path)
    monkeypatch.setattr(source_store, "case_dir", lambda slug: tmp_path)
    briefs = [{"source": source, "title": "t", "principal": "the authors", "state": "full_text_held",
               "mode": "objections", "objections": objections}]
    (tmp_path / "advocate").mkdir(exist_ok=True)
    (tmp_path / "advocate" / ("%s-briefs.json" % name)).write_text(json.dumps(briefs))
    SA.write_template(SLUG, name, briefs, name)
    return tmp_path / "advocate" / ("%s-adjudication.md" % name)


def _obj(quote, anchor=PAGE[1], severity="SERIOUS", changes="NARROWS", type_="LEAVES_OUT"):
    return {"type": type_, "claim_quoted": anchor, "objection": "ADVOCATE-PROSE-LEAK the page omits this",
            "source_says": quote, "severity": severity, "changes_conclusion": changes, "why": "w"}


class Fake:
    """Answers the omission prompt with REPLY, filling the span from the
    finding quoted in the prompt when asked to (span="FROM_PROMPT")."""

    def __init__(self, reply):
        self.reply, self.prompts = reply, []

    def __call__(self, prompt, max_tokens, role):
        self.prompts.append(prompt)
        r = dict(self.reply)
        m = re.search(r'Quotation: "(.*)"\nIn its document', prompt, re.S)
        if r.get("span") == "FROM_PROMPT":
            r["span"] = m.group(1)
            r["draft_text"] = "The assessment finds that " + m.group(1)[0].lower() + m.group(1)[1:]
        return json.dumps(r), {"input": 10, "output": 5, "usd": 0.0}


def never(prompt, max_tokens, role):
    raise AssertionError("the model was called")


def _run(tmp_path, fake, **kw):
    args = dict(P=P, rows=ROWS, held=HELD, case=tmp_path, page_sentences=PAGE, scope=SCOPE,
                reader="a planner", licensed=set())
    args.update(kw)
    return R.rule_omissions(SLUG, fake, **args)


def _chunk(adj, head):
    return [c for c in adj.read_text().split("### ")[1:] if c.startswith(head)][0]


ADD = {"in_scope": True, "material": True, "outcome": "ADD", "span": "FROM_PROMPT", "reason": "answers it"}


# ----------------------------------------------------------------- outcomes on synthetic text

def test_a_fabricated_quotation_is_not_in_source_with_no_model_call(tmp_path, monkeypatch):
    adj = _case(tmp_path, monkeypatch, [_obj("Public transport always halves emissions.")])
    [d] = _run(tmp_path, never)
    assert d["outcome"] == O.NOT_IN_SOURCE
    assert "OMISSION: not_in_source" in _chunk(adj, "S003-01") and SA._closed("### " + _chunk(adj, "S003-01"), "objections")
    [e] = O.load(tmp_path)["omissions"]
    assert e["outcome"] == O.NOT_IN_SOURCE and e["by"] == "code (omissions.precheck)"


def test_an_add_is_placed_after_its_anchor_and_recorded_without_source_text(tmp_path, monkeypatch):
    adj = _case(tmp_path, monkeypatch, [_obj(OMITTED)])
    fake = Fake(ADD)
    [d] = _run(tmp_path, fake)
    assert d["outcome"] == "ADD" and d["insert_after"] == PAGE[1] and d["span"] == OMITTED
    assert d["text"].startswith("The assessment finds that investment in public transport")
    assert "OMISSION: add" in _chunk(adj, "S003-01")
    assert O.leaks_source_text(tmp_path, HELD) == []
    [e] = O.load(tmp_path)["omissions"]
    assert e["on_page"] == B.fingerprint(d["text"]) and e["ruling"]
    # the payload is the allow-list: no source id, no advocate prose
    assert "ADVOCATE-PROSE-LEAK" not in fake.prompts[0] and "S003" not in fake.prompts[0]
    assert QUESTION in fake.prompts[0] and "freight logistics" in fake.prompts[0]


def test_an_add_whose_span_is_not_in_the_finding_goes_to_a_person(tmp_path, monkeypatch):
    adj = _case(tmp_path, monkeypatch, [_obj(OMITTED)])
    [d] = _run(tmp_path, Fake(dict(ADD, span="Public transport always halves emissions.",
                                   draft_text="It always halves them.")))
    assert d["outcome"] == O.TO_PERSON and "span is not in the finding" in d["why"]
    assert not SA._closed("### " + _chunk(adj, "S003-01"), "objections")
    assert (tmp_path / "rulings" / R.FOR_PERSON).exists()


def test_out_of_scope_must_name_the_question_or_a_scope_entry(tmp_path, monkeypatch):
    adj = _case(tmp_path, monkeypatch, [_obj(OMITTED)])
    [d] = _run(tmp_path, Fake({"in_scope": False, "material": False, "outcome": "OUT_OF_SCOPE",
                               "scope_element": "freight logistics", "reason": "about freight"}))
    assert d["outcome"] == O.OUT_OF_SCOPE and "OMISSION: out_of_scope" in _chunk(adj, "S003-01")
    adj2 = _case(tmp_path / "b", monkeypatch, [_obj(OMITTED)]) if (tmp_path / "b").mkdir() is None else None
    [d2] = _run(tmp_path / "b", Fake({"in_scope": False, "material": False, "outcome": "OUT_OF_SCOPE",
                                      "scope_element": "the economics of electric buses", "reason": "r"}))
    assert d2["outcome"] == O.TO_PERSON and "refused by code" in d2["why"]
    assert not SA._closed("### " + _chunk(adj2, "S003-01"), "objections")


def test_not_material_on_a_serious_objection_that_changes_the_conclusion_goes_to_a_person(tmp_path, monkeypatch):
    _case(tmp_path, monkeypatch, [_obj(OMITTED, changes="CHANGES")])
    [d] = _run(tmp_path, Fake({"in_scope": True, "material": False, "outcome": "NOT_MATERIAL", "reason": "r"}))
    assert d["outcome"] == O.TO_PERSON


def test_an_add_never_goes_into_or_in_place_of_a_protected_anchor(tmp_path, monkeypatch):
    _case(tmp_path, monkeypatch, [_obj(OMITTED, anchor="We did not search the grey literature")])
    [d] = _run(tmp_path, Fake(ADD))
    assert d["outcome"] == "ADD" and d["insert_after"] == PAGE[2]
    assert "after the nearest unprotected sentence" in d["placement"]


def test_adds_past_the_budget_go_to_a_person(tmp_path, monkeypatch):
    two = [_obj(OMITTED), _obj("Some changes could lead to induced demand (medium confidence).")]
    _case(tmp_path, monkeypatch, two)
    ds = _run(tmp_path, Fake(ADD), page_sentences=PAGE[:10])          # budget min(8, 15% of 10) = 1
    assert [d["outcome"] for d in ds] == ["ADD", O.TO_PERSON] and "ADD budget" in ds[1]["why"]


def test_overlapping_objections_are_one_ruling(tmp_path, monkeypatch):
    _case(tmp_path, monkeypatch, [_obj(OMITTED), _obj("public transport can further support a shift")])
    fake = Fake(ADD)
    [d] = _run(tmp_path, fake)
    assert len(fake.prompts) == 1 and d["origins"] == ["S003-01", "S003-02"]


def test_the_reask_path_takes_only_a_quotation_in_the_held_text(tmp_path, monkeypatch):
    _case(tmp_path, monkeypatch, [_obj(BOUND)])         # quotes what the page already binds
    asked = []

    def reask(system, user):
        asked.append(json.loads(user))
        return {"source_says": OMITTED}
    [d] = _run(tmp_path, Fake(ADD), reask=reask)
    assert asked and asked[0]["already_on_the_page"] == [BOUND] and d["span"] == OMITTED


def test_the_advocate_mode_no_longer_rules_a_leaves_out_objection(tmp_path, monkeypatch):
    adj = _case(tmp_path, monkeypatch, [_obj(OMITTED, type_="LEAVES_OUT"),
                                        _obj(BOUND, type_="MISSTATES")])
    fake = Fake({"ruling": "reject", "text": None, "reason": "supported"})
    R.rule_advocate(SLUG, fake, P=P, rows=ROWS, held=HELD, case=tmp_path)
    assert len(fake.prompts) == 1
    assert not SA._closed("### " + _chunk(adj, "S003-01"), "objections")
    assert SA._closed("### " + _chunk(adj, "S003-02"), "objections")


def test_the_consistency_sample_can_rerun_an_omission_ruling(tmp_path, monkeypatch):
    _case(tmp_path, monkeypatch, [_obj(OMITTED)])
    _run(tmp_path, Fake(ADD))
    [rec] = [json.loads(l) for l in (tmp_path / "rulings" / "rulings.jsonl").read_text().splitlines()]
    assert rec["ruling_kind"] == "omission" and rec["ruling"] == "add" and tuple(rec["inputs"]) == R.OMISSION_FIELDS
    assert isinstance(rec["at"], str) and rec["offsets"] == [O.locate(T, TEXT)[0] for T in [OMITTED]] + [
        O.locate(OMITTED, TEXT)[1]]                 # the timestamp is not overwritten by the offsets
    second, _u, note = CS.ruling_reask(Fake(ADD))(rec)
    assert note is None and second["ruling"] == "add" and second["text"] == rec["text"]


# ----------------------------------------------------------------- replays of the study's records

def _real(slug, case_glob, head):
    import source_store as store
    case = sorted((ROOT / "issues").glob(case_glob))
    if not case:
        pytest.skip("no case directory")
    briefs = sorted((case[0] / "advocate").glob("*-briefs.json"))
    if not briefs or not (case[0] / "bindings.json").exists():
        pytest.skip("the study's advocate briefs and bindings are private and not here")
    held = R.held_texts(slug)
    if not held:
        pytest.skip("the held texts are not here")
    return case[0], briefs[0], held


def _replay_case(tmp_path, monkeypatch, brief_file, slug):
    monkeypatch.setattr(SA.sl, "case_dir", lambda s: tmp_path)
    (tmp_path / "advocate").mkdir()
    shutil.copy(brief_file, tmp_path / "advocate" / brief_file.name)
    name = brief_file.name[:-len("-briefs.json")]
    SA.write_template(slug, name, json.loads(brief_file.read_text()), name)
    return tmp_path / "advocate" / ("%s-adjudication.md" % name)


def _only(monkeypatch, head):
    """Rule only HEAD: the replay is of one study objection."""
    real = R._leaves_out
    monkeypatch.setattr(R, "_leaves_out", lambda slug, case=None: [it for it in real(slug, case) if it["head"] == head])


def test_replay_s07_s003_13_is_added(tmp_path, monkeypatch):
    slug = "urban-form-transport-emissions"
    case, brief, held = _real(slug, "WHU-S07-*", "S003-13")
    adj = _replay_case(tmp_path, monkeypatch, brief, slug)
    _only(monkeypatch, "S003-13")
    import premise as PM
    fake = Fake(dict(ADD))
    ds = R.rule_omissions(slug, fake, P=P, rows=B.load(slug)["bindings"], held=held, case=tmp_path,
                          page_sentences=B.page_sentences(slug), scope=PM.scope_of(slug), licensed=set(),
                          reask=lambda s, u: pytest.fail("S003-13 quotes the omitted sentences; no re-ask"))
    [d] = ds
    assert d["outcome"] == "ADD", d
    assert d["insert_after"].endswith("but the sources narrow it in two ways.")
    # the span the fake took from the prompt is in the held text, checked by the real span check
    import spancheck as SC
    assert O.locate(d["span"], held["S003"]) is not None
    assert SC.b2_present(d["span"], slug, "S003")[0] is True       # B2, over the held bytes
    assert "OMISSION: add" in _chunk(adj, "S003-13")
    assert O.leaks_source_text(tmp_path, {"S003": held["S003"]}) == []
    # the issue's own adjudication file is untouched: the replay ran on a copy
    assert "OMISSION: add" not in (case / "advocate" / adj.name).read_text()


def test_replay_s03_s002_14_is_out_of_scope(tmp_path, monkeypatch):
    slug = "public-involvement-climate-policy"
    case, brief, held = _real(slug, "WHU-S03-*", "S002-14")
    adj = _replay_case(tmp_path, monkeypatch, brief, slug)
    _only(monkeypatch, "S002-14")
    import premise as PM
    scope = PM.scope_of(slug)
    out = {"in_scope": False, "material": False, "outcome": "OUT_OF_SCOPE",
           "scope_element": "affect whether the policies win political backing and get results",
           "reason": "a recommendation on how to follow up assemblies, not an effect on backing or results"}
    [d] = R.rule_omissions(slug, Fake(out), P=P, rows=B.load(slug)["bindings"], held=held, case=tmp_path,
                           page_sentences=B.page_sentences(slug), scope=scope, licensed=set())
    assert d["outcome"] == O.OUT_OF_SCOPE and "OMISSION: out_of_scope" in _chunk(adj, "S002-14")
    assert O.leaks_source_text(tmp_path, {"S002": held["S002"]}) == []
    # twin: an element that is in neither the question nor a scope entry is refused by code
    t2 = tmp_path / "twin"
    t2.mkdir()
    _replay_case(t2, monkeypatch, brief, slug)
    [d2] = R.rule_omissions(slug, Fake(dict(out, scope_element="the design of future assemblies")), P=P,
                            rows=B.load(slug)["bindings"], held=held, case=t2,
                            page_sentences=B.page_sentences(slug), scope=scope, licensed=set())
    assert d2["outcome"] == O.TO_PERSON


def test_replay_a_fabricated_quotation_on_s03_is_not_in_source_with_no_call(tmp_path, monkeypatch):
    slug = "public-involvement-climate-policy"
    case, brief, held = _real(slug, "WHU-S03-*", "S002-14")
    briefs = json.loads(brief.read_text())
    for b in briefs:
        for o in b.get("objections") or []:
            o["source_says"] = "Citizens' assemblies doubled public support for every climate law they reviewed."
    f = tmp_path / brief.name
    f.write_text(json.dumps(briefs))
    _replay_case(tmp_path / "c", monkeypatch, f, slug) if (tmp_path / "c").mkdir() is None else None
    _only(monkeypatch, "S002-14")
    [d] = R.rule_omissions(slug, never, P=P, rows=B.load(slug)["bindings"], held=held, case=tmp_path / "c",
                           page_sentences=B.page_sentences(slug), licensed=set())
    assert d["outcome"] == O.NOT_IN_SOURCE
