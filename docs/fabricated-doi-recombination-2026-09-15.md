# The 59 fabricated identifiers: is the DOI suffix recombined from the citation?

For the research-reliability workstream. Written 2026-09-15; nothing here was
acted on in Signal, and the snapshot it reads
(`backend/scripts/signal/output/verify_sources_2026-09-14.json`, 381 rows,
unchanged since `9c135c9`) was not touched. The citations come from the live
`signal_sources.metadata.citation` of the same 59 rows (read-only; migration
081 changed two of the rows' `url`, not their citation).

## The hypothesis

Jain 2015 was stored as `10.1001/jama.2015.1534`. The real paper is JAMA
2015;313(15):1534–1540, DOI `10.1001/jama.2015.3077`. The model produced the
correct registrant (`10.1001`), the correct journal code (`jama`), the
correct year, and then the real **first page** as the suffix. Every part was
plausible; only the registry round-trip caught it. If most of the 59 are
built that way, that characterises the generative mechanism.

## Method

One definition, shared with the extractor that now flags this shape in
production (`backend/verify/extract.py::doi_recombination`; tests in
`tests/verify/test_doi_recombination.py`). For each DOI, the suffix after the
registrant's `/` is compared with the numbers its own citation states:

- **page / volume / issue** — whole digit runs of the suffix (1534 in
  `…2015.1534`, not 15 inside 2015);
- **article id** — alphanumeric elocation ids (`m4570`, `CD015687`,
  `EVIDra2300029`, `110native`) as case-insensitive substrings;
- **run together** — volume‖issue‖article, issue zero-padded (MDPI's
  `nu12061190` is volume 12, issue 06, article 1190);
- **year** — counted separately, 4-digit and publisher-style 2-digit
  (`JCO.22.`, `dc19-`, `S1470-2045(22)`), because a year in the suffix is a
  publisher convention, not a recombination on its own.

A second question the data forced: does the DOI follow the **DOI template the
cited journal's publisher actually uses** (Elsevier's `S0140-6736(yy)nnnnn-c`
for the Lancet, `10.1200/JCO.yy.nnnnn` for JCO, `10.1056/NEJMoannnnnnn`,
`10.1038/s41591-` for Nature Medicine, and so on)? Judged by prefix against a
hand-written map of the 45 journals named in these citations.

## Result

| | count | of 59 |
|---|---|---|
| suffix repeats the citation's page, volume, issue or article id (the shape Jain has) | **10** | 17% |
| — of which a page number | 4 (Jain ×2, `j.ctrv.2023.102589`, the SICI `…<2281::…`) | |
| — an article / elocation id | 4 (`bmj.m4570`, `CD015687`, `EVIDra2300029`, `110native`) | |
| — volume, issue and article run together | 2 (`nu12061190`, `s22072030`) | |
| suffix carries the citation's year (4-digit / 2-digit) | 13 / 7 | 34% |
| any of the above | 26 | 44% |
| **none of the above** | **33** | 56% |
| DOI follows the cited journal's publisher template | **49** | 83% |
| DOI follows a *different* journal's template than the one cited | 10 | 17% |

## Reading

**The strict recombination hypothesis does not hold for most of them.** Ten
of 59 are Jain's shape; of those, every one is a case where the cited
journal's real DOIs *do* embed the page or article id (JAMA, BMJ, Cochrane,
NEJM Evidence, MDPI, Elsevier article numbers, Wiley SICI). The model was not
recombining at random: it applied that publisher's template and filled the
template's article slot from the citation it had just written. Where the
publisher's template has no such slot (NEJM's `NEJMoa` + 7 digits, JCO's
`yy.nnnnn`, Springer's `s10549-yyy-nnnnn-c`, Elsevier's PII), the suffix is a
free digit string of the right length and shape, traceable to nothing.

So the mechanism the data supports is one level up: **the model reproduces
the publisher's DOI template for the journal it names — 49 of 59 times — and
fills the free positions with whatever the template asks for.** When the
template asks for the year, it supplies the citation's year (20 of 59). When
it asks for a page or article id, it supplies the citation's (10 of 59). When
it asks for an opaque serial, it invents one. Jain is the special case where
the template's free slot *is* a page number, so the fabrication and the
citation agree on it and every prior check passed.

Two corollaries for the workstream:

1. **Template-conformity is a stronger detector than recombination.** A
   fabricated DOI that follows the right template is indistinguishable from
   a real one by shape; the only test that works is resolution. The
   recombination flag (`doi_recombination`) catches the 10, and it will also
   flag real JAMA/BMJ/MDPI DOIs, which is why it is a flag and never a
   refusal. Nothing short of the registry decides.
2. **The ten template mismatches are a mechanism note, not a
   reclassification.** In nine the DOI is shaped for a different journal
   than the citation names — `blood.` for a JCO paper, `s10549-` (Breast
   Cancer Res Treat) for an Asian Pac J Cancer Prev paper and for a Nutr Rev
   paper, `jamacardio.` for a paper cited as JAMA, `EDE.` (Epidemiology) for
   Environ Health Perspect. The tenth cites "Lancet. 2019;392:2555-2564.
   Updated 2023." against an Annals of Oncology DOI.

   **Checked, not inferred (2026-09-15, read-only, live):** all ten were put
   through `literature.resolve` again. Every one returns Handle HTTP 404 with
   a parsed `responseCode` ≠ 1 — **NONEXISTENT, ten of ten**, agreeing with
   the snapshot. None resolves to any document, so none is a wrong document
   wearing the wrong citation; FABRICATED_IDENTIFIER is the correct verdict
   for all ten and **the 288 / 59 / 33 / 1 split stands as published.** The
   template confusion says something about how the fabrication was
   generated (the model reached for a neighbouring journal's template) and
   nothing about the source's existence. An earlier draft of this note
   called the group "WRONG_DOCUMENT leaking into FABRICATED"; that sentence
   is withdrawn.

## Per-row table

Template = whether the DOI's prefix and shape are the cited journal's
publisher's. Traceable = which citation numbers the suffix repeats.

| topic | fabricated DOI | cited as | template | traceable |
|---|---|---|---|---|
| breast-cancer-therapies | `10.1016/j.ctrv.2023.102589` | Cancer Treat Rev. 2023;117:102589. | yes | page 102589; year 2023 |
| breast-cancer-therapies | `10.1038/s41571-024-00870-0` | Nat Rev Clin Oncol. 2024;21(3):190-205. | yes | — |
| breast-cancer-therapies | `10.1093/annonc/mdac462` | 2019;392:2555-2564. Updated 2023. | n/a | — |
| breast-cancer-therapies | `10.1158/1078-0432.CCR-23-3847` | Clin Cancer Res. 2024;30(12):2532-2543. | yes | — |
| breast-cancer-therapies | `10.1186/s13058-024-01789-5` | Breast Cancer Res. 2024;26:78. | yes | — |
| breast-cancer-therapies | `10.1200/JCO.22.02436` | J Clin Oncol. 2023;41(12):2306-2319. | yes | — |
| breast-cancer-therapies | `10.1200/JCO.22.02726` | J Clin Oncol. 2023;41(14):2496-2510. | yes | — |
| breast-cancer-therapies | `10.1200/JCO.23.01338` | J Clin Oncol. 2024;42(5):560-575. | yes | — |
| car-t-cell-therapy | `10.1016/S1470-2045(22)00444-5` | Lancet Oncology. 2022;23(9):e421-e432. | yes | 2-digit year 22 |
| car-t-cell-therapy | `10.1016/S2352-3026(22)00103-4` | Lancet Haematology. 2022;9(6):e424-e433. | yes | 2-digit year 22 |
| car-t-cell-therapy | `10.1038/s41375-023-01847-3` | Leukemia. 2023;37(4):723-735. | yes | — |
| car-t-cell-therapy | `10.1182/blood-2022-167818` | Blood. 2022;140(Suppl 1):1360-1362. | yes | year 2022 |
| car-t-cell-therapy | `10.1182/blood.2021011888` | Blood. 2021;138(Suppl 1):1217. | yes | — |
| car-t-cell-therapy | `10.1182/blood.2021014831` | J Clin Oncol. 2021;39(35):3978-3992. | **no** | — |
| car-t-cell-therapy | `10.1200/JCO.20.01300` | J Clin Oncol. 2020;38(27):3119-3128. | yes | 2-digit year 20 |
| car-t-cell-therapy | `10.1200/JCO.22.01771` | J Clin Oncol. 2023;41(6):1128-1138. | yes | — |
| car-t-cell-therapy | `10.3324/haematol.2019.229518` | Haematologica. 2020;105(4):858-872. | yes | — |
| cgm-non-diabetic-populations | `10.1001/jama.2023.13050` | JAMA Internal Medicine. 2023;183(9):921–930. | **no** | year 2023 |
| cgm-non-diabetic-populations | `10.1007/s11695-021-05379-4` | Obesity Surgery. 2021;31(8):3507–3515. | yes | — |
| cgm-non-diabetic-populations | `10.1007/s41669-022-00357-5` | PharmacoEconomics Open. 2022;6(5):721–733. | yes | — |
| cgm-non-diabetic-populations | `10.1016/j.diabres.2022.110native` | Diabetes Research and Clinical Practice. 2022;190:110native. | yes | article 110native; year 2022 |
| cgm-non-diabetic-populations | `10.1093/ajcn/nqad025` | American Journal of Clinical Nutrition. 2023;117(4):812–821. | yes | — |
| cgm-non-diabetic-populations | `10.1093/ajcn/nqad045` | American Journal of Clinical Nutrition. 2023;117(6):1123-1135. | yes | — |
| cgm-non-diabetic-populations | `10.1101/2021.09.02.21263027` | 2021. doi:10.1101/2021.09.02.21263027. | yes | year 2021 |
| cgm-non-diabetic-populations | `10.1136/bjsports-2020-103154` | British Journal of Sports Medicine. 2021;55(10):560-568. | yes | — |
| cgm-non-diabetic-populations | `10.1186/s12966-023-01430-8` | International Journal of Behavioral Nutrition and Physical Activity. 2023;20(1):34. | yes | — |
| cgm-non-diabetic-populations | `10.2337/dc19-0655` | Diabetes Care. 2019;42(8):1593-1603. | yes | 2-digit year 19 |
| cgm-non-diabetic-populations | `10.3390/s22072030` | Sensors. 2022;22(7):2030. | yes | volume 22, issue 7 and 2030 run together |
| crispr-gene-therapy | `10.1001/jama.2023.14788` | JAMA. 2023;330(14):1365-1376. | yes | year 2023 |
| crispr-gene-therapy | `10.1002/14651858.CD015687` | Cochrane Database Syst Rev. 2023;8:CD015687. | yes | article CD015687 |
| crispr-gene-therapy | `10.1016/S2352-3026(23)00163-4` | Lancet Haematol. 2023;10(7):e528-e540. | yes | 2-digit year 23 |
| crispr-gene-therapy | `10.1016/j.ejhaem.2024.01.008` | Eur J Haematol. 2024;112(3):345-358. | **no** | year 2024 |
| crispr-gene-therapy | `10.1038/s41591-022-01807-5` | Nat Med. 2022;28(5):902-915. | yes | — |
| crispr-gene-therapy | `10.1056/EVIDra2300029` | NEJM Evidence. 2023;2(5):EVIDra2300029. | yes | article EVIDra2300029 |
| crispr-gene-therapy | `10.1056/NEJMoa2309805` | N Engl J Med. 2024;390(5):432-443. | yes | — |
| crispr-gene-therapy | `10.1056/NEJMoa2310054` | N Engl J Med. 2024;390(18):1649-1662. | yes | — |
| crispr-gene-therapy | `10.1182/blood.2023020164` | Blood. 2023;142(11):945-958. | yes | — |
| diet-and-breast-cancer-risk-prevention-and-recurrence | `10.1001/jamaoncol.2021.5465` | JAMA Oncol. 2022;8(1):39-47. | yes | — |
| diet-and-breast-cancer-risk-prevention-and-recurrence | `10.1007/s10549-019-05330-x` | Asian Pac J Cancer Prev. 2013;14(4):2407-2412. | **no** | — |
| diet-and-breast-cancer-risk-prevention-and-recurrence | `10.1007/s10549-020-05680-7` | Breast Cancer Res Treat. 2020;182(2):301-314. | yes | — |
| diet-and-breast-cancer-risk-prevention-and-recurrence | `10.1007/s10549-021-06147-3` | Nutr Rev. 2016;74(12):737-748. | **no** | — |
| diet-and-breast-cancer-risk-prevention-and-recurrence | `10.1136/bmjopen-2015-008879` | Br J Cancer. 2015;112(3):580-593. | **no** | year 2015 |
| diet-and-cancer-risk-recurrence | `10.1002/(SICI)1097-0142(19991201)86:11<2281::AID-CNCR12>3.0.CO;2-5` | Cancer. 1999;86(11):2281–2288. | yes | page 2281, volume 86, issue 11 |
| diet-and-cancer-risk-recurrence | `10.1136/bmj.m4570` | BMJ. 2021;372:m4570. | yes | article m4570 |
| diet-and-cancer-risk-recurrence | `10.3390/nu12061190` | Nutrients. 2020;12(6):1190. | yes | volume 12, issue 6 and 1190 run together |
| glp1-drugs | `10.1001/jama.2024.2525` | . JAMA Systematic Review: Weight Regain After GLP-1 RA Discontinuation, 2024 | yes | year 2024 |
| health-impacts-of-climate-change | `10.1016/S0140-6736(06)69261-6` | Lancet. 2006;367(9528):2101-2109. | yes | 2-digit year 06 |
| health-impacts-of-climate-change | `10.1016/S2542-5196(19)30003-7` | Lancet Planet Health. 2019;3(2):e46–e47. | yes | 2-digit year 19 |
| health-impacts-of-climate-change | `10.1016/S2542-5196(21)00278-6` | Lancet Planet Health. 2022;6(1):e9-e17. | yes | — |
| health-impacts-of-climate-change | `10.1017/S0033291717002981` | Nat Clim Chang. 2018;8(4):282-290. | **no** | — |
| health-impacts-of-climate-change | `10.1097/EDE.0b013e3181ad9d4d` | Environ Health Perspect. 2006;114(9):1318-1324. | **no** | — |
| mmr-vaccine-autism | `10.1001/jama.2015.1534` | JAMA. 2015;313(15):1534-1540. | yes | page 1534; year 2015 |
| mmr-vaccine-autism | `10.1001/jama.2015.1534` | JAMA. 2015;313(15):1534-1540. | yes | page 1534; year 2015 |
| mrna-vaccine-myocarditis | `10.1001/jamacardio.2021.5051` | JAMA. 2021;326(12):1210–1212. | **no** | year 2021 |
| social-media-teen-mental-health | `10.1007/s11126-022-10007-w` | Psychiatr Q. 2022;93:931-955. | yes | — |
| social-media-teen-mental-health | `10.1007/s40124-022-00271-6` | Curr Pediatr Rep. 2022;10:141-152. | yes | — |
| social-media-teen-mental-health | `10.1016/j.jadohealth.2022.07.025` | J Adolesc Health. 2022;71(6):696-705. | yes | year 2022 |
| social-media-teen-mental-health | `10.1111/jcom.12352` | Updated review: J Commun. 2020;70(4):555-577. | yes | — |
| social-media-teen-mental-health | `10.1177/0963721419877526` | Rev Gen Psychol. 2020;24(1):60-74. | yes | — |

## What the finding forces on the resolver

If shape cannot distinguish a fabricated DOI from a real one, the registry
round-trip is the only test in the literature path, and the registries'
failure behaviour is the system's. Measured on 2026-09-15 with each failure
injected: `verify.search` reported a 429, a 5xx, a timeout and an
unparseable 200 all as "no registry title matched" — a refusal, but one that
misstated the fact; and `literature.resolve` reported a Handle 429, 503 or
HTML 200 as **EXISTS**. Both fixed the same day: `search` now returns
`REGISTRY_UNAVAILABLE` (with each registry's answered/not and the HTTP
reason) apart from `NOT_FOUND`; `resolve` decides existence only on a parsed
Handle answer and otherwise stays `UNCHECKED` with `registry_unavailable` on
the record, which the publication record carries as
`resolve: REGISTRY_UNAVAILABLE handle: HTTP 429 after 4 attempts` apart from
`resolve: NONEXISTENT`. `http.get` retries at most four times. Every case is
a test with the failure injected: `tests/verify/test_registry_unavailable.py`.

## Not done, deliberately

No source was re-resolved, no row of the snapshot or the corpus changed, and
no topic other than mmr-vaccine-autism has been through the publish gate; the
57 non-mmr rows here belong to unpublished topics. The extractor flag is
live in `verify/policy.py` for every gated surface, as a note appended to the
identifier's refusal or flag reason.
