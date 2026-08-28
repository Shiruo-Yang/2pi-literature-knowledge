"""Merge the legacy audited evidence registry with the automatic field registry.

The merge is intentionally additive.  Legacy records remain identifiable as
legacy audited text evidence, automatic records retain their machine status,
and possible overlaps are marked rather than silently removed.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
LEGACY_CSV = ROOT / "outputs/zotero_tpp_literature_pilot_20260828/audited_evidence/audited_evidence_registry.csv"
AUTOMATIC_CSV = ROOT / "outputs/zotero_tpp_literature_pilot_20260828/automatic_field_evidence_v3/literature_field_evidence_registry.csv"
OUTPUT_DIR = ROOT / "outputs/zotero_tpp_literature_pilot_20260828/unified_evidence_v1"


CANONICAL_FIELDS = [
    "evidence_id",
    "source_id",
    "zotero_key",
    "doi",
    "title",
    "field_name",
    "raw_value",
    "raw_unit",
    "normalized_value",
    "normalized_unit",
    "page_hint",
    "evidence_anchor",
    "local_context",
    "formulation",
    "wavelength_nm",
    "figure_or_table",
    "data_role",
    "evidence_lane",
    "confidence_class",
    "automatic_status",
    "automatic_use",
    "source_layer",
    "source_record_id",
    "source_text_path",
    "automatic_reason",
    "notes",
    "record_origin",
    "legacy_value_type",
    "legacy_audit_status",
    "legacy_visual_audit_reference",
    "legacy_source_json",
    "evidence_identity_key",
    "duplicate_group_id",
    "duplicate_group_size",
    "duplicate_relation",
]


def text(value: object) -> str:
    return "" if value is None else str(value).strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [{key: text(value) for key, value in row.items()} for row in csv.DictReader(handle)]


def safe_relative_path(value: str) -> str:
    """Keep provenance useful without exporting machine-specific absolute paths."""

    value = text(value)
    if not value:
        return ""
    parts = [part.strip() for part in re.split(r"[;|]\s*", value) if part.strip()]
    safe_parts: list[str] = []
    for part in parts:
        path = Path(part)
        try:
            safe = path.resolve().relative_to(ROOT.resolve()).as_posix()
        except (OSError, ValueError):
            # For paths outside this repository, preserve only the final name.
            safe = path.name or part.replace("\\", "/").split("/")[-1]
        safe_parts.append(safe)
    return "; ".join(dict.fromkeys(safe_parts))


def legacy_field_name(value_type: str) -> str:
    mapping = {
        "polymerization_threshold_laser_power": "polymerization_threshold",
        "polymerization_threshold_relative_claim": "polymerization_threshold",
    }
    return mapping.get(value_type, value_type)


def make_legacy(row: dict[str, str]) -> dict[str, str]:
    source_id = text(row.get("paper_id")) or text(row.get("zotero_key")) or text(row.get("doi"))
    value_type = text(row.get("value_type"))
    anchor = text(row.get("evidence_anchor"))
    notes = text(row.get("notes"))
    if value_type and f"legacy_value_type={value_type}" not in notes:
        notes = f"{notes}; legacy_value_type={value_type}" if notes else f"legacy_value_type={value_type}"
    return {
        "evidence_id": text(row.get("evidence_id")),
        "source_id": source_id,
        "zotero_key": text(row.get("zotero_key")),
        "doi": text(row.get("doi")),
        "title": text(row.get("title")),
        "field_name": legacy_field_name(value_type),
        "raw_value": text(row.get("raw_value")),
        "raw_unit": text(row.get("raw_unit")),
        "normalized_value": text(row.get("normalized_value")),
        "normalized_unit": text(row.get("normalized_unit")),
        "page_hint": text(row.get("page_hint")),
        "evidence_anchor": anchor,
        "local_context": anchor,
        "formulation": text(row.get("formulation")),
        "wavelength_nm": text(row.get("wavelength_nm")),
        "figure_or_table": text(row.get("figure_id")),
        "data_role": text(row.get("data_role")),
        "evidence_lane": text(row.get("evidence_lane")) or "text_exact",
        "confidence_class": text(row.get("confidence_class")),
        "automatic_status": "legacy_accepted_preserved",
        "automatic_use": "legacy_evidence_reference",
        "source_layer": "legacy_audited_text_exact",
        "source_record_id": text(row.get("evidence_id")),
        "source_text_path": safe_relative_path(row.get("source_json", "")),
        "automatic_reason": "Preserved from the previous evidence registry; no machine reinterpretation applied.",
        "notes": notes,
        "record_origin": "legacy_registry",
        "legacy_value_type": value_type,
        "legacy_audit_status": text(row.get("audit_status")),
        "legacy_visual_audit_reference": safe_relative_path(row.get("visual_audit_reference", "")),
        "legacy_source_json": safe_relative_path(row.get("source_json", "")),
    }


def make_automatic(row: dict[str, str]) -> dict[str, str]:
    result = {field: text(row.get(field, "")) for field in CANONICAL_FIELDS}
    result.update(
        {
            "record_origin": "automatic_field_registry",
            "legacy_value_type": "",
            "legacy_audit_status": "",
            "legacy_visual_audit_reference": "",
            "legacy_source_json": "",
        }
    )
    result["source_text_path"] = safe_relative_path(result.get("source_text_path", ""))
    return result


def identity_key(row: dict[str, str]) -> str:
    """Create a stable overlap key; it is a review aid, not a deletion key."""

    source = text(row.get("doi")).lower() or text(row.get("source_id")).lower() or text(row.get("title")).lower()
    values = [
        source,
        text(row.get("field_name")).lower(),
        text(row.get("raw_value")).lower(),
        text(row.get("raw_unit")).lower(),
        text(row.get("normalized_value")).lower(),
        text(row.get("normalized_unit")).lower(),
        text(row.get("page_hint")).lower(),
        text(row.get("formulation")).lower(),
        text(row.get("wavelength_nm")).lower(),
    ]
    payload = "\x1f".join(values).encode("utf-8")
    return "EIK-" + hashlib.sha256(payload).hexdigest()[:16]


def assign_overlap_metadata(rows: list[dict[str, str]]) -> None:
    groups: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = identity_key(row)
        row["evidence_identity_key"] = key
        groups[key].append(row)

    for key, group in groups.items():
        origins = {text(row.get("record_origin")) for row in group}
        if len(origins) > 1:
            relation = "legacy_automatic_overlap"
        elif len(group) > 1:
            relation = "same_layer_duplicate_candidate"
        else:
            relation = "unique_record"
        group_id = "DUP-" + key.removeprefix("EIK-")
        for row in group:
            row["duplicate_group_id"] = group_id
            row["duplicate_group_size"] = str(len(group))
            row["duplicate_relation"] = relation


def write_csv(path: Path, rows: Iterable[dict[str, str]], fields: list[str]) -> None:
    rows = list(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: text(row.get(field, "")) for field in fields})


def source_summary(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[text(row.get("source_id")) or text(row.get("doi")) or text(row.get("title"))].append(row)
    result: list[dict[str, str]] = []
    for source_id, items in sorted(grouped.items()):
        result.append(
            {
                "source_id": source_id,
                "doi": next((text(item.get("doi")) for item in items if text(item.get("doi"))), ""),
                "title": next((text(item.get("title")) for item in items if text(item.get("title"))), ""),
                "total_record_count": str(len(items)),
                "legacy_record_count": str(sum(text(item.get("record_origin")) == "legacy_registry" for item in items)),
                "automatic_record_count": str(sum(text(item.get("record_origin")) == "automatic_field_registry" for item in items)),
                "field_names": "; ".join(sorted({text(item.get("field_name")) for item in items if text(item.get("field_name"))})),
                "evidence_lanes": "; ".join(sorted({text(item.get("evidence_lane")) for item in items if text(item.get("evidence_lane"))})),
                "automatic_statuses": "; ".join(sorted({text(item.get("automatic_status")) for item in items if text(item.get("automatic_status"))})),
                "overlap_group_count": str(len({text(item.get("duplicate_group_id")) for item in items if text(item.get("duplicate_relation")) == "legacy_automatic_overlap"})),
            }
        )
    return result


def build_sqlite(rows: list[dict[str, str]], numeric_rows: list[dict[str, str]], sources: list[dict[str, str]], path: Path, metadata: dict[str, object]) -> None:
    if path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    try:
        column_sql = ", ".join(f'"{field}" TEXT' for field in CANONICAL_FIELDS)
        connection.execute(f'CREATE TABLE unified_evidence_registry (db_row_id INTEGER PRIMARY KEY AUTOINCREMENT, {column_sql})')
        connection.execute(f'CREATE TABLE unified_numeric_evidence (db_row_id INTEGER PRIMARY KEY AUTOINCREMENT, {column_sql})')
        source_fields = list(sources[0].keys()) if sources else [
            "source_id", "doi", "title", "total_record_count", "legacy_record_count", "automatic_record_count",
            "field_names", "evidence_lanes", "automatic_statuses", "overlap_group_count",
        ]
        source_sql = ", ".join(f'"{field}" TEXT' for field in source_fields)
        connection.execute(f'CREATE TABLE unified_source_summary ({source_sql})')
        connection.execute('CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)')
        placeholders = ", ".join("?" for _ in CANONICAL_FIELDS)
        insert_sql = f'INSERT INTO unified_evidence_registry ({", ".join(chr(34) + f + chr(34) for f in CANONICAL_FIELDS)}) VALUES ({placeholders})'
        numeric_insert_sql = f'INSERT INTO unified_numeric_evidence ({", ".join(chr(34) + f + chr(34) for f in CANONICAL_FIELDS)}) VALUES ({placeholders})'
        connection.executemany(insert_sql, [[text(row.get(field)) for field in CANONICAL_FIELDS] for row in rows])
        connection.executemany(numeric_insert_sql, [[text(row.get(field)) for field in CANONICAL_FIELDS] for row in numeric_rows])
        source_placeholders = ", ".join("?" for _ in source_fields)
        source_insert = f'INSERT INTO unified_source_summary ({", ".join(chr(34) + f + chr(34) for f in source_fields)}) VALUES ({source_placeholders})'
        connection.executemany(source_insert, [[text(row.get(field)) for field in source_fields] for row in sources])
        connection.executemany('INSERT INTO metadata (key, value) VALUES (?, ?)', [(key, json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value) for key, value in metadata.items()])
        connection.execute('CREATE INDEX idx_unified_source ON unified_evidence_registry (source_id)')
        connection.execute('CREATE INDEX idx_unified_field ON unified_evidence_registry (field_name)')
        connection.execute('CREATE INDEX idx_unified_origin ON unified_evidence_registry (record_origin)')
        connection.execute('CREATE INDEX idx_unified_overlap ON unified_evidence_registry (duplicate_relation)')
        connection.execute('CREATE VIEW v_unified_evidence AS SELECT * FROM unified_evidence_registry')
        connection.commit()
    finally:
        connection.close()


def main() -> None:
    legacy_rows = [make_legacy(row) for row in read_csv(LEGACY_CSV)]
    automatic_rows = [make_automatic(row) for row in read_csv(AUTOMATIC_CSV)]
    rows = legacy_rows + automatic_rows
    assign_overlap_metadata(rows)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    numeric_fields = {"sigma_2pa", "pi_loading", "polymerization_threshold", "isc_t1_proxy"}
    numeric_rows = [row for row in rows if text(row.get("raw_value")) or text(row.get("field_name")) in numeric_fields]
    sources = source_summary(rows)
    now = datetime.now(timezone.utc).isoformat()
    summary = {
        "generated_at_utc": now,
        "merge_policy": "additive; possible overlaps marked and retained",
        "legacy_input_records": len(legacy_rows),
        "automatic_input_records": len(automatic_rows),
        "unified_record_count": len(rows),
        "unified_numeric_or_value_records": len(numeric_rows),
        "unified_source_count": len(sources),
        "record_origin_counts": dict(Counter(row["record_origin"] for row in rows)),
        "source_layer_counts": dict(Counter(row["source_layer"] for row in rows)),
        "field_counts": dict(Counter(row["field_name"] for row in rows)),
        "duplicate_relation_counts": dict(Counter(row["duplicate_relation"] for row in rows)),
        "automatic_status_counts": dict(Counter(row["automatic_status"] for row in rows)),
        "input_files": {
            "legacy_registry": LEGACY_CSV.relative_to(ROOT).as_posix(),
            "automatic_registry": AUTOMATIC_CSV.relative_to(ROOT).as_posix(),
        },
        "outputs": {
            "registry_csv": "unified_evidence_registry.csv",
            "registry_jsonl": "unified_evidence_registry.jsonl",
            "supplementary_csv": "supplementary_unified_evidence.csv",
            "numeric_csv": "unified_numeric_evidence.csv",
            "source_summary_csv": "unified_source_summary.csv",
            "sqlite": "unified_evidence_database.sqlite",
        },
    }

    write_csv(OUTPUT_DIR / "unified_evidence_registry.csv", rows, CANONICAL_FIELDS)
    write_csv(OUTPUT_DIR / "supplementary_unified_evidence.csv", rows, CANONICAL_FIELDS)
    write_csv(OUTPUT_DIR / "unified_numeric_evidence.csv", numeric_rows, CANONICAL_FIELDS)
    write_csv(OUTPUT_DIR / "unified_source_summary.csv", sources, list(sources[0].keys()) if sources else [])
    with (OUTPUT_DIR / "unified_evidence_registry.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (OUTPUT_DIR / "unified_evidence_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    build_sqlite(rows, numeric_rows, sources, OUTPUT_DIR / "unified_evidence_database.sqlite", summary)

    readme = f"# Unified literature evidence database\n\n"
    readme += f"This package additively combines the previous 49-record evidence registry with the automatic field-evidence registry. It contains **{len(rows):,} records** from **{len(sources):,} source identifiers**.\n\n"
    readme += "## What is preserved\n\n"
    readme += "- `legacy_registry`: the earlier text-exact records remain unchanged in meaning and retain their prior accepted status.\n"
    readme += "- `automatic_field_registry`: machine-extracted field anchors and candidates retain their automatic status and use restriction.\n"
    readme += "- `duplicate_relation`: possible overlaps are labelled; no records are silently deleted.\n\n"
    readme += "## Files\n\n"
    readme += "- `unified_evidence_registry.csv`: complete tabular registry.\n- `unified_evidence_registry.jsonl`: one complete JSON object per record.\n- `supplementary_unified_evidence.csv`: supplementary-data copy of the complete registry.\n- `unified_numeric_evidence.csv`: records carrying a numeric/value candidate.\n- `unified_source_summary.csv`: source-level counts and covered fields.\n- `unified_evidence_database.sqlite`: queryable SQLite database with registry, numeric subset, source summary, metadata, indexes, and view.\n- `unified_evidence_summary.json`: machine-readable counts and merge policy.\n\n"
    readme += "This is a fully automatic database merge. Automatic records are not silently promoted to manually verified facts; their machine status and provenance remain explicit.\n"
    (OUTPUT_DIR / "README.md").write_text(readme, encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
