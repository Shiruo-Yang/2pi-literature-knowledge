# Unified literature evidence database

This package additively combines the previous 150-record evidence registry with the automatic field-evidence registry. It contains **1,179 records** from **55 source identifiers**.

The broader literature candidate pool contains 80 source records. In the current expansion snapshot, 51 have local or legally recovered full text and 29 remain metadata-only or not started. Candidate discovery and legal-source resolution are tracked separately; a discovered or resolved source is not counted as field evidence unless a structured evidence record was generated.

## What is preserved

- `legacy_registry`: the earlier text-exact records remain unchanged in meaning and retain their prior accepted status.
- `automatic_field_registry`: machine-extracted field anchors and candidates retain their automatic status and use restriction.
- `duplicate_relation`: possible overlaps are labelled; no records are silently deleted.
- The current automatic layer contains 715 full-text field anchors and 314 numeric or experimental-context candidates. These are automatic acquisition records, not claims of experimental verification.

## Files

- `unified_evidence_registry.csv`: complete tabular registry.
- `unified_evidence_registry.jsonl`: one complete JSON object per record.
- `supplementary_unified_evidence.csv`: supplementary-data copy of the complete registry.
- `unified_numeric_evidence.csv`: records carrying a numeric/value candidate.
- `unified_source_summary.csv`: source-level counts and covered fields.
- `unified_evidence_database.sqlite`: queryable SQLite database with registry, numeric subset, source summary, metadata, indexes, and view.
- `unified_evidence_summary.json`: machine-readable counts and merge policy.

This is a fully automatic database merge. Automatic records are not silently promoted to manually verified facts; their machine status and provenance remain explicit.
