#!/usr/bin/env python3
"""The files frozen for the WHU reliability study, pinned by sha256
(protocol rev 38).

Code refuses to run on a frozen file whose sha256 is not the one recorded
here, as judge_m1.py and judge_m2.py refuse a changed judge prompt and
blind.py a changed spelling map or blinding list:

  * the ruling and audit prompts are checked whenever they are read
    (ruling.build_prompt; audit_stage's reader, summary and ruling prompts),
    for every issue: they are WHU's prompts, not the study's alone;
  * RUN.md, the study's run procedure, is checked with all of them before any
    paid stage of a study issue starts (stage_cap.guard) and by the study
    preflight.

A changed file is not "updated" by changing a hash here during the study:
that is a deviation, logged as the protocol says. `py frozen.py` prints the
state of every pin.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

FROZEN_SHA256 = {
    "backend/scripts/whatholdsup/audit_prompts/rule.md":
        "388a27cee450b3cd27c5dfc394cb63f39bfda40016ac6df96c67d1958d57ac11",
    "backend/scripts/whatholdsup/audit_prompts/rule_cite.md":
        "ecd312671f41d473071aa6a3202149af188e33460f1e496c7123c59073b1e8d4",
    "backend/scripts/whatholdsup/audit_prompts/rule_group.md":
        "68a0fd068ff518820dfbaeab58eeba4a571fa7928e231b80dbf0112c01d39a62",
    "backend/scripts/whatholdsup/audit_prompts/rule_group_cite.md":
        "82d440f6a68192763882744323b64eb83a95baebb2f9e8c0395193c98faeb84d",
    "backend/scripts/whatholdsup/audit_prompts/read.md":
        "6ea2f39f88794f68d8fd81bfe41b329d5531e8c8fa41461013930bb19db04792",
    "backend/scripts/whatholdsup/audit_prompts/summary.md":
        "1c7e7082472ee657c7014b4ce805ec62cf1ff16bd91cd0cf2548ca111764335a",
    "study/whu-reliability/RUN.md":
        "17e248432c128edaf747bd6f6fa808d48fa378d7cbb2c8097659ea8706cbe6c0",
}
# Pinned where they are read, and listed here so one report covers them all.
ELSEWHERE = {
    "study/whu-reliability/prompts/m1_citation_support.md": "judge_m1.PROMPT_SHA256",
    "study/whu-reliability/prompts/m2_conclusion_calibration.md": "judge_m2.PROMPT_SHA256",
    "study/whu-reliability/blinding/blind_phrases.json": "blind.PHRASES_SHA256",
    "study/whu-reliability/blinding/spelling_us.json": "blind.SPELLING_SHA256",
}


class FrozenFileChanged(RuntimeError):
    pass


def _rel(path) -> str:
    p = Path(path).resolve()
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(path)


def sha_of(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify(path) -> None:
    """Raise FrozenFileChanged if PATH is frozen and its sha256 differs."""
    rel = _rel(path)
    want = FROZEN_SHA256.get(rel)
    if want is None:
        return
    got = sha_of(ROOT / rel)
    if got != want:
        raise FrozenFileChanged("%s has sha256 %s, not the frozen %s (protocol rev 38): nothing runs on a "
                                "changed frozen file" % (rel, got, want))


def read_text(path) -> str:
    """PATH's text, after verify()."""
    verify(path)
    return Path(path).read_text(encoding="utf-8")


def mismatches() -> list[tuple[str, str, str]]:
    """(path, frozen sha256, sha256 now) for every pinned file that differs."""
    out = []
    for rel, want in FROZEN_SHA256.items():
        p = ROOT / rel
        got = sha_of(p) if p.exists() else "missing"
        if got != want:
            out.append((rel, want, got))
    return out


def verify_all() -> None:
    bad = mismatches()
    if bad:
        raise FrozenFileChanged("; ".join("%s has sha256 %s, not the frozen %s" % (r, g, w) for r, w, g in bad))


def is_study(slug: str) -> bool:
    for d in sorted((ROOT / "issues").glob("WHU-*-%s" % slug)):
        try:
            return bool(json.loads((d / "issue.json").read_text(encoding="utf-8")).get("study"))
        except Exception:
            return False
    return False


def main() -> int:
    bad = {r for r, _w, _g in mismatches()}
    for rel, want in FROZEN_SHA256.items():
        print("  %-5s %s  %s" % ("STOP" if rel in bad else "ok", want[:16], rel))
    for rel, where in ELSEWHERE.items():
        print("  %-5s %s  %s (pinned in %s)" % ("", sha_of(ROOT / rel)[:16], rel, where))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
