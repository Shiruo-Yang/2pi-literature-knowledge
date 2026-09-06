# Current public database map

This repository is organized as one merged knowledge-and-decision package. The registries remain separate when they answer different scientific questions; they are not duplicated databases.

## Active public layers

| Layer | Main files | What it contains |
|---|---|---|
| Literature sources | `source_registry.csv`, `outputs/zotero_tpp_literature_pilot_20260828/` | Source metadata, access metadata and extracted literature evidence |
| Scientific prior knowledge | `domain_knowledge_registry.csv`, `mechanism_decision_registry.csv`, `synthesis_route_evidence_registry.csv` | Domain, mechanism and synthesis-precedent evidence |
| Model and task policy | `model_evaluation_registry.csv`, `task_weight_*.csv`, `TASK_WEIGHT_POLICY.md` | Frozen model records, six-task definitions, weights and sensitivity evidence |
| Current molecular identity database | `outputs/literature_identity_current/` | Source-local names, structures, aliases, formulation links and material/non-chemical classifications |
| Unresolved identity queue | `outputs/literature_identity_current/unresolved_queue/` | Automatic records that still lack a unique structure assignment |
| Screening and quantum chemistry | `screening_workflow_summary.csv`, `representative_qm_evidence_registry.csv` | Existing screening and candidate-level quantum-chemistry evidence |

## Current identity database

The active single-molecule registry contains 72 RDKit-valid accepted identities. Eight salts, ionic materials or commercial multicomponent records are retained separately, and 13 non-chemical tokens are terminally classified. The database also records 124 source-local entities, 3,376 evidence links and 2,344 formulation clusters.

The active machine-readable files are:

- `accepted_source_identity_registry.csv`: accepted source-local single-molecule identities;
- `multicomponent_material_registry.csv`: salts, ionic materials and commercial/multicomponent records;
- `terminal_identity_registry.csv`: material and non-chemical terminal classifications;
- `formulation_linkage_registry_enriched.csv`: source conditions linked to accepted identities where possible;
- `condition_identity_linkage.sqlite`: queryable copy of the current identity tables.

Earlier intermediate tables are retained only in `outputs/literature_identity_current/audit/` for traceability. They are not additional active records. No new experimental optical values, model labels, external-validation observations, screening decisions or quantum-chemistry inputs are created by this identity database.

## Reproducibility

`package_manifest.json` records the public package contents and hashes, while `checksums.sha256` and `scripts/validate_release.py` provide the release-level integrity check. Local PDFs, page images, caches and absolute workstation paths are excluded.
