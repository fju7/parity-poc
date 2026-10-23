"""A server that omits its intermediate certificate (WHU-S03, 2026-10-22).

orbilu.uni.lu serves its leaf without GEANT TLS RSA 1, and acquire_sources /
find_access failed on CERTIFICATE_VERIFY_FAILED. tls.urlopen now fetches the
missing intermediate from the leaf's AIA "CA Issuers" URL and verifies the
chain against the trust store plus that certificate, never with verification
off and never with the downloaded certificate as an anchor.

Two kinds of test:
  * the SAVED PAIR (fixtures/tls_aia): orbilu.uni.lu's real leaf and the
    HARICA intermediate its AIA names, both public certificates, saved
    2026-10-22. The AIA is read from them, and the chain is checked offline at
    that date against the trust store with the openssl CLI where it exists.
  * a LOCAL SERVER, end to end, on a test PKI generated per run with the
    openssl CLI (no private key is committed): the server sends its leaf
    alone, the intermediate is served at the leaf's AIA URL. A chain that
    ends at an untrusted root still fails, a downloaded certificate is not an
    anchor, and a hostname mismatch is not excused.
"""
import calendar
import http.server
import shutil
import ssl
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend" / "scripts" / "whatholdsup"))

import tls  # noqa: E402

FIX = Path(__file__).parent / "fixtures" / "tls_aia"
LEAF = FIX / "orbilu.uni.lu.leaf.pem"
INTER = FIX / "HARICA-GEANT-TLS-R1.pem"
SAVED_ON = datetime(2026, 10, 22, 12, tzinfo=timezone.utc)


def _der(p):
    return ssl.PEM_cert_to_DER_cert(p.read_text())


def _openssl():
    for exe in ("/opt/homebrew/bin/openssl", "/usr/local/bin/openssl", shutil.which("openssl")):
        if exe and Path(exe).exists():
            v = subprocess.run([exe, "version"], capture_output=True, text=True).stdout
            if v.startswith("OpenSSL 3"):
                return exe
    return None


# --- the saved pair -------------------------------------------------------------

def test_the_saved_orbilu_leaf_names_the_harica_intermediate():
    assert tls.ca_issuers(_der(LEAF)) == ["http://crt.harica.gr/HARICA-GEANT-TLS-R1.cer"]
    assert tls.ca_issuers(_der(INTER)) == ["http://crt.harica.gr/HARICA-TLS-Root-2021-RSA.cer"]


def test_the_saved_pair_chains_to_the_trust_store_and_the_leaf_alone_does_not():
    exe, cafile = _openssl(), ssl.get_default_verify_paths().cafile
    if not exe or not cafile or not Path(cafile).exists():
        pytest.skip("no OpenSSL 3 CLI or no CA file to verify against")
    at = str(calendar.timegm(SAVED_ON.utctimetuple()))
    both = subprocess.run([exe, "verify", "-attime", at, "-CAfile", cafile, "-untrusted", str(INTER), str(LEAF)],
                          capture_output=True, text=True)
    if "unable to get issuer" in both.stdout + both.stderr:
        pytest.skip("this trust store does not hold HARICA TLS RSA Root CA 2021")
    assert both.returncode == 0, both.stdout + both.stderr
    alone = subprocess.run([exe, "verify", "-attime", at, "-CAfile", cafile, str(LEAF)],
                           capture_output=True, text=True)
    assert alone.returncode != 0 and "unable to get local issuer certificate" in alone.stdout + alone.stderr


def test_a_certificate_with_no_aia_has_no_issuer_urls(pki):
    assert tls.ca_issuers(_der(pki["root"])) == []


# --- a local server that sends its leaf alone -------------------------------------

def _run(exe, *args, cwd):
    subprocess.run([exe, *args], cwd=cwd, check=True, capture_output=True)


def _ca(exe, d, name, signer=None, aia=None, leaf=False):
    _run(exe, "ecparam", "-name", "prime256v1", "-genkey", "-noout", "-out", "%s.key" % name, cwd=d)
    if signer is None:
        _run(exe, "req", "-x509", "-new", "-key", "%s.key" % name, "-out", "%s.pem" % name, "-days", "3650",
             "-subj", "/CN=WHU test %s" % name, "-addext", "basicConstraints=critical,CA:TRUE",
             "-addext", "keyUsage=critical,keyCertSign,cRLSign", cwd=d)
        return d / ("%s.pem" % name)
    ext = (["basicConstraints=critical,CA:FALSE", "keyUsage=critical,digitalSignature",
            "extendedKeyUsage=serverAuth", "subjectAltName=DNS:localhost"] if leaf else
           ["basicConstraints=critical,CA:TRUE,pathlen:0", "keyUsage=critical,keyCertSign,cRLSign"])
    ext += ["subjectKeyIdentifier=hash", "authorityKeyIdentifier=keyid:always"]
    if aia:
        ext.append("authorityInfoAccess=caIssuers;URI:%s" % aia)
    (d / ("%s.ext" % name)).write_text("\n".join(ext) + "\n")
    _run(exe, "req", "-new", "-key", "%s.key" % name, "-out", "%s.csr" % name,
         "-subj", "/CN=%s" % ("localhost" if leaf else "WHU test %s" % name), cwd=d)
    _run(exe, "x509", "-req", "-in", "%s.csr" % name, "-CA", "%s.pem" % signer, "-CAkey", "%s.key" % signer,
         "-CAcreateserial", "-out", "%s.pem" % name, "-days", "3650", "-extfile", "%s.ext" % name, cwd=d)
    return d / ("%s.pem" % name)


class _AIA(http.server.BaseHTTPRequestHandler):
    files, hits = {}, []

    def do_GET(self):
        body = self.files.get(self.path)
        self.hits.append(self.path)
        self.send_response(200 if body is not None else 404)
        self.end_headers()
        self.wfile.write(body or b"")

    def log_message(self, *a):
        pass


class _Page(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"the document")

    def log_message(self, *a):
        pass


def _serve(handler, ctx=None):
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    if ctx:
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture
def pki(tmp_path, monkeypatch):
    exe = _openssl()
    if not exe:
        pytest.skip("no OpenSSL 3 CLI to make a test PKI")
    monkeypatch.setattr(tls, "_FETCHED", {})
    _AIA.files, _AIA.hits = {}, []
    aia = _serve(_AIA)
    base = "http://127.0.0.1:%d" % aia.server_address[1]
    d = tmp_path
    out = {"root": _ca(exe, d, "root"), "dir": d, "base": base}
    out["inter"] = _ca(exe, d, "inter", signer="root", aia=None)
    out["leaf"] = _ca(exe, d, "leaf", signer="inter", aia=base + "/inter.cer", leaf=True)
    _ca(exe, d, "rogue_root")
    out["rogue_inter"] = _ca(exe, d, "rogue_inter", signer="rogue_root")
    out["rogue_leaf"] = _ca(exe, d, "rogue_leaf", signer="rogue_inter", aia=base + "/rogue.cer", leaf=True)
    _AIA.files["/inter.cer"] = _der(out["inter"])
    _AIA.files["/rogue.cer"] = _der(out["rogue_inter"])
    servers = []

    def page(name):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(d / ("%s.pem" % name), d / ("%s.key" % name))      # the leaf ALONE
        s = _serve(_Page, ctx)
        servers.append(s)
        return s.server_address[1]
    out["page"] = page
    yield out
    for s in servers + [aia]:
        s.shutdown()


def test_without_the_intermediate_an_ordinary_request_fails_as_on_orbilu(pki):
    port = pki["page"]("leaf")
    with pytest.raises(urllib.error.URLError) as e:
        urllib.request.urlopen("https://localhost:%d/" % port, timeout=10,
                               context=ssl.create_default_context(cafile=str(pki["root"])))
    assert tls.missing_issuer(e.value)


def test_the_intermediate_is_fetched_from_the_aia_url_and_the_chain_verified(pki):
    port = pki["page"]("leaf")
    with tls.urlopen(urllib.request.Request("https://localhost:%d/" % port), timeout=10,
                     cafile=str(pki["root"])) as r:
        assert r.read() == b"the document"
    assert _AIA.hits == ["/inter.cer"]


def test_a_pem_intermediate_is_accepted(pki):
    _AIA.files["/inter.cer"] = pki["inter"].read_bytes()
    port = pki["page"]("leaf")
    with tls.urlopen("https://localhost:%d/" % port, timeout=10, cafile=str(pki["root"])) as r:
        assert r.read() == b"the document"


def test_a_chain_that_ends_at_an_untrusted_root_still_fails(pki):
    port = pki["page"]("rogue_leaf")
    with pytest.raises(urllib.error.URLError) as e:
        tls.urlopen("https://localhost:%d/" % port, timeout=10, cafile=str(pki["root"]))
    assert isinstance(e.value.reason, ssl.SSLCertVerificationError)
    assert _AIA.hits == ["/rogue.cer"]                     # fetched, and not trusted


def test_the_downloaded_certificate_is_never_an_anchor(pki):
    # Python's default context sets VERIFY_X509_PARTIAL_CHAIN: with it, the
    # rogue intermediate loaded as above WOULD verify the rogue leaf. tls.context
    # clears it, which is the only thing between a forged AIA and a pass.
    port = pki["page"]("rogue_leaf")
    loose = ssl.create_default_context(cafile=str(pki["root"]))
    assert loose.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN
    loose.load_verify_locations(cadata=_der(pki["rogue_inter"]))
    with urllib.request.urlopen("https://localhost:%d/" % port, timeout=10, context=loose) as r:
        assert r.read() == b"the document"                  # the hazard, demonstrated
    strict = tls.context([_der(pki["rogue_inter"])], cafile=str(pki["root"]))
    assert not strict.verify_flags & ssl.VERIFY_X509_PARTIAL_CHAIN
    assert strict.verify_mode == ssl.CERT_REQUIRED and strict.check_hostname


def test_a_hostname_mismatch_is_not_excused(pki):
    port = pki["page"]("leaf")                              # the leaf names localhost only
    with pytest.raises(urllib.error.URLError) as e:
        tls.urlopen("https://127.0.0.1:%d/" % port, timeout=10, cafile=str(pki["root"]))
    assert isinstance(e.value.reason, ssl.SSLCertVerificationError)
    assert "mismatch" in str(e.value.reason) or e.value.reason.verify_code == 62


def test_an_aia_url_that_does_not_return_a_certificate_is_refused(pki):
    _AIA.files["/inter.cer"] = b"<html>not a certificate</html>"
    port = pki["page"]("leaf")
    with pytest.raises(tls.AIAError, match="did not return a certificate"):
        tls.urlopen("https://localhost:%d/" % port, timeout=10, cafile=str(pki["root"]))


def test_other_failures_are_raised_without_an_aia_fetch(pki):
    port = pki["page"]("rogue_root")                        # self-signed: verify code 18, not 20
    with pytest.raises(urllib.error.URLError):
        tls.urlopen("https://localhost:%d/" % port, timeout=10, cafile=str(pki["root"]))
    assert _AIA.hits == []


def test_acquire_sources_and_find_access_fetch_through_tls():
    import acquire_sources
    import find_access
    import inspect
    assert "tls.urlopen(" in inspect.getsource(acquire_sources.fetch)
    assert "tls.urlopen(" in inspect.getsource(find_access.get)
