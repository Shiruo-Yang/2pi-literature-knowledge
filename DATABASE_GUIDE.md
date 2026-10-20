# Literature database guide

Current source-location and field-use update: see [TRACEABILITY.md](TRACEABILITY.md) and use `scripts/open_literature_database.py` to join the unchanged base with its traceability overlay. Base tables below retain their original fields and counts; the overlay adds provenance and use restrictions, not new measurements.

## Scope and access

The active database is `data/literature/literature.sqlite`, accompanied by UTF-8-with-BOM CSV tables, an evidence JSONL export, a data dictionary and checksums. It integrates existing literature records; it is not a newly validated experimental dataset. The build does not access sealed test labels, train models, revise quantum-chemistry results or rerun optical-character recognition.

The public projection contains bibliographic metadata, scalar field candidates, inherited molecular identities, condition relationships, prior rules and provenance hashes. Source PDFs, complete text anchors, nonscalar candidate text, original input rows and local filesystem paths remain in a separate private archive. Empty public `anchor_text` cells therefore mean deliberately withheld text, not absent original evidence. `anchor_sha256` identifies the original anchor. `candidate_value_visibility` explains whether a value was exposed, originally absent or retained privately. Blank normalized values are not zero. There is no new licence grant over third-party material; consult original publishers and databases for reuse terms. No new dataset DOI or independent metadata certification is claimed.

## Tables and relationships

| Table | Meaning and key relationships |
|---|---|
| `sources` | DOI-first source keys; records without a usable DOI retain exact source aliases |
| `source_aliases` | Previous source identifiers mapped to stable source keys |
| `evidence` | Field records linked to sources, with units, inherited status, page hint and anchor hash |
| `evidence_groups`, `evidence_group_members` | Previously established automatic-candidate duplicate groups; all original members retained |
| `public_evidence_crosswalk` | Every record in the previous public evidence registry mapped to its new database record |
| `entities` | Source-local labels and separately marked existing global alias references |
| `accepted_identities` | Inherited source-local structure assignments; acceptance is about identity, not experimental numerical truth |
| `conditions`, `condition_members` | Extraction-local context groups and their evidence members |
| `formulations` | One context/formulation candidate per condition cluster; not necessarily a complete experimental recipe |
| `evidence_entity_links` | Evidence-to-entity matches, retaining match basis, confidence and original status |
| `rules`, `rule_sources` | Domain, mechanism and synthesis-route priors with their supporting source links |
| `quality_issues` | Machine-detected missing metadata or possible semantic conflicts; not confirmed corrections |
| `input_assets`, `provenance` | Original file hashes, data-row numbers and complete original-row hashes |

SQL foreign keys connect these tables. Source-local compounds keep their original entity IDs. A global alias match is not promoted to a source-local confirmed structure. An evidence-to-entity link with a NULL condition key means no condition cluster was assigned in the input.

## Normalization rules

1. Preserve all 17 input assets, their exact bytes and every original row in the private archive. Keep old published registries unchanged as compatibility inputs.
2. Normalize DOI casing and DOI URL prefixes. Resolve a DOI-absent source alias only when that exact alias has one observed DOI. Do not merge by approximate titles. Source keys hash either that DOI or the exact unresolved alias. A future DOI assignment requires an explicit crosswalk rather than an unrecorded ID change.
3. Reconcile public automatic records only when the original extraction ID, resolved source, endpoint, raw value and raw unit agree uniquely. Keep the 150 historical audit records as a separate evidence layer. Their audit status is inherited, not newly certified.
4. Preserve the 8,573 pre-existing candidate groups and all 9,107 member records. These groups are not equivalent to independent experiments. No merging across conditions is inferred from matching values.
5. Preserve original units and existing normalized values. No guessed conversions, interpolation, peak reassignment or numeric correction is performed. Public values are limited to syntactically numeric scalars; inequalities, ranges and compound context strings stay in the private raw archive.
6. Retain the distinction between source-local single molecules, materials/ionic records, nonchemical labels, unresolved identities and global alias-only references. Stored molecular identifiers are inherited; this build does not repeat chemical validation.
7. Flag document titles matching the project's evidence-guided, mechanism-aware workflow as possible internal research documents. The conservative view excludes those flagged documents, without deleting them or claiming that every remaining document is independent.
8. Flag wavelength-related candidates whose anchor also discusses line width, voxel size or spatial resolution. This deliberately broad heuristic identifies review candidates, not proven errors. It does not repair their values.

No new model labels or certified measurements are generated. Two-photon absorption, absorption at a particular wavelength, reported-window maxima and polymerization efficiency remain different quantities. A condition cluster does not certify unique compound–curve–measurement ownership.

## Rebuild and verify

Python 3.11 or later is required because some inherited CSV text contains embedded NUL characters. No third-party package is required. Supply a local JSON object mapping the 17 semantic input keys below to existing CSV paths. Keep that local configuration outside the repository:

`source_inventory`, `established_sources`, `public_sources`, `candidates`, `canonical_groups`, `public_evidence`, `source_entities`, `accepted_identities`, `terminal_entities`, `molecule_aliases`, `conditions`, `condition_members`, `formulations`, `entity_links`, `domain_rules`, `mechanism_rules`, `route_rules`.

```sh
python scripts/normalize_literature_database.py --inputs input_assets.local.json --public-output public_staging --private-output private_archive
python scripts/test_normalize_literature_database.py
python scripts/verify_normalized_database.py public_staging --private private_archive
```

Both build destinations must be new directories. Move a validated public projection into `data/literature` only after review. The private archive and its path-bearing configuration must never be committed. Public users can validate the delivered snapshot without the restricted inputs:

```sh
python scripts/verify_normalized_database.py data/literature
```

The verifier is independent of the builder. It checks file hashes, SQLite integrity and foreign keys, CSV/JSONL parity, group membership counts, source-local relationship consistency and public path/text exclusions. When the private archive is available, it also checks every original input file, every original row, all 62,575 provenance links and the previous public-registry crosswalk. These checks establish structural consistency, not scientific correctness of every extraction.

## Example queries

```sql
-- Evidence-bearing sources, not the larger discovery inventory.
SELECT COUNT(DISTINCT source_key) FROM evidence;

-- Source-local identity classes; these are not counts of unique molecules.
SELECT * FROM source_local_identity_summary;

-- Literature candidates after excluding flagged internal documents.
-- This view is NOT an independently validated training dataset.
SELECT s.doi, e.evidence_id, e.field_name, e.raw_value, e.raw_unit,
       e.page_hint, e.use_status
FROM literature_candidates_excluding_flagged_internal_docs e
JOIN sources s USING(source_key)
WHERE e.field_name LIKE '%sigma%';

-- Trace a candidate to its source and inherited structure link.
SELECT e.evidence_id, s.doi, n.label, a.canonical_smiles,
       l.original_status, e.use_status
FROM evidence e
JOIN sources s USING(source_key)
JOIN evidence_entity_links l USING(evidence_id)
JOIN entities n USING(entity_id)
LEFT JOIN accepted_identities a USING(entity_id);
```

## Compatibility and future updates

The previous `outputs/literature_evidence_current` and `outputs/literature_identity_current` packages remain unchanged for provenance and existing users. They are compatibility inputs, not additional records to append to the normalized database. The root model, screening and quantum-chemistry registries remain historical study artifacts and are not loaded by this normalizer. Public entry points use descriptive names, not internal iteration labels.

Future expansion should prioritize source-to-value ownership, page/table/figure locators, conditions and original experimental sources before increasing record counts. Newly verified corrections belong in an explicit evidence overlay linked to the original row; they must not overwrite raw evidence or inherit acceptance solely from a molecule-name match.
