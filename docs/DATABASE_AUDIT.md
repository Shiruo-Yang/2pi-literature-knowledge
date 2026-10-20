# Database normalization audit

## Manuscript-aligned organization: 2026-10-20

The current scientific export is `data/research/research.sqlite`. Its five modules follow the study's molecular-design priors, six-task property rationale, mechanism admissibility, formulation/processing context and synthesis evidence. The 98 inherited field names map to 56 canonical concepts, with all 9,257 IDs retained. The 69 priors, 72 source-local accepted identities and six endpoint definitions retain their previous scientific status and weights. Existing metadata filled 449 missing bibliography cells by exact DOI; six journal-format variants retain established spelling. The previous use restrictions remain active. See [RESEARCH_DATABASE.md](RESEARCH_DATABASE.md) for record definitions, current counts and validation.

Use-specific assessments now cover all 9,257 fields and 69 rules, with a 56-concept coverage table. The paper-supporting index has 80 entries of four different types, not 80 independent measurements. Five previously audited source structures, two source-defined optical table records, 16 condition fields and three review-to-primary bibliographic links are integrated through a path-free input projection. Five existing-audit DOI references extend the scientific source inventory from 621 to 626 without changing the preserved base. The two optical cases remain window maxima with missing laser specifications and no training/final-test eligibility. Independent source-input verification re-parsed their table values and checked 18 original asset hashes plus the main PDF. Whole-corpus semantic accuracy remains unmeasured; no candidate or rule is promoted merely by these engineering checks.

## Read-only source organisation: 2026-10-20

The current 33-table export adds source dossiers and attachment provenance without changing the five scientific modules. A Zotero snapshot matched 471 existing DOI sources. OpenRefine retained every input row and original column; syntax-cleanup changes were zero. Exact-DOI empty-field fills added 341 years and 333 journal names, leaving 15 missing years and 24 missing journals. Thirty-six formatting differences and two content differences retain existing values. Together with the prior 449 fills, 1,123 bibliography cells have explicit fill provenance.

The 666 attachment links include 518 local PDF links and 425 distinct hashes. All 45 repeated-content groups are within one source; no files were deleted or sources merged. First-page DOI checks returned 463 literal matches and 55 unresolved links, without unique attachment-identity certification. Ten papers were processed by each of LiteParse and Docling, producing 20 parser outputs and seven candidate tables. A dropped-cell warning on one table is retained; no numeric candidate is promoted by parser success.

Independent public verification checks all 33 CSV/SQLite mirrors and the new input projections. Optional private verification re-reads 471 Zotero metadata rows, rehashes 518 original PDF links, recomputes 518 first-page checks, and checks all 20 parser-output fingerprints. These are provenance and transformation checks, not measured semantic precision or recall. All 9,257 original field records, 6,179 scalar candidates, six fixed endpoints, use restrictions and prior source-audit facts remain unchanged. Zotero mutations and new experiment/training labels are zero. No source full text, original image or private path is added to the public package.

## Source-location follow-up: 2026-10-20

The base snapshot below is unchanged. A new reversible overlay covers 1,496 targeted records from 58 source identifiers. It supplies source-verified locations for 1,017 of the 1,399 records originally lacking page hints (772 XML node spans and 245 PDF page spans), leaving 382 unresolved. Including records with prior hints, 1,092 anchor locations pass source verification. Fifty-six original source-file hashes and all target records passed the independent verifier.

Four extractions from one Pucher source have their 250 nm wavelength component withheld after assistant source-image inspection identifies fabricated line width. Thirty-three literal scalar-to-anchor gaps are withheld from numerical reuse pending review; one original page hint is inconsistent with the recovered anchor location. Original values are not changed. The current read-only view retains 9,257 records and explicitly exposes these restrictions. Nine matching tests and seven view tests pass. See [TRACEABILITY.md](TRACEABILITY.md) for methods, limits and full counts.

## Original normalization snapshot

Audit date: 2026-10-15. Scope: existing literature corpus and the current public repository, with no model fitting or new source extraction.

## Reconciled record flow

- 9,107 local automatic field candidates were preserved.
- All 1,029 public automatic records mapped uniquely to those candidates by preserved extraction origin, source, endpoint, raw value and raw unit. They were not counted twice.
- 150 historical audit records were retained as a separate layer, yielding 9,257 field records. Historical audit statuses were not re-certified.
- 8,573 inherited candidate groups retain all 9,107 automatic members.
- 621 DOI-first or alias-only source keys were assembled across the selected assets. Of these, 612 have recorded DOIs, 286 have field evidence, and 335 have no field evidence in this build. These are inventory unions, not 621 newly read papers or independent experiments. The original 345-row source inventory is only one input asset.
- 124 source-local entities comprise 72 accepted identity assignments, 8 material/ionic records, 13 nonchemical records and 31 unresolved records. The 72 accepted assignments contain 26 distinct recorded InChIKeys. Another 86 entities are inherited global alias references, not additional accepted source-local molecules.
- 2,344 condition clusters, 8,107 cluster members, 2,344 formulation/context candidates and 3,376 evidence-to-entity links were preserved.
- 69 prior rules comprise 25 domain rules, 25 mechanism rules and 19 route-evidence records, with 477 rule–source links. They are not 69 experimental measurements.

## Quality findings retained in the database

| Finding | Count | Interpretation |
|---|---:|---|
| Missing page locator | 1,399 evidence rows | Original anchors remain locally; page-level provenance is incomplete |
| DOI absent on original evidence row | 48 evidence rows | Some can still resolve via a unique source alias; this count describes input completeness |
| Geometry/wavelength context collision | 122 evidence rows | Broad semantic warning requiring source-level resolution; not 122 proven errors |
| Possible internal research documents | 4 source keys / 32 evidence rows | Kept for provenance, excluded by the conservative literature-candidate view |

The 1,573 quality issues are issue occurrences, not 1,573 independent faulty records. A record can have multiple issues. The build creates zero newly certified numerical observations and zero training labels.

## Verification

Five focused unit tests pass. The independent verifier checks all 17 relational tables, file hashes, foreign keys, CSV/JSONL mirrors, condition/group membership, source-local link consistency and public export boundaries. With the private archive it also checks all 17 original assets and 62,575 row-provenance links, plus the complete 1,179-record public crosswalk. SQLite integrity is `ok`, with no foreign-key violations.

No new full text, PDF, absolute local path, source screenshot or sealed final-test label is included in the normalized public export. The public export is a metadata/scalar projection of a separately retained full local database, not a claim that copyrighted source text is openly licensed.

The legacy study README has been preserved in `HISTORICAL_STUDY_CONTEXT.md`. Existing model/QM/screening records and prior published evidence files have not been replaced. This audit does not renew the scientific claims in those historical files.
