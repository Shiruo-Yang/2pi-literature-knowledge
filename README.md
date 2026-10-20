# Two-photon photoinitiator literature knowledge database

A source-linked database of literature field evidence, molecular identities, experimental-context candidates and photoinitiator priors. The current normalization integrates existing public registries and previously collected local corpus without re-extracting papers, overwriting raw evidence or promoting machine candidates to validated measurements.

Base snapshot: **2026-10-15** · Traceability update: **2026-10-20** · [Database guide](DATABASE_GUIDE.md) · [Quality audit](DATABASE_AUDIT.md) · [Base summary](data/literature/summary.json)

## Current database

| Object | Records | Meaning |
|---|---:|---|
| Combined source directory | 621 | DOI-first or alias-only source keys; not all have extracted evidence |
| Sources with recorded DOIs | 612 | Recorded identifiers, not newly verified publication metadata |
| Sources with field evidence | 286 | Actual field-evidence coverage, before internal-document flags |
| Automatic field candidates | 9,107 | Extracted candidates, not certified experimental values |
| Historical audit-layer records | 150 | Original audit status preserved; not newly re-audited |
| Integrated field records | 9,257 | 9,107 automatic candidates plus 150 historical records |
| Automatic evidence groups | 8,573 | Inherited duplicate groups with all members retained |
| Source-local entities | 124 | 72 accepted identities, 8 material/ionic, 13 nonchemical and 31 unresolved |
| Distinct recorded accepted structures | 26 | Distinct InChIKeys across the 72 source-local assignments |
| Evidence-to-entity links | 3,376 | Includes alias-only matches and source-local links |
| Condition/formulation clusters | 2,344 | Contextual groupings, not necessarily complete experimental recipes |
| Domain / mechanism / route priors | 25 / 25 / 19 | 69 rules with 477 source links, separate from measurements |

The previous 1,179-record public registry is fully accounted for: its 1,029 automatic records map to existing local candidates, and its 150 historical records remain a separate layer. **Do not add 1,179 to 9,107.** The previous 345-row source inventory is one input to the combined directory, not the full evidence-bearing source count. Of the 621 source keys, 335 have no field evidence in this build.

## Files to use

| File | Use |
|---|---|
| [literature.sqlite](data/literature/literature.sqlite) | Query all normalized relational tables and conservative views |
| [Current read-only query entry point](scripts/open_literature_database.py) | Combine the unchanged base with current source-location and field-use assessments |
| [Traceability overlay](data/literature/traceability/) / [summary](data/literature/traceability/summary.json) | Recovered original-source locations and explicit unresolved cases |
| [sources.csv](data/literature/sources.csv) | Source keys, DOIs, titles and scope flags |
| [evidence.csv](data/literature/evidence.csv) / [evidence.jsonl](data/literature/evidence.jsonl) | Spreadsheet / programmatic field-evidence access |
| [accepted_identities.csv](data/literature/accepted_identities.csv) / [entities.csv](data/literature/entities.csv) | Structure assignments and identity categories |
| [conditions.csv](data/literature/conditions.csv) / [formulations.csv](data/literature/formulations.csv) | Experimental-context groupings |
| [evidence_entity_links.csv](data/literature/evidence_entity_links.csv) | Link status, confidence and match basis |
| [rules.csv](data/literature/rules.csv) / [rule_sources.csv](data/literature/rule_sources.csv) | Domain, mechanism and route priors with citations |
| [quality_issues.csv](data/literature/quality_issues.csv) | Missing provenance and possible semantic conflicts |
| [public_evidence_crosswalk.csv](data/literature/public_evidence_crosswalk.csv) | Complete mapping from the earlier public registry |
| [data_dictionary.csv](data/literature/data_dictionary.csv) | Fields, missing values and unit policy |
| [input_assets.csv](data/literature/input_assets.csv), [provenance.csv](data/literature/provenance.csv), [manifest.json](data/literature/manifest.json) | Input hashes, row provenance and output checksums |

CSV files use UTF-8 with a byte-order mark for spreadsheet compatibility. SQLite provides relational queries; JSONL provides one evidence object per line. No Excel installation is needed.

## Quality and scientific-use boundaries

The original normalization flagged 1,399 evidence rows lacking page locators. The current source-location overlay recovers unique, source-verified locations for **1,017** of these: **772 publisher-XML node spans and 245 PDF page spans**. XML articles without pagination receive node addresses, not invented page numbers. **382 remain unresolved.** The base missing-page flags stay unchanged for audit history.

Across the union of missing-location and semantic-warning records, 1,496 records from 58 source identifiers were assessed; 1,092 have source-verified anchor locations, including 75 that already had page hints. DOI checks bind original documents to source metadata. Text matching locates an anchor, not a certified measurement.

The current view withholds the **250 nm wavelength component in four records** after assistant inspection of Pucher et al.'s original PDF page 9 confirmed that this number describes fabricated line width. These are four extractions from one source, not four independent experiments. No replacement wavelength or new line-width label is created. Another **33 records** lack their literal scalar in the attached anchor; their numerical use is held pending value-to-anchor review, without declaring their reported values wrong. One original page hint lies outside the recovered anchor span and is retained alongside the new location. See the [traceability method and field dictionary](TRACEABILITY.md).

The original 122 broad geometry/wavelength warnings remain available; the other 118 have not been cleared by this targeted check. Four possible internal research documents containing 32 field records remain excluded from external-evidence use in the current view. Neither exclusion nor recovered location certifies the remaining data as independent experiments.

Accepted identity is not an accepted numerical measurement. A field value, context cluster, alias match and source-supported structure are different evidence objects. Numeric-looking candidates still require correct compound, endpoint, unit, condition and original-source ownership. Absorption cross section is not polymerization efficiency; a maximum in a measured wavelength window is not automatically a global maximum.

This build creates **zero newly certified measurements and zero training labels**. It does not access sealed final-test labels, retrain models, update screening decisions or revise quantum-chemistry conclusions.

## Access and reproducibility

The public database contains metadata, scalar candidates, inherited identities, rules, relationships and hashes. Full text anchors, nonscalar extraction text, source PDFs and original path-bearing inputs remain in a separate local archive. Withheld public text is distinguished from data missing in the original extraction. Third-party content retains its original rights; no new licence over it is granted.

Validate with Python 3.11 or later:

```sh
python scripts/test_normalize_literature_database.py
python scripts/verify_normalized_database.py data/literature
python scripts/test_literature_traceability.py
python scripts/test_current_literature_view.py
python scripts/open_literature_database.py
python scripts/validate_release.py
```

The [database guide](DATABASE_GUIDE.md) describes rebuild inputs, normalization policies and SQL queries. The independent verifier checks all 17 tables, file hashes, foreign keys, group membership, CSV/JSONL mirrors and public export boundaries. With the private archive, it also verifies original input bytes and 62,575 row-provenance links.

## Earlier study records and compatibility

Use `data/literature` as the single current normalized database entry point. The older [public evidence package](outputs/literature_evidence_current/) and [identity package](outputs/literature_identity_current/) remain unchanged for compatibility and provenance; they are not extra observations to append.

The previous model, task-weight, screening and quantum-chemistry narrative is preserved in [Historical study context](HISTORICAL_STUDY_CONTEXT.md). Those study records are not inputs to this normalized database, and their scientific claims have not been renewed by the rebuild.
