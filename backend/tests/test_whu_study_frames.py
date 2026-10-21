"""The sampling frames' eligibility tests (protocol rev 33, "Question selection").

Offline: the rules frames.py applies to each registry record, on fixed
examples. No registry is called.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("frames_t", ROOT / "study" / "whu-reliability" / "scripts" / "frames.py")
FR = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(FR)


@pytest.mark.parametrize("title, topic", [
    ("Exercise for depression.", "T01"),
    ("Intermittent fasting for adults with overweight or obesity.", "T03"),
    ("Vitamin D supplementation for women during pregnancy.", "T04"),
    ("Ultra-processed food consumption and adverse health outcomes", "T02"),
    ("CDK4/6 inhibitors plus endocrine therapy for advanced breast cancer", "WHU-002"),
    ("Adjuvant therapy for resected melanoma", "WHU-001"),
    ("Generative AI use and critical thinking in university students", "WHU-003"),
])
def test_a_whu_topic_is_excluded(title, topic):
    assert any(k.startswith(topic) for k in FR.topic_exclusion(title))


@pytest.mark.parametrize("title", [
    "Interventions for quitting vaping.",
    "Artificial intelligence for detecting diabetic retinopathy",          # AI, but not AI and cognition
    "Fasting before elective surgery",                                     # not intermittent fasting
    "School-based interventions for reducing disciplinary school exclusion",
])
def test_other_topics_are_not(title):
    assert FR.topic_exclusion(title) == []


def test_protocols_and_maps_are_not_reviews():
    assert FR.PROTOCOL_ABSTRACT.match("This is a protocol for a Cochrane Review (intervention). The objectives")
    for t in ("PROTOCOL: Effects of tutoring", "Determinants of weight gain: A Protocol for a Systematic Review",
              "An evidence and gap map of youth interventions", "Campbell title registrations to date - May 2025"):
        assert FR.NOT_A_REVIEW.search(t), t
    assert not FR.NOT_A_REVIEW.search("Cognitive behavioural therapy for reoffending: a systematic review")


def test_a_certainty_grade_in_an_abstract():
    assert FR.GRADE_TERMS.search("We found low-certainty evidence that it may reduce falls")
    assert FR.GRADE_TERMS.search("the certainty of the evidence was very low")
    assert not FR.GRADE_TERMS.search("Two trials found a reduction in falls (RR 0.8).")


def test_graded_conclusions_in_a_national_academies_summary():
    text = ("There is conclusive evidence that cannabis is effective for chronic pain. There is substantial "
            "evidence of an association with schizophrenia. There is limited evidence of an association with "
            "anxiety.")
    levels = {m.group(1).lower() for m in FR.EVIDENCE_LEVEL.finditer(text)}
    assert levels == {"conclusive", "substantial", "limited"}
    assert not {m.group(1) for m in FR.EVIDENCE_LEVEL.finditer("Strong evidence that the program works.")} - {"Strong"}


def test_ipcc_calibrated_language():
    assert FR.IPCC_CALIBRATED.search("would cause unavoidable increases in multiple climate hazards (very high confidence)")
    assert FR.IPCC_CALIBRATED.search("it is very likely that")
    assert not FR.IPCC_CALIBRATED.search("It is unequivocal that human influence has warmed the atmosphere")
    assert not FR.IPCC_CALIBRATED.search("Low-likelihood outcomes cannot be ruled out")


def test_the_summary_chapter_is_found_by_its_suggested_citation():
    page = b'<p>Suggested Citation: &quot;Summary.&quot; National Academies of Sciences. 2017.</p>'
    assert FR.chapter_name(page) == "summary"
    assert FR.chapter_name(b'Suggested Citation: "Front Matter." National Academies') == "front matter"


def test_a_catalogue_card_gives_id_title_type_and_year():
    card = ('<a data-wrapper-component="x" href="https://www.nationalacademies.org/publications/29401" class="b">'
            '<div><div><p class="f-heading-09 effect-group-focus-visible">\n Human Exploration Across the Moon\n </p>'
            '<div class="f-ui-02 text-secondary gap-spacing-set-1 flex"><p>Consensus Study Report</p>'
            '<span aria-hidden="true">·</span><p>2026</p></div></div></div></a>')
    [(nid, title, meta)] = FR.CARD.findall(card)
    assert nid == "29401" and title.strip() == "Human Exploration Across the Moon"
    assert "Consensus Study Report" in meta and "2026" in meta


def test_the_draw_shuffles_with_the_seed_and_takes_the_first_eligible(tmp_path, monkeypatch):
    import json, random
    frame = tmp_path / "f.json"
    rows = [{"n": i, "id": str(100 + i), "doi": "10.17226/%d" % (100 + i), "title": "T%d" % i, "year": 2020,
             "url": "u"} for i in range(1, 11)]
    frame.write_text(json.dumps({"rows": rows}))
    order = list(range(1, 11))
    random.Random(7).shuffle(order)
    eligible_n = order[3]                                   # the fourth in seeded order
    undetermined_n = order[1]

    def check(F, row, window):
        n = row["n"]
        if n == undetermined_n:
            return {"states_a_certainty_grade": {"pass": False, "undetermined": True, "why": "not fetched"}}
        return {"states_a_certainty_grade": {"pass": n == eligible_n, "why": "x"}}
    monkeypatch.setattr(FR, "check_nasem", check)
    monkeypatch.setattr(FR, "STUDY", tmp_path)
    res = FR.draw(type("F", (), {"log": []})(), frame, 7, FR.PRACTICE_WINDOW)
    assert res["drawn"]["n"] == eligible_n and res["checked"] == 4
    assert [x["n"] for x in res["log"]] == order[:4]                     # every candidate checked is logged
    assert res["log"][1]["undetermined"] == ["states_a_certainty_grade"] and not res["log"][1]["eligible"]
    assert res["shuffled_order_first_50"] == order and res["seed"] == 7


def test_the_summary_pages_a_draw_reads_are_logged(tmp_path):
    import gzip
    F = FR.Fetcher(tmp_path)
    url = "https://www.nationalacademies.org/read/123/chapter/2"
    page = (b'Suggested Citation: "Summary." National Academies. There is sufficient evidence of X. '
            b'There is limited evidence of Y. There is inadequate evidence of Z.')
    (tmp_path / (FR.sha(url)[:32] + ".gz")).write_bytes(gzip.compress(page))   # cached: no network
    s = FR.nap_summary(F, "123")
    assert s["found"] and s["graded"]
    assert [(q["url"], q["kind"], q["status"]) for q in F.log] == [(url, "openbook", 200)]
