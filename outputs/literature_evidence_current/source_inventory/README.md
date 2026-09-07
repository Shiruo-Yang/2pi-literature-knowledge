# Current public source inventory (2026-08-28)

This directory contains the current Zotero source inventory and access-resolution metadata used by the public literature database.

## Deduplication policy

- Sources are deduplicated DOI-first. If DOI is absent, the source remains a separate metadata record; no fuzzy title match was promoted.
- Candidate and audited evidence are deduplicated by exact same-layer signature. Cross-layer overlaps are retained because machine candidates and audited values have different evidentiary meanings.
- The current literature evidence registry already contains the 1,179 evidence IDs; `remote_evidence_crosswalk.csv` records that no evidence ID needed to be appended during the source-inventory merge.
- Local PDF/text/screenshot paths are replaced by `local_only/...` placeholders. No PDF, full-text file, cookie, credential, or absolute local path is included.

## Files

- `integrated_literature_evidence.sqlite`: public-safe queryable database with C1 sources, merged sources, Zotero papers, deduplicated evidence, source access metadata, FTS5, and provenance tables.
- `merged_source_registry.csv`: C1 + Zotero source registry after DOI-first merge.
- `zotero_source_crosswalk.csv`: maps all Zotero keys to merged source IDs and merge basis.
- `candidate_evidence_deduplicated.csv`: sanitized automatic candidate layer.
- `audited_evidence_deduplicated.csv`: sanitized page-audited layer.
- `source_access_resolution.csv`: OA/landing-page metadata only.
- `dedup_relations.csv`: records removed exact same-layer duplicates and their canonical IDs.
- `remote_evidence_crosswalk.csv`: exact-ID comparison with the current public literature evidence registry.
- `dedup_merge_report.json`: machine-readable counts and policy.

All automatic records remain candidates; automatic status is not a claim of human-verified experimental truth.
