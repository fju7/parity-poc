"""Write provisions.json for build_attorney_doc.js from candidates.json + retrieved text.

Excerpts are VERBATIM slices of the fetched provision: the sentences carrying the
assertion's figures or distinctive words, in document order, ' […] ' between
non-adjacent ones. Never paraphrased. Sheets 6 and 7 carry a specific question
under "Why we selected it".

    cd backend && python3 scripts/legal_review/build_provisions.py && (cd scripts/legal_review && node build_attorney_doc.js OUT.docx)
"""
import json, re, sys
from pathlib import Path
BACKEND = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(BACKEND))
from verify import law
from verify.numbers import figures, canonical_numbers
from verify.text import content_tokens, LAW_BOILERPLATE

MEANING = {"CO-16": "Claim/service lacks information or has submission/billing error(s).",
           "CO-45": "Charge exceeds fee schedule/maximum allowable or contracted/legislated fee arrangement.",
           "CO-97": "The benefit for this service is included in the payment/allowance for another service/procedure that has already been adjudicated.",
           "CO-4": "The procedure code is inconsistent with the modifier used, or a required modifier is missing.",
           "CO-50": "These are non-covered services because this is not deemed a 'medical necessity' by the payer.",
           "OA-18": "Exact duplicate claim/service.", "PR-1": "Deductible amount."}
NOTES = {6: "Question for you: 3922.01 is the definitions section of the external-review chapter. Should the operative request section be cited instead — and which one?",
         7: "Question for you: does a bare CO-50 without disclosed criteria plausibly reach the unfair-practices prohibition, or is this over-reach in a first-level appeal?"}
OUR_NOTE = ("Our automated check confirms this provision exists, that its text contains the figures asserted, and that it "
            "applies to this payer type in Ohio. It cannot confirm that it is the right provision to cite for this denial "
            "reason. That is the question on this sheet.")


def excerpt(text, assertion, characterisation, limit=1600):
    sents = re.split(r"(?<=[.;])\s+(?=[A-Z(])", text)
    want_nums = figures(assertion); want_words = content_tokens(assertion + " " + characterisation, LAW_BOILERPLATE)
    keep = []
    for i, s in enumerate(sents):
        score = len(canonical_numbers(s) & want_nums) * 3 + len(content_tokens(s, LAW_BOILERPLATE) & want_words)
        if score: keep.append((i, score, s.strip()))
    keep.sort(key=lambda x: -x[1]); chosen = sorted(keep[:6])
    out, total, last = [], 0, None
    for i, _, s in chosen:
        if total + len(s) > limit: break
        out.append(("" if last is None or i == last + 1 else "[…] ") + s); total += len(s); last = i
    return " ".join(out) if out else text[:limit]


def main():
    rows = json.loads((BACKEND / "data" / "verify" / "candidates.json").read_text())["rows"]
    prov = []
    for n, r in enumerate(rows, 1):
        ident = law.identify(r["cite"]); res = law.resolve(ident); doc = law.fetch(res)
        if doc is None:
            sys.exit(f"row {n}: {r['cite']} did not resolve/fetch; the packet must not carry a provision the gate cannot")
        prov.append({"id": f"OH-{n:02d}", "denialCode": r["denial_code"], "denialMeaning": MEANING[r["denial_code"]],
                     "payerType": "Commercial (non-Medicare)" if r["payer_type"] == "commercial" else "Medicare",
                     "citation": r["cite"], "heading": (res.heading or "").split(" || ")[0], "source": res.canonical,
                     "excerpt": excerpt(doc.text, r["may_assert"], r["characterisation"]),
                     "assertion": r["may_assert"][0].upper() + r["may_assert"][1:] + ".",
                     "rationale": r["rationale"] + (("  " + NOTES[n]) if n in NOTES else ""),
                     "ourNote": OUR_NOTE})
    (Path(__file__).parent / "provisions.json").write_text(json.dumps(prov, indent=1, ensure_ascii=False))
    print(f"{len(prov)} provisions written")


if __name__ == "__main__":
    main()
