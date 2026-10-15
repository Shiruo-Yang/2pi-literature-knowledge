# Database normalization audit

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
