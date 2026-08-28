# Unified literature evidence database

This package additively combines the previous 137-record evidence registry with the automatic field-evidence registry. It contains **1,145 records** from **54 source identifiers**.

The broader literature candidate pool contains 80 source records. The expansion batch added 40 candidates; 10 had local full text available for automatic parsing and 30 remained metadata-only or unresolved at the time of this snapshot. These candidate records are not counted as field evidence unless an evidence record was actually generated.

## What is preserved

- `legacy_registry`: the earlier text-exact records remain unchanged in meaning and retain their prior accepted status.
- `automatic_field_registry`: machine-extracted field anchors and candidates retain their automatic status and use restriction.
- `duplicate_relation`: possible overlaps are labelled; no records are silently deleted.
- Source coverage is reported separately from the broader candidate pool, so a source being discovered or resolved does not by itself mean that it contributed a verified scientific value.

## Files

- `unified_evidence_registry.csv`: complete tabular registry.
- `unified_evidence_registry.jsonl`: one complete JSON object per record.
- `supplementary_unified_evidence.csv`: supplementary-data copy of the complete registry.
- `unified_numeric_evidence.csv`: records carrying a numeric/value candidate.
- `unified_source_summary.csv`: source-level counts and covered fields.
- `unified_evidence_database.sqlite`: queryable SQLite database with registry, numeric subset, source summary, metadata, indexes, and view.
- `unified_evidence_summary.json`: machine-readable counts and merge policy.

This is a fully automatic database merge. Automatic records are not silently promoted to manually verified facts; their machine status and provenance remain explicit.
