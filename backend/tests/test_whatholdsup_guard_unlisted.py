"""The unlisted preview page and the pre-push guard (advisor ruling, 2026-10-28).

site/whatholdsup/check.html is allowed only while it is unlisted: the noindex,nofollow
robots meta, absent from sitemap.xml, disallowed in robots.txt, and linked from no other
file. Each failing condition makes the guard refuse it as any unclassified page.
Fixtures only: the issue table, the record, the branch listing and the bytes are stubbed."""
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WHU = ROOT / "backend" / "scripts" / "whatholdsup"
sys.path.insert(0, str(WHU))
spec = importlib.util.spec_from_file_location("guard_published_unlisted", WHU / "guard_published.py")
G = importlib.util.module_from_spec(spec)
spec.loader.exec_module(G)

STANDING = ["index.html", "what-this-is.html", "who-pays-for-this.html", "the-rubric.html", "issues.html"]
PAGE = b'<html><head><meta name="robots" content="noindex,nofollow"></head><body>check</body></html>'
SITEMAP = b'<urlset><url><loc>https://whatholdsup.org/</loc></url></urlset>'
ROBOTS = b"User-agent: *\nAllow: /\nDisallow: /check\n"


def files(**over):
    f = {"site/whatholdsup/check.html": PAGE, "site/whatholdsup/sitemap.xml": SITEMAP,
         "site/whatholdsup/robots.txt": ROBOTS}
    for n in STANDING:
        f["site/whatholdsup/" + n] = b'<html><a href="/what-this-is">x</a></html>'
    f.update({k.replace("__", "/").replace("_dot_", "."): v for k, v in over.items()})
    return f


def run(monkeypatch, f):
    monkeypatch.setattr(G, "_issues", lambda: {})
    monkeypatch.setattr(G, "_record", lambda ref: [])
    monkeypatch.setattr(G, "_known_actions", lambda: ("publish", "republish", "update", "announce", "record-deployed"))
    monkeypatch.setattr(G, "_blob", lambda ref, rel: f.get(rel))
    names = [p for p in f if p.startswith("site/whatholdsup/")]
    monkeypatch.setattr(G, "_git", lambda *a: (0, "\n".join(names)))
    blocking, _w = G.check()
    return [b for b in blocking if "check.html" in b]


def test_an_unlisted_check_page_is_allowed(monkeypatch):
    assert run(monkeypatch, files()) == []


def test_refused_without_the_noindex_meta(monkeypatch):
    f = files()
    f["site/whatholdsup/check.html"] = b"<html><head><title>x</title></head></html>"
    b = run(monkeypatch, f)
    assert b and "noindex,nofollow" in b[0]


def test_refused_with_noindex_but_not_nofollow(monkeypatch):
    f = files()
    f["site/whatholdsup/check.html"] = b'<meta name="robots" content="noindex">'
    assert run(monkeypatch, f)


def test_refused_when_in_the_sitemap(monkeypatch):
    f = files()
    f["site/whatholdsup/sitemap.xml"] = SITEMAP.replace(b"</urlset>", b"<url><loc>https://whatholdsup.org/check</loc></url></urlset>")
    b = run(monkeypatch, f)
    assert b and "sitemap.xml lists it" in b[0]


def test_refused_when_robots_does_not_disallow_it(monkeypatch):
    f = files()
    f["site/whatholdsup/robots.txt"] = b"User-agent: *\nAllow: /\n"
    b = run(monkeypatch, f)
    assert b and "robots.txt" in b[0]


def test_refused_when_robots_file_is_missing(monkeypatch):
    f = files()
    del f["site/whatholdsup/robots.txt"]
    assert run(monkeypatch, f)


def test_refused_when_another_page_links_to_it(monkeypatch):
    for href in (b'href="/check"', b'href="/check.html"', b"href='https://whatholdsup.org/check'",
                 b'href="check.html"', b'href="/check?x=1"'):
        f = files()
        f["site/whatholdsup/index.html"] = b"<html><a " + href + b">try it</a></html>"
        b = run(monkeypatch, f)
        assert b and "index.html links to it" in b[0], href


def test_a_link_from_an_email_file_also_refuses(monkeypatch):
    f = files()
    f["site/whatholdsup/email/issue9.html"] = b'<a href="https://whatholdsup.org/check">x</a>'
    b = run(monkeypatch, f)
    assert b and "email/issue9.html links to it" in b[0]


def test_a_similar_name_is_not_a_link(monkeypatch):
    f = files()
    f["site/whatholdsup/index.html"] = b'<a href="/checklist">x</a><a href="/the-rubric#check">y</a>'
    assert run(monkeypatch, f) == []


def test_any_other_unclassified_page_still_blocks(monkeypatch):
    f = files()
    f["site/whatholdsup/draft.html"] = PAGE
    monkeypatch.setattr(G, "_issues", lambda: {})
    blocking = []
    names = [p for p in f if p.startswith("site/whatholdsup/")]
    monkeypatch.setattr(G, "_record", lambda ref: [])
    monkeypatch.setattr(G, "_known_actions", lambda: ("publish",))
    monkeypatch.setattr(G, "_blob", lambda ref, rel: f.get(rel))
    monkeypatch.setattr(G, "_git", lambda *a: (0, "\n".join(names)))
    blocking, _w = G.check()
    assert any("draft.html" in b for b in blocking)
    assert not any("check.html" in b for b in blocking)
