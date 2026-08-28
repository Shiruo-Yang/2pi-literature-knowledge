"""Build a no-manual-stop literature evidence database.

This workflow deliberately keeps every machine-derived record instead of
waiting for a human review queue. It creates an automatic/provisional layer,
not a claim that every parser output is scientifically verified.
"""

from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "automatic_literature_database_20260828_v1"
ANCHOR_PATH = ROOT / "outputs" / "zotero_tpp_literature_pilot_20260828" / "evidence" / "evidence_anchor_candidates.csv"
NUMERIC_PATH = ROOT / "outputs" / "literature_fulltext_review_20260828_v1" / "two_photon_evidence_skill_p1_v2" / "evidence_value_candidates.csv"
DECISION_PATH = ROOT / "outputs" / "literature_fulltext_review_20260828_v1" / "two_photon_evidence_skill_p1_v2" / "extraction_decision.csv"
CONTEXT_PATH = ROOT / "outputs" / "literature_fulltext_review_20260828_v1" / "two_photon_evidence_skill_p1_v2" / "series_context.csv"
SOURCE_PATH = ROOT / "literature_knowledge" / "source_registry.csv"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def relative_path(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    candidate = Path(text)
    try:
        return candidate.resolve().relative_to(ROOT).as_posix()
    except (OSError, ValueError):
        return candidate.name if candidate.is_absolute() else text.replace("\\", "/")


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def clean_row(row: dict[str, Any], path_fields: Iterable[str] = ()) -> dict[str, Any]:
    result = dict(row)
    for field in path_fields:
        if field in result:
            result[field] = relative_path(result[field])
    return result


def build_automatic_numeric_rows(
    numeric_rows: list[dict[str, str]], decision_rows: list[dict[str, str]]
) -> list[dict[str, Any]]:
    decisions = {row.get("candidate_id", ""): row for row in decision_rows}
    output: list[dict[str, Any]] = []
    for row in numeric_rows:
        item = clean_row(row)
        decision = decisions.get(row.get("candidate_id", ""), {})
        machine_decision = decision.get("decision", "")
        field_type = row.get("candidate_field_type", "")
        raw_value = row.get("raw_value", "").strip()
        raw_unit = row.get("raw_unit", "").strip()
        anchor = row.get("evidence_anchor", "").strip()
        if machine_decision == "auto_accept":
            automatic_status = "auto_provisional_accept"
            automatic_use = "automatic_numeric_candidate" if field_type in {"sigma2", "PI_loading", "threshold"} else "automatic_context_candidate"
            confidence = "machine_high" if raw_value and raw_unit and anchor else "machine_medium"
        elif field_type in {"series_context", "voxel_validation"}:
            automatic_status = "auto_retained_context_candidate"
            automatic_use = "automatic_context_or_validation_candidate"
            confidence = "machine_medium" if anchor else "machine_low"
        else:
            automatic_status = "auto_retained_low_context_candidate"
            automatic_use = "automatic_candidate_with_context_warning"
            confidence = "machine_low" if not raw_value or not raw_unit else "machine_medium"
        item.update(
            {
                "automatic_status": automatic_status,
                "automatic_use_class": automatic_use,
                "automatic_confidence": confidence,
                "automatic_gate_decision": machine_decision or "no_decision_record",
                "automatic_gate_reason": decision.get("reject_reason", "") or decision.get("gate_notes", ""),
            }
        )
        output.append(item)
    return output


def build_automatic_decision_rows(decision_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    output = []
    for row in decision_rows:
        item = dict(row)
        decision = row.get("decision", "")
        if decision == "auto_accept":
            item["automatic_action"] = "retain_as_auto_provisional"
        else:
            item["automatic_action"] = "retain_as_auto_candidate_with_warning"
        item["automatic_review_required_flag"] = "no_workflow_block"
        output.append(item)
    return output


def make_source_summary(
    anchors: list[dict[str, Any]], numeric: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "source_id": "",
            "doi": "",
            "title": "",
            "anchor_candidate_count": 0,
            "numeric_candidate_count": 0,
            "auto_provisional_count": 0,
            "context_candidate_count": 0,
            "low_context_candidate_count": 0,
        }
    )
    for row in anchors:
        key = row.get("paper_id", "")
        item = summary[key]
        item["source_id"] = key
        item["doi"] = row.get("doi", "")
        item["title"] = row.get("title", "")
        item["anchor_candidate_count"] += 1
    for row in numeric:
        key = row.get("source_id", "")
        item = summary[key]
        item["source_id"] = key
        item["doi"] = row.get("doi", "")
        item["title"] = row.get("title", "")
        item["numeric_candidate_count"] += 1
        status = row.get("automatic_status", "")
        if status == "auto_provisional_accept":
            item["auto_provisional_count"] += 1
        elif status == "auto_retained_context_candidate":
            item["context_candidate_count"] += 1
        else:
            item["low_context_candidate_count"] += 1
    return sorted(summary.values(), key=lambda row: (row["source_id"], row["doi"]))


def sqlite_type(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        return "TEXT"
    if field.endswith("_count") or field in {"page_hint", "year"}:
        try:
            int(text)
            return "INTEGER"
        except ValueError:
            return "TEXT"
    return "TEXT"


def create_table(conn: sqlite3.Connection, table: str, rows: list[dict[str, Any]], extra_fields: list[str] | None = None) -> list[str]:
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    for field in extra_fields or []:
        if field not in fields:
            fields.append(field)
    if not fields:
        fields = ["record_id"]
    type_map: dict[str, str] = {}
    for field in fields:
        values = [row.get(field, "") for row in rows]
        type_map[field] = next((sqlite_type(value, field) for value in values if str(value or "").strip()), "TEXT")
    sql_fields = ", ".join('"' + field.replace('"', '""') + '" ' + type_map[field] for field in fields)
    conn.execute(f'CREATE TABLE "{table}" (db_row_id INTEGER PRIMARY KEY AUTOINCREMENT, {sql_fields})')
    if rows:
        placeholders = ",".join("?" for _ in fields)
        conn.executemany(
            f'INSERT INTO "{table}" ({",".join(chr(34) + field + chr(34) for field in fields)}) VALUES ({placeholders})',
            [[row.get(field, "") for field in fields] for row in rows],
        )
    return fields


def main() -> int:
    required = [ANCHOR_PATH, NUMERIC_PATH, DECISION_PATH, CONTEXT_PATH]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing automatic input: " + "; ".join(missing))
    if OUT.exists():
        raise FileExistsError(f"Output directory already exists: {OUT}")
    OUT.mkdir(parents=True)

    anchors = [clean_row(row, ("source_text_path",)) for row in read_csv(ANCHOR_PATH)]
    numeric_raw = read_csv(NUMERIC_PATH)
    decisions_raw = read_csv(DECISION_PATH)
    contexts = [clean_row(row, ("source_text_path",)) for row in read_csv(CONTEXT_PATH)]
    numeric = build_automatic_numeric_rows(numeric_raw, decisions_raw)
    decisions = build_automatic_decision_rows(decisions_raw)
    summary_rows = make_source_summary(anchors, numeric)

    anchor_fields = list(anchors[0]) if anchors else ["record_id"]
    numeric_fields = list(numeric[0]) if numeric else ["record_id"]
    decision_fields = list(decisions[0]) if decisions else ["record_id"]
    context_fields = list(contexts[0]) if contexts else ["record_id"]
    summary_fields = list(summary_rows[0]) if summary_rows else ["source_id"]

    write_csv(OUT / "automated_anchor_candidates.csv", anchors, anchor_fields)
    write_csv(OUT / "automated_numeric_candidates.csv", numeric, numeric_fields)
    write_csv(OUT / "automated_extraction_decisions.csv", decisions, decision_fields)
    write_csv(OUT / "automated_series_context.csv", contexts, context_fields)
    provisional = [
        row for row in numeric
        if row.get("automatic_status") == "auto_provisional_accept"
        and row.get("candidate_field_type") in {"sigma2", "PI_loading", "threshold"}
    ]
    provisional_fields = list(provisional[0]) if provisional else numeric_fields
    write_csv(OUT / "automatic_provisional_numeric.csv", provisional, provisional_fields)
    write_csv(OUT / "automatic_source_summary.csv", summary_rows, summary_fields)

    conn = sqlite3.connect(OUT / "automatic_literature_database.sqlite")
    try:
        conn.execute("CREATE TABLE database_metadata (metadata_key TEXT PRIMARY KEY, metadata_value TEXT NOT NULL)")
        metadata = {
            "database_name": "automatic_two_photon_photoinitiator_literature",
            "database_version": "2026-08-28.auto-v1",
            "built_at": now_iso(),
            "workflow_mode": "fully_automatic_no_manual_stop",
            "scientific_status": "machine_provisional_not_human_verified",
            "source_policy": "all machine candidates retained; no candidate silently discarded",
        }
        conn.executemany("INSERT INTO database_metadata VALUES (?, ?)", metadata.items())
        create_table(conn, "automated_anchor_candidates", anchors)
        create_table(conn, "automated_numeric_candidates", numeric)
        create_table(conn, "automated_extraction_decisions", decisions)
        create_table(conn, "automated_series_context", contexts)
        create_table(conn, "automatic_provisional_numeric", provisional)
        create_table(conn, "automatic_source_summary", summary_rows)
        conn.execute(
            """CREATE VIEW v_automatic_database_overview AS
               SELECT 'anchor_candidate' AS record_layer, COUNT(*) AS row_count FROM automated_anchor_candidates
               UNION ALL SELECT 'numeric_candidate', COUNT(*) FROM automated_numeric_candidates
               UNION ALL SELECT 'provisional_numeric', COUNT(*) FROM automatic_provisional_numeric
               UNION ALL SELECT 'series_context', COUNT(*) FROM automated_series_context"""
        )
        conn.execute("CREATE INDEX idx_auto_numeric_source ON automated_numeric_candidates(source_id)")
        conn.execute("CREATE INDEX idx_auto_numeric_status ON automated_numeric_candidates(automatic_status)")
        conn.commit()
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    finally:
        conn.close()

    status_counts = Counter(row.get("automatic_status", "") for row in numeric)
    field_counts = Counter(row.get("candidate_field_type", "") for row in numeric)
    summary = {
        "database_name": "automatic_two_photon_photoinitiator_literature",
        "database_version": "2026-08-28.auto-v1",
        "workflow_mode": "fully_automatic_no_manual_stop",
        "input_files": {
            "anchor_candidates": ANCHOR_PATH.relative_to(ROOT).as_posix(),
            "numeric_candidates": NUMERIC_PATH.relative_to(ROOT).as_posix(),
            "extraction_decisions": DECISION_PATH.relative_to(ROOT).as_posix(),
            "series_context": CONTEXT_PATH.relative_to(ROOT).as_posix(),
        },
        "input_sha256": {path.name: sha256_file(path) for path in required},
        "counts": {
            "source_papers_with_anchor_candidates": len({row.get("paper_id", "") for row in anchors}),
            "anchor_candidates": len(anchors),
            "numeric_candidates": len(numeric),
            "automatic_provisional_numeric": len(provisional),
            "series_context_records": len(contexts),
            "extraction_decision_records": len(decisions),
        },
        "numeric_field_counts": dict(sorted(field_counts.items())),
        "automatic_status_counts": dict(sorted(status_counts.items())),
        "sqlite_integrity_check": integrity,
        "scientific_boundary": "This is a machine-provisional acquisition database. It is suitable for automated retrieval, triage, and provisional model input generation, but not by itself proof that every value is chemically or experimentally correct.",
    }
    (OUT / "automatic_database_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(
        "# 全自动光引发剂文献证据数据库\n\n"
        "版本：2026-08-28.auto-v1\n\n"
        "本库采用全自动模式，不设置人工复核阻塞步骤。机器发现的候选、数值、实验上下文和自动闸门理由全部直接入库；不足的上下文不会被删除，而是保留为带警告的候选。\n\n"
        f"本次收录 {len(anchors)} 条文献证据锚点、{len(numeric)} 条数值候选、{len(provisional)} 条自动暂定数值记录和 {len(contexts)} 条来源上下文记录。\n\n"
        "## 文件\n\n"
        "- `automatic_literature_database.sqlite`：自动数据库主文件。\n"
        "- `automated_anchor_candidates.csv`：机器从40篇全文中发现的证据锚点。\n"
        "- `automated_numeric_candidates.csv`：双光子吸收截面、用量、阈值、上下文和尺寸等数值候选。\n"
        "- `automatic_provisional_numeric.csv`：机器按已有确定性规则暂时接受的数值候选。\n"
        "- `automated_extraction_decisions.csv`：机器闸门结果和自动处理动作；不产生人工任务。\n"
        "- `automated_series_context.csv`：波长、树脂、光源和加工条件等上下文。\n"
        "- `automatic_source_summary.csv`：按来源汇总的自动采集量。\n"
        "- `automatic_database_summary.json`：计数、输入文件校验和与状态分布。\n\n"
        "## 自动状态含义\n\n"
        "- `auto_provisional_accept`：机器有原始数值和单位，暂时作为自动候选输出。\n"
        "- `auto_retained_context_candidate`：机器保留为条件或尺寸候选，不当作分子固有数值。\n"
        "- `auto_retained_low_context_candidate`：机器保留，但原文上下文不足，仍可供检索和后续模型筛选使用。\n\n"
        "## 研究边界\n\n"
        "全自动意味着不需要研究者逐条确认，而不意味着解析器不会产生标签错配、单位误读或把背景数字识别成目标数值。因此，本库适合自动检索、候选排序和模型输入准备；若用于论文最终定量表，应在论文中声明其为机器采集数据，并保留自动状态与原文锚点。\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
