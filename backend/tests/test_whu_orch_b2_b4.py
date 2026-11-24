"""Fred's terms B2-B4 after orchestrator trial 1 attempt 23 (2026-11-24), at $0: quotations matched by code in held
text (B2); the belief shown held / carried in general coverage, proposed by a web-search step and verified by code
(B3); direction and the kill-condition test answered from held sources, each quotation verified by code (B4); and the
guard fault the rehearsal found (a step charged with the previous step's calls)."""
import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
import orchestrator as O  # noqa: E402
import quotations as Q  # noqa: E402
import source_store as store  # noqa: E402
import spancheck as SC  # noqa: E402
from orch import premise_reading as P  # noqa: E402
from orch import steps as ST  # noqa: E402
from orch import writes as WR  # noqa: E402

HELD = ("The review found that teacher training improved attitudes towards inclusion in eleven of the fourteen "
        "studies. Only three studies measured learning outcomes.")
QUESTION = "Do programmes for children with disabilities work, and which kinds work best?"


@pytest.fixture
def case(tmp_path, monkeypatch):
    c = tmp_path / "issues" / "WHU-OT1-99-whu-x"
    (c / "draft").mkdir(parents=True)
    (c / "issue.json").write_text(json.dumps({"slug": "whu-x", "question": QUESTION}))
    monkeypatch.setattr(Q, "CASES", tmp_path / "issues")
    monkeypatch.setattr(store, "held", lambda slug: {"S001": {"sha256": "d" * 64, "file": "x"}})
    monkeypatch.setattr(SC, "_texts", lambda slug, sid: [("docs/x.xml", HELD)] if sid == "S001" else [])
    return c


# ----------------------------------------------------------------- B2: quotations, code only

def _page(c, *quotes):
    p = c / "draft" / "whu-x.html"
    p.write_text("<html><body><article>%s</article></body></html>" % " ".join("<p>It said <q>%s</q>.</p>" % q
                                                                              for q in quotes))
    return p


def test_a_quotation_in_held_text_is_recorded_with_source_offsets_and_hashes(case):
    page = _page(case, "teacher training improved attitudes towards inclusion in eleven of the fourteen studies")
    got = Q.match_held("whu-x", page)
    (row,) = json.loads((case / "quotations.json").read_text())["quotations"]
    assert got == {"matched": 1, "unmatched": []}
    assert row["source_id"] == "S001" and row["document_sha256"] == "d" * 64 and len(row["span_sha256"]) == 64
    a, b = row["offsets"]
    assert HELD[a:b] == row["verbatim"] and Q.quoted_in(Q.norm(row["quote"]), Q.norm(row["verbatim"]))
    assert row["attested"] == {"by": "", "on": ""}                 # nobody attests: code matched it


def test_an_unmatched_quotation_stops_the_page(case):
    page = _page(case, "teacher training transformed learning in every one of the studies reviewed")
    got = Q.match_held("whu-x", page)
    assert got["matched"] == 0 and len(got["unmatched"]) == 1
    rows = dict((r[0], r[1]) for r in Q.preflight_rows("whu-x", page.read_text(), page))
    assert Q.BAD in rows.values()


def test_an_ellipsis_quotation_matches_by_its_segments(case):
    page = _page(case, "teacher training improved attitudes … Only three studies measured learning outcomes")
    assert Q.match_held("whu-x", page)["matched"] == 1


def test_the_pages_own_question_is_its_own_voice_only_on_exact_equality(case):
    page = _page(case, QUESTION, QUESTION.replace("work best", "work better"))
    got = Q.match_held("whu-x", page)
    rows = json.loads((case / "quotations.json").read_text())["quotations"]
    kinds = {r["quote"]: r.get("kind") for r in rows}
    assert kinds[QUESTION] == "rhetorical" and got["unmatched"] == [QUESTION.replace("work best", "work better")]


def test_a_blocked_source_is_never_searched(case, monkeypatch):
    """source_store.held is the holdings gate (ruling C): only what it returns is searched."""
    monkeypatch.setattr(store, "held", lambda slug: {})
    page = _page(case, "teacher training improved attitudes towards inclusion in eleven of the fourteen studies")
    assert Q.match_held("whu-x", page)["matched"] == 0


# ----------------------------------------------------------------- B3: the belief, in a published outlet

BELIEF = "Inclusive education helps children with disabilities learn in ordinary schools."
GOOD = (b"<html><body><p>Inclusive education means all children learn together in the same schools, including "
        b"children with disabilities.</p></body></html>")


def _get(pages):
    def get(url):
        if url.endswith("/robots.txt"):
            return pages.get(url, {"status": 404, "headers": {}, "body": b"", "final_url": url})
        return pages[url]
    return get


def _ok(body=GOOD, status=200, headers=None, final=None, url="https://www.unicef.org/x"):
    return {"status": status, "headers": headers or {}, "body": body, "final_url": final or url}


def test_the_markers_are_the_check_pilots():
    tree = ast.parse((ROOT / "study/whu-reliability/check_pilot/pipeline_v3.py").read_text(encoding="utf-8"))
    consts = {t.id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
              for t in n.targets if isinstance(t, ast.Name) and t.id in ("CHALLENGE_MARKERS", "SIGNIN_MARKERS")}
    assert consts["CHALLENGE_MARKERS"] == P.CHALLENGE_MARKERS and consts["SIGNIN_MARKERS"] == P.SIGNIN_MARKERS


def test_a_page_with_the_beliefs_key_words_verifies_and_is_hashed():
    v = P.verify_outlet(BELIEF, {"outlet": "UNICEF", "url": "https://www.unicef.org/x"},
                        _get({"https://www.unicef.org/x": _ok()}))
    assert v["ok"] and len(v["sha256"]) == 64 and set(v["key_words_found"]) >= {"inclusive", "education", "children"}


@pytest.mark.parametrize("page,why", [
    (_ok(b"<p>Just a moment... checking your browser</p>"), "a wall"),
    (_ok(b"<p>Please sign in to continue reading.</p>"), "a wall"),
    (_ok(status=403), "a wall"),
    (_ok(final="https://www.unicef.org/login?next=x"), "a wall"),
    (_ok(b"<p>Schools reopened after the holidays.</p>"), "key words"),
    (_ok(status=404, body=b"not found"), "HTTP 404"),
])
def test_a_wall_a_missing_page_or_too_few_key_words_never_verifies(page, why):
    v = P.verify_outlet(BELIEF, {"outlet": "X", "url": "https://www.unicef.org/x"}, _get({"https://www.unicef.org/x": page}))
    assert not v["ok"] and why in v["why"]


def test_robots_txt_is_respected():
    robots = {"status": 200, "headers": {}, "body": b"User-agent: *\nDisallow: /", "final_url": "r"}
    v = P.verify_outlet(BELIEF, {"outlet": "X", "url": "https://www.unicef.org/x"},
                        _get({"https://www.unicef.org/robots.txt": robots, "https://www.unicef.org/x": _ok()}))
    assert not v["ok"] and "disallows" in v["why"]


def _premise(c, **extra):
    d = {"belief": {"statement": BELIEF}, "kill_condition": "No held review finds any improved outcome.",
         "public_record_check": {"carried_in_general_coverage": ""}, **extra}
    (c / "premise.json").write_text(json.dumps(d))


def test_only_a_verified_outlet_is_written_and_it_is_the_models_reading(case, monkeypatch):
    _premise(case)
    reply = json.dumps({"outlets": [{"outlet": "Walled", "url": "https://paywall.example/a", "sentence": "s"},
                                    {"outlet": "UNICEF", "url": "https://www.unicef.org/x", "sentence": "s"}]})
    get = _get({"https://www.unicef.org/x": _ok(), "https://paywall.example/a": _ok(status=402)})
    got = P.belief_outlets(case, lambda p, m, r: reply, "claude-sonnet-4-6", get=get)
    d = json.loads((case / "premise.json").read_text())
    assert got["verified"] == 1 and [c["outlet"] for c in d["belief"]["carried_by"]] == ["UNICEF"]
    assert "a model's reading" in d["belief"]["carried_by"][0]["by"]
    assert d["public_record_check"]["carried_in_general_coverage"].startswith("Yes: UNICEF")
    assert len(json.loads((case / P.LOG).read_text().splitlines()[0])["proposed"]) == 3


def test_no_verified_outlet_leaves_the_rows_to_stop_the_page(case):
    _premise(case)
    reply = json.dumps({"outlets": [{"outlet": "X", "url": "https://www.unicef.org/x"}]})
    got = P.belief_outlets(case, lambda p, m, r: reply, "m", get=_get({"https://www.unicef.org/x": _ok(status=403)}))
    d = json.loads((case / "premise.json").read_text())
    assert got["verified"] == 0 and "carried_by" not in d["belief"] and not d["public_record_check"]["carried_in_general_coverage"]


# ----------------------------------------------------------------- B4: direction and kill condition from held text

@pytest.fixture
def held(monkeypatch):
    import ruling as R
    monkeypatch.setattr(R, "held_texts", lambda slug: {"S001": HELD})


def _reading(direction="narrows", kill="survived", quote="Only three studies measured learning outcomes.", sid="S001"):
    q = {"source": sid, "quote": quote}
    return lambda p, m, r: json.dumps({"direction": direction, "direction_quote": q, "direction_why": "w",
                                       "kill_result": kill, "kill_quote": q, "kill_note": "n"})


def test_a_verbatim_quotation_writes_direction_and_the_kill_test(case, held):
    _premise(case)
    got = P.direction_and_kill(case, "whu-x", _reading(), "claude-opus-5-5")
    d = json.loads((case / "premise.json").read_text())
    assert got == {"direction": "narrows", "kill": "survived"}
    assert d["direction"]["value"] == "narrows" and d["direction"]["evidence"]["source"] == "S001"
    assert d["kill_condition_tested"]["result"] == "survived" and d["kill_condition_tested"]["by"]
    a, b = d["direction"]["evidence"]["offsets"]
    assert HELD[a:b] == "Only three studies measured learning outcomes."
    assert "Only three studies" not in (case / "premise.json").read_text()          # offsets and hashes, no text


@pytest.mark.parametrize("kw", [dict(quote="Only three studies measured every outcome that mattered."),
                                dict(sid="S002"), dict(direction="supports"), dict(kill="maybe")])
def test_an_unverified_or_invalid_answer_is_not_written(case, held, kw):
    _premise(case)
    P.direction_and_kill(case, "whu-x", _reading(**kw), "m")
    assert (case / P.LOG).exists()                     # the call was made and recorded; only the answer was refused
    d = json.loads((case / "premise.json").read_text())
    if "direction" in kw or "quote" in kw or "sid" in kw:
        assert "direction" not in d or not d["direction"].get("value")
    if "kill" in kw or "quote" in kw or "sid" in kw:
        assert "kill_condition_tested" not in d


# ----------------------------------------------------------------- the steps

def test_the_new_steps_are_in_order_and_declared():
    names = list(ST.NAMES)
    assert names.index("judgements") < names.index("belief") < names.index("premise_reading") < \
        names.index("corrections_3b")
    assert names.index("changecheck") < names.index("quotations") < names.index("preflight")
    for n in ("belief", "premise_reading", "quotations"):
        assert n in O.STEP_CODE and n in WR.CODE_WRITES
    assert ST.BY_NAME["belief"].models == (ST.GATE_MODEL,) and ST.BY_NAME["premise_reading"].models == (ST.CURRENT,)
    assert ST.BY_NAME["quotations"].models == ()                                    # code only


# ----------------------------------------------------------------- the guard counts this step's calls only

def test_the_previous_steps_calls_in_the_same_second_are_not_this_steps(monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location("spend_ledger_t", ROOT / "backend/scripts/spend_ledger.py")
    S = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(S)
    t = "2026-11-24T15:00:00+00:00"
    rows = [{"issue": "whu-x", "at": t, "step": "judgements", "usd": 0.01, "role": "audit"}] * 2
    monkeypatch.setattr(S, "entries", lambda: list(rows))
    monkeypatch.setattr(S, "orch_lock", lambda: {"token": "tok", "step": "belief"})
    for k, v in {"WHU_ORCH_MODE": "paid", "WHU_ORCH_STEP": "belief", "WHU_ORCH_TOKEN": "tok", "WHU_ORCH_ISSUE": "whu-x",
                 "WHU_ORCH_ALLOW": json.dumps({"models": ["m"]}), "WHU_ORCH_STEP_START": t,
                 "WHU_ORCH_STEP_CALLS": "2", "WHU_ORCH_STEP_CAP": "1"}.items():
        monkeypatch.setenv(k, v)
    S.orch_guard("m", "x", "belief-outlet", "whu-x", 0.01)                         # not refused
    rows[:] = [dict(r, step="belief") for r in rows]
    with pytest.raises(S.OrchestratorRefused, match="has made its 2 calls"):
        S.orch_guard("m", "x", "belief-outlet", "whu-x", 0.01)
