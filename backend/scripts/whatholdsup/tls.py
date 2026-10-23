#!/usr/bin/env python3
"""HTTPS from a server that omits an intermediate certificate (2026-10-22).

WHU-S03: orbilu.uni.lu serves its leaf certificate without the intermediate
that issued it (GEANT TLS RSA 1), so acquire_sources and find_access failed on
SSL CERTIFICATE_VERIFY_FAILED, "unable to get local issuer certificate". A
browser fills the gap from the leaf's Authority Information Access extension;
urllib does not.

urlopen() here does what the browser does, and nothing looser:

  * the first attempt is an ordinary verified request;
  * only on that one failure (verify code 20, the issuer is not held) does it
    read the server's leaf certificate, take the "CA Issuers" URL from its AIA
    extension, and download the certificate there (DER or PEM; at most
    MAX_DEPTH of them, following each one's own AIA);
  * it then asks again on a fresh connection, verifying against the system
    trust store PLUS those certificates, with hostname checking on and
    VERIFY_X509_PARTIAL_CHAIN cleared. Python 3.13+ sets that flag by default,
    and with it a downloaded certificate could act as a trust anchor by
    itself; cleared, the chain must still end at a root in the system store.

Verification is never disabled for the request. The leaf is read with
ssl.get_server_certificate, which does not verify, because the point is to read
a certificate that cannot yet be verified; nothing from that connection is used
except the URL it names, and whatever is downloaded from that URL is trusted
only if it chains to a system root. Any other certificate failure (expired,
wrong host, self-signed, untrusted root) is raised unchanged.

A redirect to another host that omits its intermediate is not handled: the AIA
is read from the URL first asked for, the retry fails, and the error is raised.
"""
from __future__ import annotations

import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

MISSING_ISSUER = 20              # X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY
MAX_DEPTH = 3
MAX_CERT_BYTES = 64_000
AIA_OID = bytes.fromhex("2b06010505070101")         # 1.3.6.1.5.5.7.1.1 authorityInfoAccess
CA_ISSUERS_OID = bytes.fromhex("2b06010505073002")  # 1.3.6.1.5.5.7.48.2 caIssuers
_FETCHED: dict[str, bytes] = {}                      # AIA URL -> DER, per process


class AIAError(Exception):
    pass


# --- reading the AIA extension (DER, no third-party parser) ---------------------

def _tlv(b: bytes, i: int) -> tuple[int, int, int]:
    """(tag, start of value, end of value) of the DER element at i."""
    if i + 2 > len(b):
        raise AIAError("truncated DER")
    tag, n, i = b[i], b[i + 1], i + 2
    if n & 0x80:
        k = n & 0x7F
        if not 0 < k <= 4 or i + k > len(b):
            raise AIAError("bad DER length")
        n, i = int.from_bytes(b[i:i + k], "big"), i + k
    if i + n > len(b):
        raise AIAError("DER element runs past the end")
    return tag, i, i + n


def _children(b: bytes, start: int, end: int):
    i = start
    while i < end:
        tag, s, e = _tlv(b, i)
        yield tag, s, e
        i = e


def ca_issuers(der: bytes) -> list[str]:
    """The CA Issuers URLs in a DER certificate's AIA extension, in order."""
    _t, cs, ce = _tlv(der, 0)                                   # Certificate
    tbs = next(_children(der, cs, ce))                          # tbsCertificate
    ext = [c for c in _children(der, tbs[1], tbs[2]) if c[0] == 0xA3]
    if not ext:
        return []
    _t, ls, le = next(_children(der, ext[0][1], ext[0][2]))     # SEQUENCE OF Extension
    out = []
    for _t, s, e in _children(der, ls, le):
        parts = list(_children(der, s, e))
        if not parts or der[parts[0][1]:parts[0][2]] != AIA_OID:
            continue
        _t, os_, oe = parts[-1]                                 # extnValue OCTET STRING
        _t, ss, se = _tlv(der, os_)                             # AuthorityInfoAccessSyntax
        for _t, ds, de in _children(der, ss, se):               # AccessDescription
            (_t1, ms, me), (gtag, gs, ge) = list(_children(der, ds, de))[:2]
            if der[ms:me] == CA_ISSUERS_OID and gtag == 0x86:   # [6] uniformResourceIdentifier
                out.append(der[gs:ge].decode("ascii", "replace"))
    return out


# --- the request -------------------------------------------------------------------

def context(extra_der=(), cafile: str | None = None) -> ssl.SSLContext:
    """A verifying context: the system trust store (or CAFILE, for tests), plus
    EXTRA_DER as certificates to build the chain from, never as anchors."""
    ctx = ssl.create_default_context(cafile=cafile)
    ctx.verify_flags &= ~ssl.VERIFY_X509_PARTIAL_CHAIN
    for der in extra_der:
        ctx.load_verify_locations(cadata=der)
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname
    return ctx


def missing_issuer(exc: BaseException) -> bool:
    e = getattr(exc, "reason", exc)
    return isinstance(e, ssl.SSLCertVerificationError) and getattr(e, "verify_code", None) == MISSING_ISSUER


def server_leaf(host: str, port: int, timeout: float) -> bytes:
    return ssl.PEM_cert_to_DER_cert(ssl.get_server_certificate((host, port), timeout=timeout))


def fetch_issuer(url: str, timeout: float) -> bytes:
    """The certificate at an AIA URL, as DER (DER or PEM accepted)."""
    if url in _FETCHED:
        return _FETCHED[url]
    if urllib.parse.urlsplit(url).scheme not in ("http", "https"):
        raise AIAError("CA Issuers URL is not http(s): %s" % url)
    with urllib.request.urlopen(url, timeout=timeout) as r:
        data = r.read(MAX_CERT_BYTES + 1)
    if len(data) > MAX_CERT_BYTES:
        raise AIAError("CA Issuers URL returned more than %d bytes: %s" % (MAX_CERT_BYTES, url))
    if data.lstrip().startswith(b"-----BEGIN CERTIFICATE-----"):
        data = ssl.PEM_cert_to_DER_cert(data.decode("ascii"))
    elif not data.startswith(b"\x30"):
        raise AIAError("CA Issuers URL did not return a certificate (DER or PEM): %s" % url)
    _FETCHED[url] = data
    return data


def urlopen(req, timeout: float = 30, cafile: str | None = None):
    """urllib.request.urlopen, verified, completing a chain the server left
    short from the AIA CA Issuers URLs. See the module docstring."""
    try:
        return urllib.request.urlopen(req, timeout=timeout, context=context(cafile=cafile))
    except (urllib.error.URLError, ssl.SSLCertVerificationError) as first:
        if not missing_issuer(first):
            raise
        err = first
    url = req.full_url if isinstance(req, urllib.request.Request) else req
    u = urllib.parse.urlsplit(url)
    if u.scheme != "https" or not u.hostname:
        raise err
    cert, extra = server_leaf(u.hostname, u.port or 443, timeout), []
    for _ in range(MAX_DEPTH):
        urls = ca_issuers(cert)
        if not urls:
            raise err
        cert = fetch_issuer(urls[0], timeout)
        extra.append(cert)
        try:
            r = urllib.request.urlopen(req, timeout=timeout, context=context(extra, cafile=cafile))
        except (urllib.error.URLError, ssl.SSLCertVerificationError) as again:
            if not missing_issuer(again):
                raise
            err = again
            continue
        print("  [tls] %s omitted %d intermediate certificate(s); fetched from %s and verified "
              "against the trust store" % (u.hostname, len(extra), urls[0]), file=sys.stderr)
        return r
    raise err
