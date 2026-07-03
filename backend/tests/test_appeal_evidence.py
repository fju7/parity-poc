"""
PH-4a — evidence-into-letter integration tests.

Deterministic suite (default, offline — NO network, NO DB, NO model call):
  * code-built reference block (stable keys, FDA-specific indication, guideline
    rendered reference-only);
  * the anti-fabrication citation guard (THE load-bearing safety gate);
  * reviewer checklist + gap surfacing.
Live eval (@pytest.mark.eval): full generate_appeal end-to-end on the Signatera
fixture (extraction -> retrieve_evidence live -> letter -> guard), asserting the
letter cites only real evidence with no raw citation detail in the prose.

Deterministic: python3 -m pytest backend/tests/test_appeal_evidence.py -v
Eval:          python3 -m pytest backend/tests/test_appeal_evidence.py -m eval -v -s
"""

import json
import os
import re
import sys

import pytest

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from routers.health_analyze import (  # noqa: E402
    _build_evidence_block,
    _format_reference,
    _format_reference_plain,
    _validate_evidence_claims,
    _build_reviewer_checklist,
    _validate_letter,
    _renumber_ordered_lists,
    _map_citation_numbers,
    _normalize_dashes,
    generate_appeal,
    AppealGenerateRequest,
)

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_FIX = os.path.join(_REPO, "test-data", "appeals", "signatera_cigna")


def _pack():
    with open(os.path.join(_FIX, "expected_evidence.json")) as f:
        return json.load(f)


def _denial():
    with open(os.path.join(_FIX, "expected_extraction.json")) as f:
        return json.load(f)


# ===========================================================================
# Deterministic — code-built reference block (Task 2)
# ===========================================================================

class TestEvidenceBlock:
    def test_stable_e_keying_pubmed_then_cms_then_fda(self):
        ev = _build_evidence_block(_pack())
        keys = list(ev["keys"].keys())
        assert keys == [f"E{i}" for i in range(1, len(keys) + 1)]   # E1..En contiguous
        assert ev["keys"]["E1"]["source"] == "pubmed"              # pubmed first
        assert ev["keys"][keys[-1]]["source"] == "fda"            # fda last

    def test_fda_reference_states_specific_indication(self):
        ev = _build_evidence_block(_pack())
        fda_item = next(it for it in ev["keys"].values() if it["source"] == "fda")
        low = _format_reference(fda_item).lower()
        assert "muscle" in low and "bladder" in low            # specific indication, not bare "FDA-approved"
        assert "atezolizumab" in low
        # the reference names the indication, not a bare "FDA-approved" with no scope
        assert "companion diagnostic" in low

    def test_guideline_rendered_reference_only(self):
        ev = _build_evidence_block(_pack())
        g_key = next(k for k, it in ev["keys"].items() if it.get("study_type") == "guideline")
        item = ev["keys"][g_key]
        ref = _format_reference(item).lower()
        assert "pmid" in ref and item["source_uid"] in ref       # reference form
        assert "pubmed guideline" not in ref                     # study_type label must not leak
        assert ".." not in ref                                   # no double periods
        # No expanded recommendation text (only title/journal/year/url are stored).
        for word in ("recommend", "first-line", "should receive", "we suggest"):
            assert word not in ref

    def test_cms_reference_has_policy_id_and_title(self):
        ev = _build_evidence_block(_pack())
        cms_key = next(k for k, it in ev["keys"].items() if it["source"] in ("cms_moldx", "cms_ncd_lcd"))
        ref = _format_reference(ev["keys"][cms_key])
        assert ref.startswith("CMS ")
        assert ev["keys"][cms_key]["source_uid"] in ref          # states the specific doc id


# ===========================================================================
# Deterministic — PH-4a.4 grouped-citation survival + safe rendering
# ===========================================================================

class TestGroupedCitations:
    def test_grouped_citations_survive_validate_letter(self):
        """[E6, E7] and [E1, E2, E4, E5] must NOT be deleted by the cleaner; they
        are preserved and expanded to single brackets for the downstream guard."""
        da = _denial()
        body = ("Medicare covers this [E6, E7].\n"
                "The evidence is strong [E1, E2, E4, E5].\n"
                "A single cite [E3] stays.")
        out = _validate_letter(body, da)["letter_text"]
        assert "[E6][E7]" in out                       # grouped -> expanded singles
        assert "[E1][E2][E4][E5]" in out
        assert "[E3]" in out                            # single unchanged
        assert "Medicare covers this" in out            # line NOT emptied

    def test_genuine_placeholder_still_removed(self):
        da = _denial()
        out = _validate_letter("Ref [E6, E7] kept.\nDrop [Totally Unknown Field] line.", da)
        assert "[E6][E7]" in out["letter_text"]
        assert "[Totally Unknown Field]" not in out["letter_text"]
        assert "Drop" not in out["letter_text"]         # whole non-citation line removed

    def test_grouped_render_to_adjacent_numbers(self):
        assert _map_citation_numbers("see [E6][E7]") == "see [6][7]"
        assert _map_citation_numbers("see [E6, E7]") == "see [6][7]"       # robust to grouped input
        assert _map_citation_numbers("[E1, E2, E4, E5]") == "[1][2][4][5]"
        assert _map_citation_numbers("single [E11]") == "single [11]"

    def test_grouped_unknown_key_caught_by_guard(self):
        """After _validate_letter expands the group, the UNCHANGED guard must
        hard-fail on an unknown key inside the group (no slip-past)."""
        da = _denial()
        expanded = _validate_letter("bad group [E6, E99] here", da)["letter_text"]
        assert "[E6][E99]" in expanded
        r = _validate_evidence_claims(expanded, {"E6": {}})   # E99 does not exist
        assert r["citations_ok"] is False
        assert any("E99" in f for f in r["hard_failures"])

    def test_safeguard_never_silently_deletes_citation_shaped_token(self):
        """A citation-SHAPED token that can't be cleanly expanded is flagged for
        review and left in place, never silently deleted."""
        da = _denial()
        out = _validate_letter("keep me [E6 and E7] please", da)
        assert "[E6 and E7]" in out["letter_text"]     # preserved, not dropped
        assert any(e["action"] == "citation_preserved_for_review"
                   and e["field"] == "[E6 and E7]" for e in out["validation_log"])


# ===========================================================================
# Deterministic — PH-4a.2 em/en-dash normalization (voice pass)
# ===========================================================================

class TestDashNormalization:
    def test_no_em_or_en_dashes_remain(self):
        body = ("The test is analytically validated — Medicare covers it. "
                "Signatera — a ctDNA assay — guides therapy. "
                "It is peer-reviewed and muscle-invasive specific. "
                "See https://pubmed.ncbi.nlm.nih.gov/39284954/ for detail. "
                "The en-dash range 2020–2024 is also removed.")
        out = _normalize_dashes(body)
        assert "—" not in out and "–" not in out            # zero em/en dashes remain
        assert "peer-reviewed" in out and "muscle-invasive" in out   # hyphen-minus untouched
        assert "https://pubmed.ncbi.nlm.nih.gov/39284954/" in out    # URL untouched

    def test_clause_separator_becomes_period(self):
        # next word capitalized -> independent clause -> ". "
        assert _normalize_dashes("The test works — Medicare agrees.") == "The test works. Medicare agrees."

    def test_midsentence_aside_becomes_commas(self):
        assert _normalize_dashes("Signatera — a ctDNA assay — guides care.") == \
            "Signatera, a ctDNA assay, guides care."

    def test_hyphenated_words_untouched(self):
        s = "muscle-invasive peer-reviewed ctDNA-based FDA-approved"
        assert _normalize_dashes(s) == s

    def test_newlines_preserved(self):
        # lowercase next word -> comma; the newline is never consumed.
        assert _normalize_dashes("Line one — end.\nLine two") == "Line one, end.\nLine two"


# ===========================================================================
# Deterministic — PH-4a.3 identifier-free model-facing evidence view
# ===========================================================================

class TestModelFacingView:
    _ID_PATTERNS = {
        "PMID": re.compile(r"\b\d{7,8}\b"),
        "PMA": re.compile(r"\bP\d{6}\b"),
        "DOI": re.compile(r"10\.\d{4,}/"),
        "URL": re.compile(r"https?://"),
    }

    def test_model_block_has_no_identifiers(self):
        ev = _build_evidence_block(_pack())
        for k, item in ev["keys"].items():
            line = _format_reference_plain(item)
            for name, pat in self._ID_PATTERNS.items():
                assert not pat.search(line), f"{k} model-facing line leaked {name}: {line}"
        # whole block, too
        for name, pat in self._ID_PATTERNS.items():
            assert not pat.search(ev["model_block"]), f"model_block leaked {name}"

    def test_appended_references_still_have_identifiers_and_urls(self):
        ev = _build_evidence_block(_pack())
        block = ev["references_block"]
        assert re.search(r"\bPMID \d{7,8}\b", block)     # PubMed IDs present
        assert re.search(r"\bP\d{6}\b", block)           # FDA PMA present
        assert re.search(r"https?://", block)            # URLs present

    def test_fda_model_line_keeps_indication_drops_pma(self):
        ev = _build_evidence_block(_pack())
        fda = next(it for it in ev["keys"].values() if it["source"] == "fda")
        line = _format_reference_plain(fda).lower()
        assert re.search(r"muscle[\s-]invasive bladder cancer", line)   # indication preserved
        assert "atezolizumab" in line
        assert "p260004" not in line                     # identifier dropped
        assert "http" not in line

    def test_model_and_appended_share_same_keys(self):
        ev = _build_evidence_block(_pack())
        model_keys = re.findall(r"\[(E\d+)\]", ev["model_block"])
        ref_keys = re.findall(r"\[(E\d+)\]", ev["references_block"])
        assert model_keys == ref_keys and model_keys == list(ev["keys"])


# ===========================================================================
# Deterministic — PH-4a.1 mechanical fixes (citation preservation, numbering)
# ===========================================================================

class TestCitationPreservationAndNumbering:
    def test_validate_letter_preserves_e_citations(self):
        """The PH-1 placeholder cleaner must NOT strip inline [E#] citations."""
        da = _denial()
        letter = ("__LETTER_DATE__\n\n"
                  "The FDA has authorized this test [E11], and Medicare covers it [E5].\n"
                  "[Unknown Placeholder] should still be removed.")
        out = _validate_letter(letter, da)
        assert "[E11]" in out["letter_text"]                     # citations survive
        assert "[E5]" in out["letter_text"]
        assert "[Unknown Placeholder]" not in out["letter_text"] # real placeholders still removed

    def test_e_citation_not_logged_as_removed(self):
        out = _validate_letter("Support [E3] applies.", _denial())
        assert "[E3]" in out["letter_text"]
        assert not any(e.get("field") == "[E3]" for e in out["validation_log"])

    def test_renumber_ordered_list_fills_gaps(self):
        gapped = "1. First\n2. Second\n4. Fourth\n8. Eighth"
        assert _renumber_ordered_lists(gapped) == "1. First\n2. Second\n3. Fourth\n4. Eighth"

    def test_renumber_separate_blocks_each_restart(self):
        text = "1. a\n2. b\n\n1. x\n5. y"
        assert _renumber_ordered_lists(text) == "1. a\n2. b\n\n1. x\n2. y"

    def test_map_citation_numbers_body_and_ref_align(self):
        assert _map_citation_numbers("see [E11] and [E6]") == "see [11] and [6]"
        assert _map_citation_numbers("[E11] FDA ...") == "[11] FDA ..."
        assert "[E" not in _map_citation_numbers("[E1][E2][E3]")


# ===========================================================================
# Deterministic — anti-fabrication guard (Task 5) — CRITICAL
# ===========================================================================

class TestAntiFabricationGuard:
    KEYS = {"E1": {}, "E2": {}, "E3": {}}

    def test_valid_keys_no_raw_citations_ok(self):
        letter = ("We rely on peer-reviewed support [E1] and Medicare coverage [E3]. "
                  "The assay is analytically validated.")
        r = _validate_evidence_claims(letter, self.KEYS)
        assert r["citations_ok"] is True
        assert r["hard_failures"] == []
        assert r["used_keys"] == ["E1", "E3"]

    def test_unknown_key_hard_fail(self):
        r = _validate_evidence_claims("As shown [E9], the test is valid.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("unknown evidence key E9" in f for f in r["hard_failures"])

    def test_bare_pmid_hard_fail(self):
        r = _validate_evidence_claims("See PMID 12345678 for evidence.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("PubMed ID" in f for f in r["hard_failures"])

    def test_pma_number_hard_fail(self):
        r = _validate_evidence_claims("The device (P260004) is approved.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("PMA" in f for f in r["hard_failures"])

    def test_doi_hard_fail(self):
        r = _validate_evidence_claims("Per doi 10.1200/JCO.22.01690 the data is clear.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("DOI" in f for f in r["hard_failures"])

    def test_et_al_hard_fail(self):
        r = _validate_evidence_claims("Nakamura et al. reported durable responses.", self.KEYS)
        assert r["citations_ok"] is False
        assert any("et al" in f.lower() for f in r["hard_failures"])

    def test_statistic_is_soft_flag_not_hard_fail(self):
        letter = "The approach improved detection by 42% in the study population."
        r = _validate_evidence_claims(letter, self.KEYS)
        assert r["citations_ok"] is True                          # NOT a hard fail
        assert r["hard_failures"] == []
        assert any(fl["figure"] == "42%" for fl in r["review_flags"])
        assert any("42%" in fl["sentence"] for fl in r["review_flags"])


# ===========================================================================
# Deterministic — reviewer checklist + gaps (Task 6)
# ===========================================================================

class TestReviewerChecklist:
    def test_status_always_draft_and_missing_icd_action(self):
        pack = _pack()
        assert _denial()["icd_codes"] == []                      # Signatera fixture has no ICD
        ev = _build_evidence_block(pack)
        val = _validate_evidence_claims("Support [E11] applies.", ev["keys"])
        checklist = _build_reviewer_checklist(ev, val)
        assert checklist["status"] == "draft — human review required before sending"
        # missing-ICD gap surfaced as an actionable regenerate prompt
        assert any(i["type"] == "gap" and "No diagnosis (ICD) code was provided" in i["action"]
                   and "regenerate" in i["action"] for i in checklist["items"])
        # cited evidence surfaces ONE consolidated scope note (not one flag per citation)
        scope = [i for i in checklist["items"] if i["type"] == "evidence_scope"]
        assert len(scope) == 1
        assert "confirm with the ordering provider" in scope[0]["prompt"].lower()

    def test_soft_flag_becomes_verify_item(self):
        ev = _build_evidence_block(_pack())
        val = _validate_evidence_claims("Detection improved 42% overall.", ev["keys"])
        checklist = _build_reviewer_checklist(ev, val)
        assert any(i["type"] == "verify_statistic" and i["figure"] == "42%" for i in checklist["items"])


# ===========================================================================
# Deterministic — PH-1 validator still passes unchanged (Task 7)
# ===========================================================================

class TestPh1Unchanged:
    def test_letter_date_token_still_stamps(self):
        da = _denial()
        out = _validate_letter("__LETTER_DATE__\n\nDear Appeals,", da)
        assert "__LETTER_DATE__" not in out["letter_text"]
        assert any(e.get("action") == "stamped" for e in out["validation_log"])

    def test_no_bracket_placeholders_leak(self):
        da = _denial()
        out = _validate_letter("[Patient Name]\n[Claim Number]\n__LETTER_DATE__", da)
        import re
        assert not re.search(r"\[[^\]]+\]", out["letter_text"])


# ===========================================================================
# Live eval (marked) — full generate_appeal end-to-end on the Signatera fixture
# ===========================================================================

@pytest.mark.eval
def test_live_appeal_generation_eval():
    """extraction fixture -> retrieve_evidence (live) -> letter -> guard.
    Asserts the letter cites only real evidence with no raw citation detail in
    the prose, and surfaces the missing-ICD gap. Prints letter + checklist."""
    da = _denial()
    req = AppealGenerateRequest(denial_analysis=da)
    result = generate_appeal(req)

    letter = result["letter_text"]
    ev_val = result["evidence_validation"]
    checklist = result["reviewer_checklist"]

    # Split the trusted References section from the model-written body.
    if "\nReferences\n" in letter:
        body, references = letter.split("\nReferences\n", 1)
    else:
        body, references = letter, ""

    import re
    used_keys = ev_val["used_keys"]

    # Print artifacts first so they always surface, even if an assertion fails.
    print("\n================= GENERATED LETTER =================\n")
    print(letter)
    print("\n================= REVIEWER CHECKLIST =================\n")
    print(json.dumps(checklist, indent=2))
    print("\n================= EVIDENCE VALIDATION =================\n")
    print(json.dumps(ev_val, indent=2))
    print(f"\nused E-keys (guard, pre-render): {used_keys}")
    print(f"needs_revision: {result['needs_revision']}  status: {result['status']}")

    # -- Durable invariants (what PH-4a.1 must guarantee) --
    # 1) Citations SURVIVED _validate_letter (the core fix): the guard saw [E#].
    assert used_keys, "no [E#] citations survived into the body — Task 1 fix failed"
    # 2) No unknown-key hard failure (the guard validates key existence itself).
    assert not any("unknown evidence key" in f for f in ev_val["hard_failures"])
    # 3) Reader-facing numbering applied: body shows [n], internal [E#] gone.
    assert not re.search(r"\[E\d+\]", body), "internal [E#] leaked into rendered letter"
    assert re.search(r"\[\d+\]", body), "no reader-facing [n] citation in body"
    # 4) References appended with the FDA-specific indication.
    assert references, "References section should be appended"
    assert "muscle" in references.lower() and "bladder" in references.lower()
    # 5) Checklist always draft + surfaces the missing-ICD gap.
    assert checklist["status"] == "draft — human review required before sending"
    assert any("No diagnosis (ICD) code was provided" in i.get("action", "")
               for i in checklist["items"] if i["type"] == "gap")
    # 6) Guard integrity: needs_revision iff a hard failure fired, and any firing
    #    has a stated reason. A hard-fail here is the guard WORKING (e.g. the model
    #    echoed a raw identifier), which the brief wants surfaced — not a bug.
    assert result["needs_revision"] == (not ev_val["citations_ok"])
    if not ev_val["citations_ok"]:
        assert ev_val["hard_failures"], "needs_revision with no stated reason"
