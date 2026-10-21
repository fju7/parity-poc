"""The sampling frames' eligibility tests (protocol rev 33 and rev 34, "Question selection").

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
    ("Vitamin D supplementation for preventing falls in older people", "T04"),
    ("Vitamin D for fracture prevention in elderly women living in care homes", "T04"),
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
    "Vitamin D supplementation for women during pregnancy.",             # vitamin D, not older adults (rev 34)
    "Vitamin D for the management of chronic obstructive pulmonary disease.",
    "Older adults and falls: exercise interventions",                     # older adults, not vitamin D
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


def test_health_and_medicine_division_reports_leave_the_list(monkeypatch):
    # protocol rev 34: a report on the HMD unit listing (or one of its boards') is
    # excluded and its units recorded; rev 34 (extended 2026-10-21): so is one on any
    # unit ruled human health or medicine (here CHPP, HCPH), and a report listed under
    # an excluded and a kept unit is excluded. A kept unit (CWSE) is counted; a
    # Health/Medicine unit nobody has ruled on is reported as unclassified.
    listings = {None: {"1": {"title": "A", "type": "Consensus Study Report", "year": 2020},
                       "2": {"title": "B", "type": "Consensus Study Report", "year": 2020},
                       "3": {"title": "C", "type": "Consensus Study Report", "year": 2021},
                       "4": {"title": "D", "type": "Proceedings", "year": 2021},
                       "5": {"title": "E", "type": "Consensus Study Report", "year": 2022},
                       "6": {"title": "F", "type": "Consensus Study Report", "year": 2022}},
                "HMD": {"1": {}}, "FNB": {"2": {}, "4": {}}, "CHPP": {"3": {}}, "HCPH": {"3": {}, "6": {}},
                "CWSE": {"5": {}, "6": {}}}

    def fake(F, y0, y1, query, unit=None):
        query.setdefault("listing", []).append("u%s" % unit)
        query["listing_pages"] = 1
        return listings.get(unit, {})
    filt = [{"code": "CHPP", "name": "Center for Health, People, and Places", "group": "Center for Health, People, and Places"},
            {"code": "HCPH", "name": "Health Care and Public Health Program Area", "group": "Center for Health, People, and Places"},
            {"code": "ESR", "name": "Earth Systems and Resources Program Area", "group": "Center for Health, People, and Places"},
            {"code": "HMD", "name": "Health and Medicine Division", "group": "Health and Medicine Division"},
            {"code": "CWSE", "name": "Committee on Women in Science, Engineering, and Medicine", "group": "PGA"},
            {"code": "XYZ", "name": "Board on Planetary Health", "group": "New"}]
    monkeypatch.setattr(FR, "nap_listing", fake)
    monkeypatch.setattr(FR, "nap_unit_filter", lambda F, y0, y1: filt)
    res = FR.nasem_list(type("F", (), {"log": []})(), "nasem-practice", FR.PRACTICE_WINDOW)
    assert [r["id"] for r in res["rows"]] == ["5"] and res["rows"][0]["n"] == 1
    ex = res["division_exclusion"]
    assert [(e["id"], e["units"]) for e in ex["excluded_reports"]] == [
        ("1", ["HMD"]), ("2", ["FNB"]), ("3", ["CHPP", "HCPH"]), ("6", ["HCPH"])]       # 6 is also under kept CWSE
    assert ex["units"]["CHPP"]["classification"] == "excluded: protocol rev 34 (extended 2026-10-21)"
    assert ex["units"]["HMD"]["classification"] == "excluded: protocol rev 34"
    assert ex["units"]["CWSE"]["classification"] == "kept: protocol rev 34 (extended 2026-10-21)"
    assert ex["unclassified_units"] == ["XYZ"] and ex["units"]["XYZ"]["classification"].startswith("unclassified")
    assert "ESR" not in ex["units"]                                          # no Health/Medicine in its name
    assert ex["units"]["CWSE"]["consensus_reports_listed"] == 2 and ex["units"]["CWSE"]["of_these_left_in_frame"] == 1
    assert res["consensus_reports"] == 5 and res["candidates"] == 1 and res["protocol"] == "rev 34"


def test_the_unit_filter_is_read_with_its_groups():
    page = (b'<div id="filter-unit"><button data-accordion-trigger data-x="1"> <span class="" > Institute of Medicine </span>'
            b'<input type="checkbox" value="IOM" /><span class="peer"></span>'
            b'<span class="f-ui-02 text-primary inline-flex relative"> Institute of Medicine </span>'
            b'<input type="checkbox" value="BMVH" /><span class="f-ui-02 text-primary inline-flex relative"> Board on '
            b'Military and Veterans Health </span></div>')
    F = type("F", (), {"get": lambda self, url, kind="": (200, page)})()
    assert FR.nap_unit_filter(F, 2017, 2023) == [
        {"code": "IOM", "name": "Institute of Medicine", "group": "Institute of Medicine"},
        {"code": "BMVH", "name": "Board on Military and Veterans Health", "group": "Institute of Medicine"}]


def test_spm_statements_are_read_from_paragraph_openings():
    page = (b'<p><span class="bulletnum">B.1</span> <span>Warming has caused losses (<i>high confidence</i>).</span>'
            b'<span>Expand</span><span>Links to chapters</span><span>2.3, 4.2</span></p>'
            b'<p><span>B.1.1</span>Impacts are cascading ( <i>medium confidence</i> ). {WGI AR6 SPM A.1.2, 5.2}</p>'
            b'<p>See WGI AR6 SPM A.3.1 for more.</p>'
            b'<p id="readmore-c7"><span class="bulletnum">C.7.</span><span>Buildings could reach net zero.</span></p>'
            b'<p><span>C.7.2</span>Retrofits lower emissions.</p>')
    st = FR.spm_statements(page)
    assert list(st) == ["B.1", "B.1.1", "C.7", "C.7.2"]
    assert st["B.1"] == "Warming has caused losses ( high confidence )."
    assert st["B.1.1"] == "Impacts are cascading ( medium confidence )."
    assert FR.numbering_gaps(list(st)) == ["C.1", "C.2", "C.3", "C.4", "C.5", "C.6", "C.7.1"]


def test_the_study_draw_plan_drops_the_national_academies():
    # protocol rev 34 (amended 2026-10-21)
    assert FR.STUDY_DRAW_PLAN == {"cochrane": 1, "campbell": 1, "ipcc": 2}
    assert "nasem" in FR.DROPPED_FRAMES and FR.PRACTICE_FRAME == "ipcc-ar5-practice"


def _xml(*texts):
    # (top, left, font, bold, text) -> pdftohtml -xml shape; font 1 = statement, 2 = heading, 3 = body
    out = ['<fontspec id="1" size="14" family="X+Sans" color="#000"/>', '<fontspec id="2" size="18" family="X+Sans" color="#00f"/>',
           '<fontspec id="3" size="14" family="X+Sans" color="#333"/>', '<page number="1" position="absolute">']
    for top, left, font, bold, t in texts:
        out.append('<text top="%d" left="%d" width="%d" height="17" font="%d">%s</text>'
                   % (top, left, 8 * len(t), font, "<b>%s</b>" % t if bold else t))
    return "\n".join(out)


def test_ar5_statements_are_the_bold_statements_labelled_by_section():
    xml = _xml((100, 60, 2, True, "SPM 1.   Observed changes"),
               (130, 60, 1, True, "Human influence on the climate system is clear, and emissions are the"),
               (148, 60, 1, True, "highest in history."),
               (150, 700, 1, True, "{1}"),
               (190, 60, 2, True, "SPM 1.1  Observed changes in the climate system"),
               (220, 60, 1, True, "Emissions have continued to increase over the period with larger increases"),
               (238, 60, 1, True, "towards its end "),
               (238, 188, 3, False, "(high confidence). The rest of the paragraph is elaboration."),
               (256, 60, 3, False, "More plain text that is not part of the statement at all, none of it."),
               (300, 60, 1, True, "Total Emissions by Gas 1970 to 2010 and other figure words"),
               (300, 700, 1, True, "Another column entirely, which is not this paragraph."))
    st = FR.ar5_statements(xml)
    assert [lab for lab, _ in st] == ["1", "1.1"]          # the figure title never ends a sentence
    assert st[0][1] == "Human influence on the climate system is clear, and emissions are the highest in history."
    assert st[1][1] == ("Emissions have continued to increase over the period with larger increases towards its end "
                        "(high confidence).")
    # Known limit: a second-column statement opening on the same line as a first-column run is not read
    # (none of the four AR5 SPMs has one; the frame's per-report counts were checked by reading).
    assert not any("figure words" in s or "Another column" in s for _, s in st)
    assert FR.IPCC_CALIBRATED.search(st[1][1]) and not FR.IPCC_CALIBRATED.search(st[0][1])


def test_a_listed_draw_takes_the_first_eligible_in_seeded_order(tmp_path, monkeypatch):
    import json, random
    rows = [{"n": i, "id": "S%d" % i, "report": "R", "year": 2014, "url": "u", "section": "1", "level": "headline",
             "statement_sha256": "x", "eligible": i % 3 == 0,
             "tests": {"states_a_certainty_grade": {"pass": i % 3 == 0}}} for i in range(1, 13)]
    f = tmp_path / "f.json"
    f.write_text(json.dumps({"rows": rows}))
    monkeypatch.setattr(FR, "STUDY", tmp_path)
    order = list(range(1, 13))
    random.Random(5).shuffle(order)
    first = next(n for n in order if n % 3 == 0)
    res = FR.draw_listed(f, 5)
    assert res["drawn"]["n"] == first and res["checked"] == order.index(first) + 1
    assert all(x["failed"] == ["states_a_certainty_grade"] for x in res["log"][:-1])


def test_a_likelihood_term_counts_only_in_italics():
    # protocol rev 34 (2026-10-21): IPCC sets its calibrated likelihood terms in italics
    xml = ('<fontspec id="1" size="14" family="X+Frutiger-Condensed" color="#000"/>'
           '<fontspec id="2" size="14" family="X+Frutiger-CondensedIta" color="#000"/><page number="1">'
           '<text top="10" left="5" width="9" height="9" font="1">A.1.2 Warming of 2390 GtCO</text>'
           '<text top="10" left="90" width="9" height="9" font="1">2 was emitted (</text>'
           '<text top="10" left="190" width="9" height="9" font="2">likely</text>'
           '<text top="10" left="240" width="9" height="9" font="1"> range) and it is likely to rise, <i>very likely</i> so.</text>')
    chars = FR.pdf_chars(xml)
    chk = FR.italic_likelihood("Warming of 2390 GtCO 2 was emitted ( likely range) and it is likely to rise, very likely so.", chars)
    assert chk["found"] and [(x["term"], x["italic"]) for x in chk["terms"]] == [
        ("likely", True), ("likely", False), ("very likely", True)]
    assert not FR.italic_likelihood("A statement that is not in the document at all, anywhere.", chars)["found"]
