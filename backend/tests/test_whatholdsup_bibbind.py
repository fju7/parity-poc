"""Title and author lines in a source list, bound to the entry's held text.

Fixtures only: the page and the store are monkeypatched; nothing reads an issue
directory."""
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("bibbind", WHU / "bibbind.py")
BB = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BB)

HELD = {
    "S001": ("Influence of AI Decision Support on Radiologists' Performance and Visual Search in Screening "
             "Mammography Jessie J. J. Gommers, MSc*1 • Sarah D. Verboom, MSc*1 • Katya M. Duvivier, MD2 "
             "Abstract ... References 4. Gommers JJJ, Smith A."),
    "S002": "Miloš Stanković1,2,*, Ella Hirche2,+, Sarah Kollatzsch2,+, Julia Nadine Doetsch2 Comment on it.",
    "S003": "Learning and deskilling effects Pedersen Tom Andre MD Mori Yuichi Prof. Botteri Edoardo Dr. Methods",
    "S004": "the accepted manuscript title, Endoscopist de-skilling after exposure",
    "S005": "Correction to: Endoscopist deskilling risk after exposure to artificial intelligence in colonoscopy.",
    "S006": "J. Weidlich1,2 | D. Gašević3 | H. Drachsler4 | P. Kirschner6,7 ... References Kirschner, P. A. 2020.",
}
SRCS = [{"id": "S001"}, {"id": "S002"}, {"id": "S003"}, {"id": "S004"}, {"id": "S005", "amends": "S004"}, {"id": "S006"}]


@pytest.fixture(autouse=True)
def store(monkeypatch):
    monkeypatch.setattr(BB.store, "sources", lambda slug: SRCS)
    monkeypatch.setattr(BB.SC, "_texts", lambda slug, sid: [("f", HELD[sid])] if sid in HELD else [])


def line(kind, body, sid):
    return {"kind": kind, "sentence": body, "body": body, "sources": [sid]}


def test_title_verbatim_binds():
    r = BB.bind_title(line("title", "Influence of AI Decision Support on Radiologists’ Performance and Visual "
                           "Search in Screening Mammography.", "S001"), "t")
    assert r["ok"] and r["span"].startswith("Influence of AI") and r["source_id"] == "S001"


def test_title_with_different_case_does_not_bind():
    r = BB.bind_title(line("title", "Influence of AI decision support on radiologists’ performance.", "S001"), "t")
    assert not r["ok"]


def test_title_found_in_the_amending_corrigendum():
    r = BB.bind_title(line("title", "Endoscopist deskilling risk after exposure to artificial intelligence "
                           "in colonoscopy.", "S004"), "t")
    assert r["ok"] and r["source_id"] == "S005"


def test_author_line_with_initials_and_et_al_binds_on_the_byline():
    r = BB.bind_authors(line("author", "Gommers JJJ, Verboom SD, Duvivier KM, et al.", "S001"), "t")
    assert r["ok"] and r["span"].startswith("Jessie J. J. Gommers") and "Duvivier" in r["span"]


def test_wrong_initials_do_not_bind():
    r = BB.bind_authors(line("author", "Gommers JJJ, Verboom SX, et al.", "S001"), "t")
    assert not r["ok"] and "Verboom SX" in r["why"]


def test_an_initial_the_byline_does_not_print_does_not_bind():
    r = BB.bind_authors(line("author", "Weidlich J, Gašević D, Drachsler H, Kirschner PA.", "S006"), "t")
    assert not r["ok"]


def test_diacritics_and_superscripts():
    r = BB.bind_authors(line("author", "Stankovic M, Hirche E, Kollatzsch S, Doetsch JN.", "S002"), "t")
    assert r["ok"] and "matched ignoring accents" in r["why"]


def test_surname_first_bylines():
    r = BB.bind_authors(line("author", "Pedersen TA, Mori Y, Botteri E.", "S003"), "t")
    assert r["ok"] and r["span"].startswith("Pedersen Tom Andre")


def test_parse_authors():
    assert BB.parse_authors("Wang DY, Ding J, Sun AL, et al.") == [("Wang", "DY"), ("Ding", "J"), ("Sun", "AL")]
    assert BB.parse_authors("Liu, Christian, Dumbalska, Bakker & Dubey.") == [
        ("Liu", ""), ("Christian", ""), ("Dumbalska", ""), ("Bakker", ""), ("Dubey", "")]
