# Current literature evidence database

This package additively combines the previous 150-record evidence registry with the automatic field-evidence registry. It contains **1,179 records** from **55 source identifiers**.

The broader literature candidate pool and legal-source resolution are tracked separately. A discovered or resolved source is not counted as field evidence unless a structured evidence record was generated.

## What is preserved

- `legacy_registry`: the earlier text-exact records remain unchanged in meaning and retain their prior accepted status.
- `automatic_field_registry`: machine-extracted field anchors and candidates retain their automatic status and use restriction.
- `duplicate_relation`: possible overlaps are labelled; no records are silently deleted.

## Files

- `literature_evidence_registry.csv`: complete tabular registry.
- `legacy_evidence_registry.csv`: stable 150-record input partition.
- `automatic_field_evidence_registry.csv`: stable 1,029-record automatic input partition.
- `literature_evidence_registry.jsonl`: one complete JSON object per record.
- `supplementary_evidence.csv`: supplementary-data copy of the complete registry.
- `numeric_evidence.csv`: records carrying a numeric/value candidate.
- `source_summary.csv`: source-level counts and covered fields.
- `literature_evidence.sqlite`: queryable SQLite database with registry, numeric subset, source summary, metadata, indexes and view.
- `literature_evidence_summary.json`: machine-readable counts and merge policy.

This is a fully automatic database merge. Automatic records are not silently promoted to manually verified facts; their machine status and provenance remain explicit.
