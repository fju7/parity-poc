"""Fix 2, step 10: the runbook, and the frozen study files untouched (post-study, 2026-10-27)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))


def test_the_frozen_study_files_are_unchanged():
    import frozen
    assert frozen.mismatches() == []


def test_the_process_doc_carries_the_post_study_steps():
    doc = (ROOT / "docs" / "whatholdsup-process.md").read_text(encoding="utf-8")
    sec = doc[doc.index("## 4.5 Protected sentences, omitted findings and coverage"):doc.index("## 5. The machine gate")]
    for want in ("coverage_check.py <slug>", "ruling.py omissions <slug>", "\"origin\": \"omission_add\"",
                 "Findings in our sources we judged outside this question", "Known limit",
                 "protected sentences kept", "omission objections ruled", "headline conclusions accounted for",
                 "declared findings shown to readers", "RUN.md` is frozen"):
        assert want in sec, want


def test_the_runbook_commands_exist():
    import coverage_check as C
    import ruling as R
    import omissions as O
    assert "omissions" in R.MODE_KIND and callable(R.rule_omissions)
    assert callable(C.main) and C.HEADING in (ROOT / "docs" / "whatholdsup-process.md").read_text(encoding="utf-8")
    assert O.ROW == "omission objections ruled"
