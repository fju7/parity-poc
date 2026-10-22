"""Audit trimming delivers every bound passage (2026-10-21, WHU-P04).

trim() merged every window into runs and, when a run was longer than
MAX_DOC_CHARS, cut it around a single centre. On WHU-P04, S005's bound passages
at about 21,541 and 106,180 characters fell in one such run; two of the batch's
three spans were cut away and the run stopped with DOCUMENT_NOT_DELIVERED. Now
each bound passage has its own window, joined in document order with a visible
marker; and a batch whose passages cannot all fit with minimal context is split
and each part audited. The delivery check is unchanged. No model is called.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

WHU = Path(__file__).resolve().parents[1] / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("audit_stage_trim_t", WHU / "audit_stage.py")
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
spec = importlib.util.spec_from_file_location("audit_test_fixtures_trim_t",
                                              Path(__file__).parent / "test_whatholdsup_audit_stage.py")
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

FILL = "Emissions were reported in the national inventory for each sector and year. "


def _text(n, spans_at):
    """N characters of filler with each (position, span) planted."""
    out, pos = [], 0
    for at, span in sorted(spans_at):
        k = (at - pos) // len(FILL) + 1
        out.append(FILL * k)
        pos += len(FILL) * k
        out.append(span + " ")
        pos += len(span) + 1
    out.append(FILL * ((n - pos) // len(FILL) + 1))
    return "".join(out)[:n]


P1 = "Global emissions grew 2.2 percent per year between 2000 and 2010."
P2 = "Growth was 1.3 percent per year over the three decades before."
P3 = "Cement and metals contributed a rising share of the increase."


def test_passages_far_apart_with_terms_everywhere_are_all_delivered():
    text = _text(430_000, [(21_541, P1), (106_180, P2), (300_000, P3)])
    out, cut = A.trim(text, ["emissions", "inventory", "sector"], [P1, P2, P3])
    assert cut and len(out) <= A.MAX_DOC_CHARS
    assert all(p in out for p in (P1, P2, P3))
    assert out.count(A.DOC_SEP) >= 2 and "[… text omitted …]" in A.DOC_SEP
    assert out.index(P1) < out.index(P2) < out.index(P3)            # document order


def test_the_remaining_space_is_shared_as_context_around_each_passage():
    text = _text(430_000, [(21_541, P1), (106_180, P2)])
    out, _ = A.trim(text, [], [P1, P2])
    i = text.index(P1)
    assert text[i - A.MAX_CONTEXT:i + len(P1) + A.MAX_CONTEXT] in out   # full context, both sides


def test_term_windows_go_in_only_after_the_passages():
    text = _text(430_000, [(21_541, P1), (106_180, P2), (380_000, "a rare tracer word")])
    out, _ = A.trim(text, ["tracer"], [P1, P2])
    assert P1 in out and P2 in out and "tracer" in out


def test_a_batch_whose_passages_cannot_fit_is_split_and_every_part_is_delivered(tmp_path, monkeypatch):
    monkeypatch.setattr(A, "MAX_DOC_CHARS", 12_000)
    spans = ["Planted bound passage number %d says the value was %d units." % (i, 10 + i) for i in range(8)]
    text = _text(200_000, [(5_000 + i * 24_000, s) for i, s in enumerate(spans)])
    held = {"demo:S021": text}
    batch = [T._unit("u%d" % (i + 1), "Sentence %d about the value." % i, span=s) for i, s in enumerate(spans)]
    assert not A.batch_fits("demo", batch, held)
    splits = []
    parts = A.fit_batches("demo", [batch], held, splits=splits)
    assert len(parts) > 1 and splits and sum(len(p) for p in parts) == len(batch)
    assert [u["id"] for p in parts for u in p] == [u["id"] for u in batch]
    for p in parts:
        docs, _ = A.batch_inputs("demo", p, held)
        A.check_delivery(A.delivery_report("demo", p, held, docs))     # unchanged check; raises if not
    m = A.run("demo", out_dir=tmp_path, ask=T.FakeModel(always_finding=False), held=held,
              unit_list=batch, cap=1.0, licensed=set())
    assert m["status"] == "complete", m.get("failure")
    assert m["splits"] and all(d["spans_inside"] for d in m["deliveries"])


def test_short_documents_pass_through_unchanged():
    assert A.trim(T.DOC, ["adenoma"], ["226 detected an adenoma (28.4%)"]) == (T.DOC, False)
    held = {"demo:S021": T.DOC}
    batch = [T._unit("u1", "The study found 226 of 795 detected an adenoma (28.4%).")]
    assert A.batch_inputs("demo", batch, held)[0] == {"S021": T.DOC}
    assert A.fit_batches("demo", [batch], held) == [batch]


def test_whu_p04_s005_all_three_bound_passages_are_delivered():
    """The real case, only where WHU-P04's private files are (bindings and the
    held S005 text; neither is committed). Nothing from either is asserted on
    or printed beyond counts and offsets."""
    slug = "greenhouse-gas-emissions-growth"
    case = WHU.parents[2] / "issues" / "WHU-P04-greenhouse-gas-emissions-growth"
    if not (case / "bindings.json").exists():
        pytest.skip("WHU-P04's bindings are not here")
    held = A.held_for_audit(slug)
    if "S005" not in held:
        pytest.skip("WHU-P04's S005 is not held here")
    want = {"u1", "u9", "u10", "u11", "u17", "u19", "u22", "u24", "u25", "u26"}
    batch = [u for u in A.units(slug) if u["id"] in want]
    text, must = A.doc_passages(slug, batch, held)["S005"]
    assert len(must) == 3
    at = [a for a, _b in A.passages(text, must)]
    assert any(abs(a - 21_541) < 500 for a in at) and any(abs(a - 106_180) < 1_000 for a in at)
    docs, _ = A.batch_inputs(slug, batch, held)
    rep = {r["source"]: r for r in A.delivery_report(slug, batch, held, docs)}
    assert rep["S005"]["bound_spans"] == 3 and rep["S005"]["spans_inside"], rep["S005"]["missing_spans"]
    A.check_delivery(list(rep.values()))
