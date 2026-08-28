"""Build the automatic literature field-evidence registry and CSV supplements."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "outputs" / "zotero_tpp_literature_pilot_20260828"
OUT = BASE / "automatic_field_evidence"
ANCHOR_PATH = BASE / "evidence" / "evidence_anchor_candidates.csv"
NUMERIC_PATH = ROOT / "outputs" / "literature_fulltext_review_20260828_v1" / "two_photon_evidence_skill_p1_v2" / "evidence_value_candidates.csv"
DECISION_PATH = ROOT / "outputs" / "literature_fulltext_review_20260828_v1" / "two_photon_evidence_skill_p1_v2" / "extraction_decision.csv"

FIELD_MAP = {
    "sigma2": "sigma_2pa",
    "PI_loading": "pi_loading",
    "threshold": "polymerization_threshold",
    "series_context": "experimental_context",
    "voxel_validation": "voxel_geometry",
    "isc_t1": "isc_t1_proxy",
    "mechanism": "mechanism",
    "voxel_geometry": "voxel_geometry",
}

REGISTRY_FIELDS = [
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
]

SUPPLEMENT_FIELDS = [
    "supplement_id",
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
    "normalization_basis",
    "extraction_mode",
    "automatic_status",
    "automatic_confidence",
    "automatic_gate_decision",
    "automatic_gate_reason",
    "source_record_id",
]


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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def automatic_state(decision: dict[str, str], row: dict[str, str]) -> tuple[str, str, str]:
    decision_value = decision.get("decision", "")
    field = row.get("candidate_field_type", "")
    raw_value = row.get("raw_value", "").strip()
    raw_unit = row.get("raw_unit", "").strip()
    anchor = row.get("evidence_anchor", "").strip()
    if decision_value == "auto_accept":
        status = "auto_provisional_accept"
        use = "automatic_numeric_candidate" if field in {"sigma2", "PI_loading", "threshold"} else "automatic_context_candidate"
        confidence = "machine_high" if raw_value and raw_unit and anchor else "machine_medium"
    elif field in {"series_context", "voxel_validation"}:
        status = "auto_retained_context_candidate"
        use = "automatic_context_or_validation_candidate"
        confidence = "machine_medium" if anchor else "machine_low"
    else:
        status = "auto_retained_low_context_candidate"
        use = "automatic_candidate_with_context_warning"
        confidence = "machine_medium" if raw_value and raw_unit else "machine_low"
    return status, use, confidence


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build automatic literature field-evidence registry.")
    parser.add_argument(
        "--additional-anchor",
        action="append",
        type=Path,
        default=[],
        help="Additional machine-mined anchor CSVs to merge with the pilot anchor CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUT,
        help="Versioned output directory. Relative paths are resolved from the project root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    anchor_paths = [ANCHOR_PATH] + [path if path.is_absolute() else ROOT / path for path in args.additional_anchor]
    required = anchor_paths + [NUMERIC_PATH, DECISION_PATH]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing automatic field-evidence input: " + "; ".join(missing))
    if output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    anchors: list[dict[str, str]] = []
    seen_anchor_ids: set[str] = set()
    for anchor_path in anchor_paths:
        for row in read_csv(anchor_path):
            anchor_id = row.get("anchor_id", "")
            if anchor_id and anchor_id in seen_anchor_ids:
                continue
            if anchor_id:
                seen_anchor_ids.add(anchor_id)
            anchors.append(row)
    numeric = read_csv(NUMERIC_PATH)
    decisions = {row.get("candidate_id", ""): row for row in read_csv(DECISION_PATH)}
    registry: list[dict[str, Any]] = []

    for row in anchors:
        value_type = row.get("value_type", "")
        registry.append({
            "evidence_id": row.get("anchor_id", ""),
            "source_id": row.get("paper_id", ""),
            "zotero_key": row.get("zotero_key", ""),
            "doi": row.get("doi", ""),
            "title": row.get("title", ""),
            "field_name": FIELD_MAP.get(value_type, value_type),
            "raw_value": row.get("raw_value", ""),
            "raw_unit": row.get("raw_unit", ""),
            "normalized_value": "",
            "normalized_unit": "",
            "page_hint": row.get("page_hint", ""),
            "evidence_anchor": row.get("evidence_anchor", ""),
            "local_context": row.get("evidence_anchor", ""),
            "formulation": "",
            "wavelength_nm": "",
            "figure_or_table": "",
            "data_role": "anchor_candidate",
            "evidence_lane": "machine_text_anchor",
            "confidence_class": row.get("confidence_class", "candidate_only"),
            "automatic_status": "auto_anchor_candidate",
            "automatic_use": "automatic_field_discovery",
            "source_layer": "anchor_mining",
            "source_record_id": row.get("anchor_id", ""),
            "source_text_path": relative_path(row.get("source_text_path", "")),
            "automatic_reason": "Keyword/field anchor mined from parsed full text; value extraction was not independently asserted.",
            "notes": row.get("audit_status", ""),
        })

    supplement: list[dict[str, Any]] = []
    for index, row in enumerate(numeric, 1):
        decision = decisions.get(row.get("candidate_id", ""), {})
        status, use, confidence = automatic_state(decision, row)
        registry.append({
            "evidence_id": row.get("candidate_id", ""),
            "source_id": row.get("source_id", ""),
            "zotero_key": "",
            "doi": row.get("doi", ""),
            "title": row.get("title", ""),
            "field_name": FIELD_MAP.get(row.get("candidate_field_type", ""), row.get("candidate_field_type", "")),
            "raw_value": row.get("raw_value", ""),
            "raw_unit": row.get("raw_unit", ""),
            "normalized_value": row.get("normalized_value", ""),
            "normalized_unit": row.get("normalized_unit", ""),
            "page_hint": row.get("page_hint", ""),
            "evidence_anchor": row.get("evidence_anchor", ""),
            "local_context": row.get("local_context", ""),
            "formulation": "",
            "wavelength_nm": "",
            "figure_or_table": "",
            "data_role": "numeric_candidate" if row.get("candidate_field_type") in {"sigma2", "PI_loading", "threshold"} else "context_candidate",
            "evidence_lane": "machine_numeric_extraction",
            "confidence_class": confidence,
            "automatic_status": status,
            "automatic_use": use,
            "source_layer": "two_photon_numeric_extraction",
            "source_record_id": row.get("candidate_id", ""),
            "source_text_path": "",
            "automatic_reason": decision.get("reject_reason", "") or decision.get("gate_notes", "") or "deterministic automatic extraction rule",
            "notes": row.get("parser_note", ""),
        })
        supplement.append({
            "supplement_id": f"SUP-AUTO-{index:06d}",
            "source_id": row.get("source_id", ""),
            "zotero_key": "",
            "doi": row.get("doi", ""),
            "title": row.get("title", ""),
            "field_name": FIELD_MAP.get(row.get("candidate_field_type", ""), row.get("candidate_field_type", "")),
            "raw_value": row.get("raw_value", ""),
            "raw_unit": row.get("raw_unit", ""),
            "normalized_value": row.get("normalized_value", ""),
            "normalized_unit": row.get("normalized_unit", ""),
            "page_hint": row.get("page_hint", ""),
            "evidence_anchor": row.get("evidence_anchor", ""),
            "local_context": row.get("local_context", ""),
            "normalization_basis": row.get("normalization_basis", ""),
            "extraction_mode": row.get("extraction_mode", ""),
            "automatic_status": status,
            "automatic_confidence": confidence,
            "automatic_gate_decision": decision.get("decision", "no_decision_record"),
            "automatic_gate_reason": decision.get("reject_reason", "") or decision.get("gate_notes", ""),
            "source_record_id": row.get("candidate_id", ""),
        })

    registry.sort(key=lambda row: (row["source_id"], row["field_name"], row["evidence_id"]))
    write_csv(output_dir / "literature_field_evidence_registry.csv", registry, REGISTRY_FIELDS)
    with (output_dir / "literature_field_evidence_registry.jsonl").open("w", encoding="utf-8") as handle:
        for row in registry:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    write_csv(output_dir / "supplementary_literature_field_evidence.csv", registry, REGISTRY_FIELDS)
    write_csv(output_dir / "supplementary_numeric_evidence.csv", supplement, SUPPLEMENT_FIELDS)

    by_source: dict[str, dict[str, Any]] = defaultdict(lambda: {"source_id": "", "doi": "", "title": "", "record_count": 0, "anchor_count": 0, "numeric_count": 0, "field_names": ""})
    field_sets: dict[str, set[str]] = defaultdict(set)
    for row in registry:
        item = by_source[row["source_id"]]
        item["source_id"] = row["source_id"]
        item["doi"] = row["doi"]
        item["title"] = row["title"]
        item["record_count"] += 1
        if row["source_layer"] == "anchor_mining":
            item["anchor_count"] += 1
        else:
            item["numeric_count"] += 1
        field_sets[row["source_id"]].add(row["field_name"])
    for source_id, item in by_source.items():
        item["field_names"] = ";".join(sorted(field_sets[source_id]))
    coverage = sorted(by_source.values(), key=lambda row: (row["source_id"], row["doi"]))
    write_csv(output_dir / "literature_field_coverage.csv", coverage, ["source_id", "doi", "title", "record_count", "anchor_count", "numeric_count", "field_names"])

    status_counts = Counter(row["automatic_status"] for row in registry)
    field_counts = Counter(row["field_name"] for row in registry)
    summary = {
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "workflow_mode": "fully_automatic_field_evidence_extraction",
        "registry_record_count": len(registry),
        "anchor_record_count": len(anchors),
        "numeric_record_count": len(numeric),
        "supplementary_numeric_record_count": len(supplement),
        "source_count_with_records": len(by_source),
        "automatic_status_counts": dict(sorted(status_counts.items())),
        "field_counts": dict(sorted(field_counts.items())),
        "input_sha256": {relative_path(path): sha256_file(path) for path in required},
        "output_files": [
            "literature_field_evidence_registry.csv",
            "literature_field_evidence_registry.jsonl",
            "supplementary_literature_field_evidence.csv",
            "supplementary_numeric_evidence.csv",
            "literature_field_coverage.csv",
            "automatic_field_evidence_summary.json",
            "README.md",
        ],
        "claim_boundary": "All records are automatic extraction candidates. They are suitable for database expansion and automated downstream processing, but automatic status does not mean human-verified experimental truth.",
    }
    (output_dir / "automatic_field_evidence_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    (output_dir / "README.md").write_text(
        "# 全自动文献字段证据注册表\n\n"
        "本目录只做一件事：把解析后的文献字段证据和数值候选自动整理成原有研究可以继续使用的 JSONL/CSV 文件。流程不设置人工复核步骤。\n\n"
        f"本次生成 {len(registry)} 条字段证据记录，其中 {len(anchors)} 条来自全文字段锚点，{len(numeric)} 条来自数值候选抽取；补充数值 CSV 共 {len(supplement)} 条。\n\n"
        "## 主要文件\n\n"
        "- `literature_field_evidence_registry.jsonl`：逐条字段证据的机器交换格式，每行一条记录。\n"
        "- `literature_field_evidence_registry.csv`：同一注册表的表格格式。\n"
        "- `supplementary_literature_field_evidence.csv`：可作为补充材料的完整字段证据表。\n"
        "- `supplementary_numeric_evidence.csv`：可作为补充材料的数值和实验条件表。\n"
        "- `literature_field_coverage.csv`：按文献汇总字段覆盖情况。\n"
        "- `automatic_field_evidence_summary.json`：记录数量、字段分布、输入校验和。\n\n"
        "## 字段范围\n\n"
        "包括双光子吸收截面、光引发剂用量、聚合阈值候选、实验条件、体素/线宽信息、三重态/系间窜越线索和光引发机理线索。缺失数值保持为空，不用程序补写。\n\n"
        "## 说明\n\n"
        "这是自动采集层，不是人工核验层。它可以直接扩充原有文献数据库和生成补充 CSV；后续模型或统计程序应同时读取 `automatic_status`、`confidence_class` 和 `automatic_reason`。\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
