#!/usr/bin/env python3
"""Build a versioned, auditable photoinitiator literature-prior database.

The builder is intentionally read-only with respect to all upstream assets. It
keeps verified registries separate from legacy/MinerU machine extractions and
does not import candidate-screening, model-prediction, external-validation or
quantum-chemistry result tables.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePath
from typing import Any, Iterable, Sequence


SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[1]
DEFAULT_CONFIG = REPO_ROOT / "configs" / "literature_prior_database.json"

EXPECTED_TASKS = (
    "sigma_780",
    "sigma_max",
    "toxicity",
    "solubility",
    "synthetic_accessibility",
    "isc_energy",
)

TABLE_DESCRIPTIONS = {
    "literature_source": "已核验文献来源；每行代表一篇可追溯来源。",
    "domain_prior_rule": "从文献证据规范化得到的领域先验规则。",
    "endpoint_and_representation_prior": "六项性质及分子输入表示、变换和缺失值规则。",
    "mechanism_prior_rule": "按光引发机理通道组织的判定与声明边界。",
    "synthesis_route_prior": "按反应家族组织的合成路线先例。",
    "local_source_evidence": "人工回到原文核实的证据锚点。",
    "task_weight_derivation": "任务权重从文献字段池到最终策略的推导步骤。",
    "task_weight_policy": "六任务权重策略；属于研究决策，不属于实验事实。",
    "task_weight_node_disclosure": "权重推导过程中自动节点和回退路径的披露。",
    "literature_package_completeness": "知识包完整性审计。",
    "legacy_paper_extract": "旧版机器提取的论文级摘要，仅用于回溯和复核。",
    "legacy_paper_extract_statement": "旧版机器提取拆分出的陈述项，均未自动核验。",
    "mineru_molecule_observation": "MinerU识别的结构对象，处于待复核区。",
    "mineru_visual_observation": "MinerU识别的图、表、公式和路线图，处于待复核区。",
    "mineru_reaction_observation": "MinerU明确解析的反应对象，处于待复核区。",
    "mineru_review_queue": "需要人工回源确认的自动提取对象。",
    "literature_fulltext_review_queue": "优先文献的全文回源、证据锚点和升级判断队列。",
    "literature_evidence_block": "全文中的候选证据块，保留原文定位但尚未完成科学核验。",
    "literature_numeric_evidence_candidate": "双光子数值候选及其原始单位、上下文和证据定位。",
    "literature_numeric_review_queue": "双光子数值候选的人工复核任务和严格闸门结果。",
    "literature_source_readiness_summary": "按来源汇总数值证据可用性和阻塞原因。",
    "literature_targeted_source_audit": "针对单篇全文来源的定向证据审计及其声明边界。",
    "evidence_boundary": "不同证据类型的使用权限和声明上限。",
    "dataset_catalog": "主库所含数据集及其记录单位、用途和边界。",
    "asset_registry": "每个输入文件的校验和、记录数和导入状态。",
    "field_dictionary": "数据库字段与原始字段的映射及中文含义。",
}

FIELD_DESCRIPTIONS = {
    "source_id": "稳定的文献来源编号。",
    "source_doi": "文献数字对象标识符。",
    "doi": "文献数字对象标识符。",
    "title": "文献题名。",
    "source_title": "文献题名。",
    "year": "发表年份。",
    "status": "记录当前状态。",
    "evidence_level": "证据强度或与目标问题的接近程度。",
    "claim_limit": "该记录允许支持的最高声明范围。",
    "normalized_rule": "由来源证据规范化得到、可供计算流程执行或审查的规则。",
    "computational_use": "该先验知识在计算流程中的用途。",
    "downstream_use": "该记录预定的后续使用位置。",
    "machine_readable_field": "程序使用的性质字段名。",
    "human_readable_name": "便于读者理解的性质或对象名称。",
    "definition": "对象的正式定义。",
    "normalized_mt6_weight": "六任务内部归一化权重，六项之和应为1。",
    "chemprop_scaled_weight": "供训练配置使用的等比例权重，六项之和应接近6。",
    "review_status": "人工复核状态。",
    "source_locator": "页码和版面坐标等原文定位信息。",
    "canonical_smiles": "规范化的一行式分子结构字符串。",
    "audit_id": "定向来源审计记录编号。",
    "pi_label": "文献中使用的光引发剂标签。",
    "value_type": "候选记录对应的证据类型。",
    "raw_value": "原文或表格中的原始数值表达。",
    "raw_unit": "原始单位。",
    "normalized_value": "在保留原始上下文后的规范化数值或边界表达。",
    "normalized_unit": "规范化单位。",
    "context_lock": "必须随数值一同保留的实验条件。",
    "figure_or_table": "证据所在图、表或文字位置。",
    "evidence_class": "证据是文字/表格候选、上下文或其他类别的标记。",
    "audit_status": "定向审计的人工签核状态。",
    "allowed_use": "当前状态下允许的研究用途。",
    "limitation": "当前证据的声明限制。",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional output directory. Relative paths are resolved from the repository root.",
    )
    return parser.parse_args()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def q(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def sanitize_identifier(value: str) -> str:
    value = value.strip().replace("/", "_")
    value = re.sub(r"[^0-9A-Za-z_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_").lower()
    if not value:
        value = "field"
    if value[0].isdigit():
        value = "f_" + value
    return value


def unique_columns(headers: Sequence[str]) -> list[str]:
    result: list[str] = []
    seen: Counter[str] = Counter()
    for header in headers:
        base = sanitize_identifier(header)
        seen[base] += 1
        result.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
    return result


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def normalize_doi(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", text)
    text = re.sub(r"^doi:\s*", "", text)
    return text.rstrip(". ")


def normalize_title(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def safe_basename(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return PurePath(text.replace("\\", "/")).name


def sanitize_paths_in_json(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {k: sanitize_paths_in_json(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitize_paths_in_json(v, key) for v in value]
    if isinstance(value, str) and ("path" in key.lower() or "file" in key.lower()):
        if re.match(r"^[A-Za-z]:[\\/]", value) or value.startswith("/"):
            return safe_basename(value)
    return value


def infer_sql_type(values: Iterable[str], column_name: str) -> str:
    nonempty = [str(v).strip() for v in values if v is not None and str(v).strip() != ""]
    if not nonempty:
        return "TEXT"
    text_markers = (
        "id",
        "doi",
        "smiles",
        "status",
        "title",
        "name",
        "rule",
        "scope",
        "summary",
        "source",
        "path",
        "location",
        "type",
        "class",
        "use",
        "role",
        "unit",
        "formula",
        "interpretation",
        "claim",
        "evidence",
        "rationale",
        "handling",
        "transformation",
        "definition",
        "reason",
        "action",
        "field",
        "representation",
        "journal",
    )
    if any(marker in column_name for marker in text_markers):
        return "TEXT"
    try:
        for value in nonempty:
            int(value)
        return "INTEGER"
    except ValueError:
        pass
    try:
        for value in nonempty:
            number = float(value)
            if not math.isfinite(number):
                raise ValueError
        return "REAL"
    except ValueError:
        return "TEXT"


def coerce(value: Any, sql_type: str) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text == "":
        return None
    if sql_type == "INTEGER":
        return int(text)
    if sql_type == "REAL":
        number = float(text)
        return number if math.isfinite(number) else None
    return text


def init_database(conn: sqlite3.Connection, config: dict[str, Any]) -> None:
    conn.executescript(
        """
        PRAGMA foreign_keys = ON;
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE database_metadata (
            metadata_key TEXT PRIMARY KEY,
            metadata_value TEXT NOT NULL
        );

        CREATE TABLE asset_registry (
            asset_id TEXT PRIMARY KEY,
            source_path TEXT NOT NULL,
            source_format TEXT NOT NULL,
            data_layer TEXT NOT NULL,
            target_table TEXT NOT NULL,
            description_cn TEXT NOT NULL,
            required_flag INTEGER NOT NULL,
            import_status TEXT NOT NULL,
            row_count INTEGER,
            file_size_bytes INTEGER,
            sha256 TEXT,
            imported_at TEXT NOT NULL
        );

        CREATE TABLE field_dictionary (
            dictionary_id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            database_field TEXT NOT NULL,
            original_field TEXT,
            sqlite_type TEXT NOT NULL,
            description_cn TEXT NOT NULL,
            data_layer TEXT,
            UNIQUE(table_name, database_field)
        );

        CREATE TABLE evidence_boundary (
            boundary_id TEXT PRIMARY KEY,
            evidence_category_cn TEXT NOT NULL,
            database_layer TEXT NOT NULL,
            manuscript_direct_use INTEGER NOT NULL,
            human_review_required INTEGER NOT NULL,
            meaning_cn TEXT NOT NULL,
            claim_limit_cn TEXT NOT NULL
        );

        CREATE TABLE dataset_catalog (
            dataset_id TEXT PRIMARY KEY,
            dataset_name_cn TEXT NOT NULL,
            table_name TEXT NOT NULL,
            record_unit_cn TEXT NOT NULL,
            input_file_form TEXT NOT NULL,
            database_role_cn TEXT NOT NULL,
            verification_state TEXT NOT NULL,
            row_count INTEGER NOT NULL,
            core_prior_flag INTEGER NOT NULL,
            claim_boundary_cn TEXT NOT NULL
        );
        """
    )

    metadata = {
        "database_name": config["database_name"],
        "database_version": config["database_version"],
        "built_at": now_iso(),
        "builder": SCRIPT_PATH.name,
        "scope": "photoinitiator literature prior knowledge only",
        "excluded_scopes": json.dumps(config.get("excluded_scopes", []), ensure_ascii=False),
    }
    conn.executemany(
        "INSERT INTO database_metadata(metadata_key, metadata_value) VALUES (?, ?)",
        metadata.items(),
    )

    boundaries = [
        (
            "BOUNDARY_VERIFIED_SOURCE",
            "已核验来源元数据",
            "verified_source_metadata",
            1,
            0,
            "题名、数字对象标识符、年份和期刊等可追溯来源信息。",
            "只能证明文献存在和可追溯，不能单独证明某个科学结论。",
        ),
        (
            "BOUNDARY_VERIFIED_PRIOR",
            "可追溯文献先验规则",
            "verified_prior_rule",
            1,
            0,
            "由来源证据规范化形成的性质、结构、机理或路线规则。",
            "应保留证据级别和适用范围；不能把家族级先例写成候选分子级实验证明。",
        ),
        (
            "BOUNDARY_LOCAL_TEXT",
            "人工回源文字证据",
            "verified_source_text_evidence",
            1,
            0,
            "已经回到原文定位的文字证据锚点。",
            "只能支持记录中明确列出的内容及其上下文。",
        ),
        (
            "BOUNDARY_WEIGHT_POLICY",
            "任务权重策略",
            "prior_policy_not_scientific_truth",
            1,
            0,
            "由文献覆盖、研究目标和计算用途共同形成的项目决策。",
            "权重不是实验测量、自然常数或已证明的全局最优比例。",
        ),
        (
            "BOUNDARY_LEGACY_MACHINE",
            "旧版机器提取",
            "unverified_legacy_extraction",
            0,
            1,
            "旧流程产生的自动摘要、陈述和证据项。",
            "未经人工回源不得进入正文事实表或作为定量证据。",
        ),
        (
            "BOUNDARY_MINERU",
            "MinerU自动识别对象",
            "unverified_mineru_staging",
            0,
            1,
            "从文献版面识别出的结构、图、表、公式或反应候选。",
            "解析成功只表示格式可读取，不表示化学结构、标签、数值或机理正确。",
        ),
    ]
    conn.executemany(
        """INSERT INTO evidence_boundary VALUES (?, ?, ?, ?, ?, ?, ?)""",
        boundaries,
    )
    for table_name, description in TABLE_DESCRIPTIONS.items():
        if table_name in {"asset_registry", "field_dictionary", "evidence_boundary", "dataset_catalog"}:
            conn.execute(
                """INSERT OR IGNORE INTO field_dictionary
                   (table_name, database_field, original_field, sqlite_type, description_cn, data_layer)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (table_name, "*", None, "TABLE", description, "database_governance"),
            )


def register_asset(
    conn: sqlite3.Connection,
    asset: dict[str, Any],
    path: Path,
    target_table: str,
    status: str,
    row_count: int | None,
) -> None:
    rel_path = path.resolve().relative_to(REPO_ROOT).as_posix() if path.exists() and REPO_ROOT in path.resolve().parents else path.as_posix()
    conn.execute(
        """INSERT INTO asset_registry
           (asset_id, source_path, source_format, data_layer, target_table,
            description_cn, required_flag, import_status, row_count,
            file_size_bytes, sha256, imported_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            asset["asset_id"],
            rel_path,
            path.suffix.lower().lstrip(".") or "unknown",
            asset["data_layer"],
            target_table,
            asset["description_cn"],
            int(bool(asset.get("required", False))),
            status,
            row_count,
            path.stat().st_size if path.exists() and path.is_file() else None,
            sha256_file(path) if path.exists() and path.is_file() else None,
            now_iso(),
        ),
    )


def add_field_dictionary(
    conn: sqlite3.Connection,
    table: str,
    db_field: str,
    original_field: str | None,
    sql_type: str,
    data_layer: str,
) -> None:
    description = FIELD_DESCRIPTIONS.get(
        db_field,
        f"来自原始字段“{original_field}”的结构化内容。" if original_field else TABLE_DESCRIPTIONS.get(table, "数据库字段。"),
    )
    conn.execute(
        """INSERT OR IGNORE INTO field_dictionary
           (table_name, database_field, original_field, sqlite_type, description_cn, data_layer)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (table, db_field, original_field, sql_type, description, data_layer),
    )


def create_empty_optional_table(conn: sqlite3.Connection, asset: dict[str, Any]) -> None:
    """Create a minimal typed table so optional MinerU staging can be absent."""
    table = sanitize_identifier(asset["table"])
    schemas = {
        "mineru_molecule_observation": [
            ("molecule_record_id", "TEXT"),
            ("source_document", "TEXT"),
            ("source_locator", "TEXT"),
            ("linked_existing_source_id", "TEXT"),
            ("canonical_smiles", "TEXT"),
            ("review_status", "TEXT"),
            ("model_ready_flag", "TEXT"),
        ],
        "mineru_visual_observation": [
            ("visual_record_id", "TEXT"),
            ("source_document", "TEXT"),
            ("source_locator", "TEXT"),
            ("linked_existing_source_id", "TEXT"),
            ("visual_type", "TEXT"),
            ("visual_role", "TEXT"),
            ("review_status", "TEXT"),
        ],
        "mineru_reaction_observation": [
            ("reaction_record_id", "TEXT"),
            ("source_document", "TEXT"),
            ("source_locator", "TEXT"),
            ("linked_existing_source_id", "TEXT"),
            ("review_status", "TEXT"),
        ],
        "mineru_review_queue": [
            ("review_id", "TEXT"),
            ("object_type", "TEXT"),
            ("object_id", "TEXT"),
            ("source_document", "TEXT"),
            ("source_locator", "TEXT"),
            ("review_reason", "TEXT"),
            ("required_action", "TEXT"),
            ("status", "TEXT"),
        ],
        "literature_discovery_candidate": [
            ("candidate_id", "TEXT"),
            ("doi", "TEXT"),
            ("title", "TEXT"),
            ("year", "INTEGER"),
            ("journal", "TEXT"),
            ("discovery_themes", "TEXT"),
            ("relevance_score", "REAL"),
            ("core_source_status", "TEXT"),
            ("scientific_review_status", "TEXT"),
            ("verification_status", "TEXT"),
            ("review_priority", "TEXT"),
        ],
        "literature_priority_candidate": [
            ("candidate_id", "TEXT"),
            ("doi", "TEXT"),
            ("title", "TEXT"),
            ("year", "INTEGER"),
            ("journal", "TEXT"),
            ("discovery_themes", "TEXT"),
            ("relevance_score", "REAL"),
            ("core_source_status", "TEXT"),
            ("scientific_review_status", "TEXT"),
            ("verification_status", "TEXT"),
            ("review_priority", "TEXT"),
        ],
        "literature_fulltext_review_queue": [
            ("review_id", "TEXT"),
            ("review_rank", "INTEGER"),
            ("candidate_id", "TEXT"),
            ("doi", "TEXT"),
            ("title", "TEXT"),
            ("year", "INTEGER"),
            ("journal", "TEXT"),
            ("paper_role", "TEXT"),
            ("local_pdf_status", "TEXT"),
            ("local_text_status", "TEXT"),
            ("retrieval_route", "TEXT"),
            ("doi_resolution_status", "TEXT"),
            ("bibliographic_status", "TEXT"),
            ("abstract_screen_status", "TEXT"),
            ("evidence_anchor_status", "TEXT"),
            ("promotion_decision", "TEXT"),
            ("review_priority", "TEXT"),
            ("required_review_action", "TEXT"),
            ("review_notes", "TEXT"),
        ],
        "literature_evidence_block": [
            ("evidence_id", "TEXT"),
            ("run_id", "TEXT"),
            ("source_id", "TEXT"),
            ("doi", "TEXT"),
            ("title", "TEXT"),
            ("block_type", "TEXT"),
            ("page_hint", "TEXT"),
            ("primary_role", "TEXT"),
            ("source_text_path", "TEXT"),
        ],
        "literature_numeric_evidence_candidate": [
            ("candidate_id", "TEXT"),
            ("evidence_id", "TEXT"),
            ("source_id", "TEXT"),
            ("candidate_field_type", "TEXT"),
            ("raw_value", "TEXT"),
            ("raw_unit", "TEXT"),
            ("page_hint", "TEXT"),
            ("evidence_anchor", "TEXT"),
            ("confidence_class", "TEXT"),
        ],
        "literature_numeric_review_queue": [
            ("candidate_id", "TEXT"),
            ("source_id", "TEXT"),
            ("candidate_field_type", "TEXT"),
            ("decision", "TEXT"),
            ("readiness_level", "TEXT"),
            ("reject_reason", "TEXT"),
            ("evidence_anchor", "TEXT"),
        ],
        "literature_source_readiness_summary": [
            ("source_id", "TEXT"),
            ("doi", "TEXT"),
            ("title", "TEXT"),
            ("source_readiness", "TEXT"),
            ("blocking_reason", "TEXT"),
            ("next_action", "TEXT"),
        ],
        "literature_targeted_source_audit": [
            ("audit_id", "TEXT"),
            ("review_id", "TEXT"),
            ("source_id", "TEXT"),
            ("doi", "TEXT"),
            ("pi_label", "TEXT"),
            ("value_type", "TEXT"),
            ("raw_value", "TEXT"),
            ("raw_unit", "TEXT"),
            ("normalized_value", "TEXT"),
            ("normalized_unit", "TEXT"),
            ("context_lock", "TEXT"),
            ("page_hint", "TEXT"),
            ("figure_or_table", "TEXT"),
            ("evidence_anchor", "TEXT"),
            ("evidence_class", "TEXT"),
            ("audit_status", "TEXT"),
            ("allowed_use", "TEXT"),
            ("limitation", "TEXT"),
        ],
    }
    columns = schemas.get(table, [])
    column_sql = ", ".join(f"{q(name)} {sql_type}" for name, sql_type in columns)
    suffix = f", {column_sql}" if column_sql else ""
    conn.execute(
        f"""CREATE TABLE {q(table)} (
            db_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL
            {suffix},
            FOREIGN KEY(asset_id) REFERENCES asset_registry(asset_id)
        )"""
    )
    add_field_dictionary(conn, table, "db_row_id", None, "INTEGER", asset["data_layer"])
    add_field_dictionary(conn, table, "asset_id", None, "TEXT", asset["data_layer"])
    for name, sql_type in columns:
        add_field_dictionary(conn, table, name, name, sql_type, asset["data_layer"])


def import_csv_asset(conn: sqlite3.Connection, asset: dict[str, Any]) -> int:
    path = (REPO_ROOT / asset["path"]).resolve()
    table = sanitize_identifier(asset["table"])
    if not path.exists():
        if asset.get("required", False):
            raise FileNotFoundError(f"Required asset is missing: {asset['path']}")
        register_asset(conn, asset, path, table, "optional_missing", None)
        create_empty_optional_table(conn, asset)
        return 0

    with path.open("r", encoding="utf-8-sig", newline="", errors="replace") as handle:
        reader = csv.DictReader(handle)
        original_headers = reader.fieldnames or []
        rows = list(reader)

    db_headers = unique_columns(original_headers)
    types = {
        db_name: infer_sql_type((row.get(original, "") for row in rows), db_name)
        for original, db_name in zip(original_headers, db_headers)
    }

    column_sql = ",\n            ".join(f"{q(name)} {types[name]}" for name in db_headers)
    conn.execute(
        f"""CREATE TABLE {q(table)} (
            db_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            {column_sql},
            FOREIGN KEY(asset_id) REFERENCES asset_registry(asset_id)
        )"""
        if db_headers
        else f"""CREATE TABLE {q(table)} (
            db_row_id INTEGER PRIMARY KEY AUTOINCREMENT,
            asset_id TEXT NOT NULL,
            FOREIGN KEY(asset_id) REFERENCES asset_registry(asset_id)
        )"""
    )

    register_asset(conn, asset, path, table, "imported", len(rows))
    add_field_dictionary(conn, table, "db_row_id", None, "INTEGER", asset["data_layer"])
    add_field_dictionary(conn, table, "asset_id", None, "TEXT", asset["data_layer"])
    for original, db_name in zip(original_headers, db_headers):
        add_field_dictionary(conn, table, db_name, original, types[db_name], asset["data_layer"])

    if rows and db_headers:
        placeholders = ", ".join("?" for _ in range(len(db_headers) + 1))
        columns = ", ".join(q(name) for name in ["asset_id", *db_headers])
        insert_sql = f"INSERT INTO {q(table)} ({columns}) VALUES ({placeholders})"
        payload = []
        for row in rows:
            values = [asset["asset_id"]]
            for original, db_name in zip(original_headers, db_headers):
                values.append(coerce(row.get(original), types[db_name]))
            payload.append(values)
        conn.executemany(insert_sql, payload)

    for column in ("source_id", "source_doi", "doi", "knowledge_id", "task", "review_status", "object_id"):
        if column in db_headers:
            conn.execute(f"CREATE INDEX {q(f'idx_{table}_{column}')} ON {q(table)} ({q(column)})")
    if table == "literature_source" and "source_id" in db_headers:
        conn.execute(
            "CREATE UNIQUE INDEX idx_literature_source_source_id_unique "
            "ON literature_source(source_id)"
        )
    return len(rows)


def source_maps(conn: sqlite3.Connection) -> tuple[dict[str, str], dict[str, str]]:
    doi_map: dict[str, str] = {}
    title_map: dict[str, str] = {}
    for row in conn.execute("SELECT source_id, doi, title FROM literature_source"):
        if row[1]:
            doi_map[normalize_doi(row[1])] = row[0]
        if row[2]:
            title_map[normalize_title(row[2])] = row[0]
    return doi_map, title_map


def import_raw_extracts(conn: sqlite3.Connection, asset: dict[str, Any]) -> tuple[int, int]:
    path = (REPO_ROOT / asset["path"]).resolve()
    if not path.exists():
        if asset.get("required", False):
            raise FileNotFoundError(f"Required asset is missing: {asset['path']}")
        register_asset(conn, asset, path, "legacy_paper_extract;legacy_paper_extract_statement", "optional_missing", None)
        return 0, 0

    with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
        raw_lines = [line for line in handle if line.strip()]
    register_asset(
        conn,
        asset,
        path,
        "legacy_paper_extract;legacy_paper_extract_statement",
        "imported_as_unverified_staging",
        len(raw_lines),
    )

    conn.executescript(
        """
        CREATE TABLE legacy_paper_extract (
            extract_id TEXT PRIMARY KEY,
            asset_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            linked_source_id TEXT,
            source_match_status TEXT NOT NULL,
            title TEXT,
            year INTEGER,
            doi_or_url TEXT,
            study_type TEXT,
            article_type TEXT,
            domain_scope_json TEXT,
            confidence_score REAL,
            confidence_label TEXT,
            key_claim_count INTEGER NOT NULL,
            evidence_item_count INTEGER NOT NULL,
            candidate_indicator_count INTEGER NOT NULL,
            limitation_count INTEGER NOT NULL,
            unresolved_point_count INTEGER NOT NULL,
            alignment_conflict_count INTEGER NOT NULL,
            source_file_name TEXT,
            source_file_hash TEXT,
            verification_status TEXT NOT NULL,
            raw_json_sanitized TEXT NOT NULL,
            FOREIGN KEY(asset_id) REFERENCES asset_registry(asset_id),
            FOREIGN KEY(linked_source_id) REFERENCES literature_source(source_id)
        );

        CREATE TABLE legacy_paper_extract_statement (
            statement_id TEXT PRIMARY KEY,
            extract_id TEXT NOT NULL,
            paper_id TEXT NOT NULL,
            statement_type TEXT NOT NULL,
            sequence_number INTEGER NOT NULL,
            topic TEXT,
            claim TEXT,
            support_type TEXT,
            page_number INTEGER,
            section TEXT,
            evidence_strength REAL,
            content_text TEXT,
            content_json TEXT NOT NULL,
            verification_status TEXT NOT NULL,
            FOREIGN KEY(extract_id) REFERENCES legacy_paper_extract(extract_id)
        );
        CREATE INDEX idx_legacy_extract_source ON legacy_paper_extract(linked_source_id);
        CREATE INDEX idx_legacy_statement_paper ON legacy_paper_extract_statement(paper_id);
        CREATE INDEX idx_legacy_statement_type ON legacy_paper_extract_statement(statement_type);
        """
    )

    doi_map, title_map = source_maps(conn)
    extract_count = 0
    statement_count = 0
    for line in raw_lines:
            obj = json.loads(line)
            paper_id = str(obj.get("paper_id") or f"paper-{extract_count + 1}")
            merged = obj.get("alignment", {}).get("merged_extraction", {}) or {}
            bib = merged.get("bibliographic_info", {}) or {}
            title = str(bib.get("title") or "").strip()
            doi_or_url = str(bib.get("doi_or_url") or "").strip()
            linked_source_id = None
            match_status = "unmatched"
            if normalize_doi(doi_or_url) in doi_map:
                linked_source_id = doi_map[normalize_doi(doi_or_url)]
                match_status = "matched_by_doi"
            elif normalize_title(title) in title_map:
                linked_source_id = title_map[normalize_title(title)]
                match_status = "matched_by_exact_normalized_title"
            extract_id = stable_id("PEX", paper_id)
            confidence = merged.get("confidence", {}) or {}
            raw_sanitized = sanitize_paths_in_json(obj)
            statement_groups = {
                "key_claim": merged.get("key_claims", []) or [],
                "evidence_item": merged.get("evidence_items", []) or [],
                "candidate_indicator": merged.get("candidate_indicators", []) or [],
                "limitation": merged.get("limitations", []) or [],
                "unresolved_point": merged.get("unresolved_points", []) or [],
                "alignment_agreement": obj.get("alignment", {}).get("agreement_items", []) or [],
                "alignment_conflict": obj.get("alignment", {}).get("conflict_items", []) or [],
            }
            conn.execute(
                """INSERT INTO legacy_paper_extract VALUES
                   (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    extract_id,
                    asset["asset_id"],
                    paper_id,
                    linked_source_id,
                    match_status,
                    title or None,
                    bib.get("year"),
                    doi_or_url or None,
                    merged.get("study_type"),
                    merged.get("article_type"),
                    json.dumps(merged.get("domain_scope", []), ensure_ascii=False),
                    confidence.get("score"),
                    confidence.get("label"),
                    len(statement_groups["key_claim"]),
                    len(statement_groups["evidence_item"]),
                    len(statement_groups["candidate_indicator"]),
                    len(statement_groups["limitation"]),
                    len(statement_groups["unresolved_point"]),
                    len(statement_groups["alignment_conflict"]),
                    safe_basename(bib.get("file_path")) or None,
                    bib.get("file_hash"),
                    "legacy_machine_extraction_unverified",
                    json.dumps(raw_sanitized, ensure_ascii=False, sort_keys=True),
                ),
            )
            extract_count += 1

            for statement_type, items in statement_groups.items():
                for sequence, item in enumerate(items, start=1):
                    item_obj = item if isinstance(item, dict) else {"value": item}
                    location = item_obj.get("location", {}) if isinstance(item_obj, dict) else {}
                    if not isinstance(location, dict):
                        location = {}
                    content_text = (
                        item_obj.get("short_excerpt_or_paraphrase")
                        or item_obj.get("claim")
                        or item_obj.get("value")
                        or json.dumps(item_obj, ensure_ascii=False)
                    )
                    statement_id = stable_id("PST", f"{paper_id}|{statement_type}|{sequence}|{content_text}")
                    conn.execute(
                        """INSERT INTO legacy_paper_extract_statement VALUES
                           (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            statement_id,
                            extract_id,
                            paper_id,
                            statement_type,
                            sequence,
                            item_obj.get("topic"),
                            item_obj.get("claim"),
                            item_obj.get("support_type"),
                            location.get("page"),
                            location.get("section"),
                            item_obj.get("evidence_strength"),
                            str(content_text),
                            json.dumps(sanitize_paths_in_json(item_obj), ensure_ascii=False, sort_keys=True),
                            "unverified_requires_source_review",
                        ),
                    )
                    statement_count += 1

    for table in ("legacy_paper_extract", "legacy_paper_extract_statement"):
        for column in conn.execute(f"PRAGMA table_info({q(table)})"):
            add_field_dictionary(conn, table, column[1], None, column[2], asset["data_layer"])
    return extract_count, statement_count


def create_views(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE VIEW v_verified_prior_knowledge AS
        SELECT
            knowledge_id AS knowledge_record_id,
            'domain_criterion' AS knowledge_type,
            source_id,
            source_doi,
            source_title,
            normalized_criterion AS topic_or_family,
            normalized_rule AS normalized_prior,
            scientific_rationale AS rationale_or_limit,
            computational_use,
            downstream_use,
            evidence_level,
            status
        FROM domain_prior_rule
        UNION ALL
        SELECT
            mechanism_rule_id,
            'mechanism_routing',
            source_id,
            source_doi,
            source_title,
            family_scope,
            normalized_rule,
            exclusion_or_claim_limit,
            computational_use,
            downstream_use,
            evidence_level,
            status
        FROM mechanism_prior_rule
        UNION ALL
        SELECT
            route_evidence_id,
            'synthesis_route',
            source_id,
            source_doi,
            source_title,
            route_family,
            normalized_route_rule,
            scope_limit,
            computational_use,
            downstream_use,
            route_evidence_class,
            status
        FROM synthesis_route_prior
        UNION ALL
        SELECT
            evidence_id,
            'verified_source_text',
            source_id,
            doi,
            source_title,
            structured_evidence,
            source_text_anchor,
            claim_limit,
            computational_role,
            downstream_use,
            evidence_type,
            status
        FROM local_source_evidence;

        CREATE VIEW v_six_task_prior_dictionary AS
        SELECT
            ep.item_id,
            ep.human_readable_name,
            ep.machine_readable_field AS task,
            ep.definition,
            ep.original_unit,
            ep.training_unit,
            ep.valid_label_count,
            ep.transformation,
            ep.inverse_transformation,
            ep.invalid_value_handling,
            ep.missing_value_rule,
            ep.scientific_rationale,
            ep.normalized_rule,
            tw.normalized_mt6_weight,
            tw.chemprop_scaled_weight,
            tw.cross_paper_support_count,
            tw.support_evidence_ref_count,
            tw.interpretation AS weight_interpretation,
            tw.claim_limit AS weight_claim_limit,
            tw.status AS weight_status
        FROM endpoint_and_representation_prior ep
        LEFT JOIN task_weight_policy tw
          ON ep.machine_readable_field = tw.task
        WHERE ep.item_type = 'endpoint'
          AND ep.machine_readable_field IN
              ('sigma_780', 'sigma_max', 'toxicity', 'solubility', 'synthetic_accessibility', 'isc_energy');

        CREATE VIEW v_source_evidence_coverage AS
        SELECT
            s.source_id,
            s.doi,
            s.title,
            s.year,
            s.journal,
            s.topic_scope,
            (SELECT COUNT(*) FROM domain_prior_rule d WHERE d.source_id = s.source_id) AS direct_domain_rule_count,
            (SELECT COUNT(*) FROM mechanism_prior_rule m WHERE m.source_id = s.source_id) AS direct_mechanism_rule_count,
            (SELECT COUNT(*) FROM synthesis_route_prior r WHERE r.source_id = s.source_id) AS direct_route_evidence_count,
            (SELECT COUNT(*) FROM local_source_evidence l WHERE l.source_id = s.source_id) AS verified_text_anchor_count,
            (SELECT COUNT(*) FROM legacy_paper_extract p WHERE p.linked_source_id = s.source_id) AS linked_legacy_extract_count,
            CASE WHEN EXISTS (
                SELECT 1 FROM mineru_molecule_observation mm
                WHERE mm.linked_existing_source_id = s.source_id
            ) OR EXISTS (
                SELECT 1 FROM mineru_visual_observation mv
                WHERE mv.linked_existing_source_id = s.source_id
            ) THEN 1 ELSE 0 END AS has_mineru_staging_objects,
            s.metadata_status,
            s.status
        FROM literature_source s;

        CREATE VIEW v_mechanism_prior AS
        SELECT * FROM mechanism_prior_rule;

        CREATE VIEW v_synthesis_route_prior AS
        SELECT * FROM synthesis_route_prior;

        CREATE VIEW v_task_weight_prior AS
        SELECT
            weight_id,
            task_order,
            task,
            normalized_mt6_weight,
            chemprop_scaled_weight,
            cross_paper_support_count,
            support_evidence_ref_count,
            computational_use,
            interpretation,
            claim_limit,
            status
        FROM task_weight_policy;

        CREATE VIEW v_unverified_extraction_review AS
        SELECT
            'legacy_statement' AS object_source,
            statement_id AS object_id,
            paper_id AS document_or_paper_id,
            statement_type AS object_type,
            content_text AS content_or_reason,
            verification_status AS review_status
        FROM legacy_paper_extract_statement
        UNION ALL
        SELECT
            'mineru_review_queue',
            object_id,
            source_document,
            object_type,
            review_reason,
            status
        FROM mineru_review_queue;

        CREATE VIEW v_literature_discovery_candidates AS
        SELECT
            candidate_id,
            doi,
            title,
            year,
            journal,
            discovery_themes,
            relevance_score,
            core_source_status,
            scientific_review_status,
            verification_status,
            review_priority
        FROM literature_discovery_candidate;

        CREATE VIEW v_literature_priority_candidates AS
        SELECT * FROM literature_priority_candidate;

        CREATE VIEW v_database_overview AS
        SELECT * FROM dataset_catalog ORDER BY core_prior_flag DESC, dataset_id;
        """
    )


def table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {q(table)}").fetchone()[0])


def populate_catalog(conn: sqlite3.Connection) -> None:
    catalog_rows = [
        ("DATASET_01", "可追溯文献来源库", "literature_source", "一篇来源文献", "CSV", "统一数字对象标识符、题名、年份和主题范围", "verified", 1, "来源元数据不是科学结论本身。"),
        ("DATASET_02", "领域先验规则库", "domain_prior_rule", "一条规范化领域规则", "CSV", "定义结构与性质判断依据", "verified_traceable_rule", 1, "按证据级别和适用范围使用。"),
        ("DATASET_03", "六任务与分子表示定义库", "endpoint_and_representation_prior", "一个性质端点或输入表示定义", "CSV", "统一模型输入、输出、单位、变换和缺失值规则", "verified_definition", 1, "六任务是项目最小预测画像，不等同完整实验效能。"),
        ("DATASET_04", "光引发机理先验库", "mechanism_prior_rule", "一条机理分流规则", "CSV", "区分I型、II型和电子转移等机制语境", "verified_traceable_rule", 1, "家族级分流不等于候选分子级机理证明。"),
        ("DATASET_05", "合成路线先验库", "synthesis_route_prior", "一条路线家族证据", "CSV", "记录反应先例、适用机理和底物范围", "verified_route_evidence", 1, "路线先例不等于具体候选可直接合成。"),
        ("DATASET_06", "人工回源证据锚点库", "local_source_evidence", "一个原文证据锚点", "CSV", "保存人工核验的原文位置和结构化含义", "verified_source_text", 1, "只支持锚点明确覆盖的陈述。"),
        ("DATASET_07", "六任务权重先验策略库", "task_weight_policy", "一个任务的权重策略", "CSV", "保存权重数值、证据覆盖和用途边界", "audited_policy", 1, "权重是项目偏好，不是全局最优或自然规律。"),
        ("DATASET_08", "任务权重推导过程库", "task_weight_derivation", "一个权重推导步骤", "CSV", "解释任务权重从文献字段池到策略数值的形成过程", "audited_provenance", 1, "推导过程说明研究决策来源，不证明权重全局最优。"),
        ("DATASET_09", "任务权重自动节点披露库", "task_weight_node_disclosure", "一个自动节点或回退路径", "CSV", "披露模型配置、确定性回退和输出使用情况", "audited_provenance", 1, "不可将自动节点表述成人类专家共识。"),
        ("DATASET_10", "旧版结构化文献提取暂存库", "legacy_paper_extract", "一篇机器提取论文", "JSONL", "保留旧提取结果供重新核对", "unverified", 0, "未经人工回源不得作为论文事实。"),
        ("DATASET_11", "旧版提取陈述暂存库", "legacy_paper_extract_statement", "一个自动提取陈述或证据项", "JSONL拆分", "形成可逐条复核队列", "unverified", 0, "不得自动提升为已核验规则。"),
        ("DATASET_12", "MinerU结构对象暂存库", "mineru_molecule_observation", "一个自动识别结构对象", "CSV", "保存结构字符串、页码和版面坐标", "unverified_requires_review", 0, "可读取不等于结构和标签正确。"),
        ("DATASET_13", "MinerU视觉对象暂存库", "mineru_visual_observation", "一个图、表、公式或路线图对象", "CSV", "保存视觉对象与原文定位", "unverified_requires_review", 0, "必须核对图题、数值、单位和化学含义。"),
        ("DATASET_14", "MinerU人工复核队列", "mineru_review_queue", "一个复核任务", "CSV", "管理自动提取对象的人工确认", "open_review_queue", 0, "完成复核前不进入已核验先验层。"),
        ("DATASET_15", "扩展文献发现池", "literature_discovery_candidate", "一篇去重后的候选文献", "CSV", "保存多来源检索得到的相关候选和排序信息", "unverified_discovery", 0, "题名/摘要相关性评分不等于科学证据强度。"),
        ("DATASET_16", "优先全文回源文献池", "literature_priority_candidate", "一篇优先回源候选文献", "CSV", "减少人工筛选范围并优先补齐知识缺口", "unverified_requires_full_text", 0, "完成全文和证据锚点核验后才能提升为核心来源。"),
        ("DATASET_17", "优先文献全文审查库", "literature_fulltext_review_queue", "一篇全文审查任务", "CSV", "记录全文入口、审查字段、证据锚点状态和升级判断", "human_review_queue", 0, "全文入口存在不等于科学内容已核验；必须保留人工证据锚点。"),
        ("DATASET_18", "双光子全文证据块暂存库", "literature_evidence_block", "一个候选证据块", "CSV", "保存原文片段、页码和字段角色，供数值审查追溯", "unverified_numeric_evidence", 0, "候选证据块不能单独证明数值或实验条件。"),
        ("DATASET_19", "双光子数值候选暂存库", "literature_numeric_evidence_candidate", "一个数值候选", "CSV", "保存光学截面、用量、阈值、上下文和尺寸候选", "unverified_numeric_evidence", 0, "必须完成单位、树脂、波长、光源和系列匹配核验。"),
        ("DATASET_20", "双光子数值人工复核库", "literature_numeric_review_queue", "一个数值复核任务", "CSV", "记录严格闸门结果和人工补证要求", "human_review_queue", 0, "未通过闸门或未完成人工核验的候选不能进入最终数值表。"),
        ("DATASET_21", "双光子来源可用性汇总库", "literature_source_readiness_summary", "一个来源汇总", "CSV", "按来源汇总已发现字段和阻塞原因", "unverified_numeric_evidence", 0, "来源可用性是审查状态，不是文献质量的最终结论。"),
        ("DATASET_22", "定向来源证据审计库", "literature_targeted_source_audit", "一条单篇来源审计记录", "CSV", "保存表格数值、实验上下文、允许用途和人工签核状态", "unverified_targeted_audit", 0, "审计记录未完成人工签核前不得提升为最终科学观测。"),
    ]
    payload = []
    for dataset_id, name, table, unit, form, role, state, core, boundary in catalog_rows:
        payload.append((dataset_id, name, table, unit, form, role, state, table_count(conn, table), core, boundary))
    conn.executemany("INSERT INTO dataset_catalog VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", payload)


def export_query(conn: sqlite3.Connection, query: str, path: Path) -> int:
    cursor = conn.execute(query)
    headers = [description[0] for description in cursor.description]
    rows = cursor.fetchall()
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    return len(rows)


def validate_database(conn: sqlite3.Connection) -> dict[str, Any]:
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    tasks = [row[0] for row in conn.execute("SELECT task FROM v_six_task_prior_dictionary ORDER BY task")]
    normalized_weight_sum = conn.execute("SELECT SUM(normalized_mt6_weight) FROM task_weight_policy").fetchone()[0]
    scaled_weight_sum = conn.execute("SELECT SUM(chemprop_scaled_weight) FROM task_weight_policy").fetchone()[0]
    orphan_checks = {}
    for table in ("domain_prior_rule", "mechanism_prior_rule", "synthesis_route_prior", "local_source_evidence"):
        orphan_checks[table] = conn.execute(
            f"""SELECT COUNT(*) FROM {q(table)} t
                LEFT JOIN literature_source s ON t.source_id = s.source_id
                WHERE t.source_id IS NOT NULL AND s.source_id IS NULL"""
        ).fetchone()[0]
    duplicate_dois = conn.execute(
        """SELECT COUNT(*) FROM (
               SELECT LOWER(TRIM(doi)) AS d, COUNT(*) AS n
               FROM literature_source WHERE doi IS NOT NULL AND TRIM(doi) <> ''
               GROUP BY d HAVING n > 1
           )"""
    ).fetchone()[0]
    table_names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    forbidden = [name for name in table_names if any(token in name for token in ("zinc", "screening", "external_validation", "model_prediction", "quantum"))]
    return {
        "sqlite_integrity_check": integrity,
        "source_count": table_count(conn, "literature_source"),
        "verified_prior_count": table_count(conn, "v_verified_prior_knowledge"),
        "six_task_count": len(tasks),
        "six_tasks": tasks,
        "six_tasks_exact_match": sorted(tasks) == sorted(EXPECTED_TASKS),
        "normalized_weight_sum": normalized_weight_sum,
        "chemprop_scaled_weight_sum": scaled_weight_sum,
        "duplicate_source_doi_groups": duplicate_dois,
        "orphan_source_links": orphan_checks,
        "legacy_paper_extract_count": table_count(conn, "legacy_paper_extract"),
        "legacy_statement_count": table_count(conn, "legacy_paper_extract_statement"),
        "legacy_extract_matched_source_count": conn.execute(
            "SELECT COUNT(*) FROM legacy_paper_extract WHERE linked_source_id IS NOT NULL"
        ).fetchone()[0],
        "mineru_molecule_count": table_count(conn, "mineru_molecule_observation"),
        "mineru_visual_count": table_count(conn, "mineru_visual_observation"),
        "mineru_reaction_count": table_count(conn, "mineru_reaction_observation"),
        "open_mineru_review_count": conn.execute(
            "SELECT COUNT(*) FROM mineru_review_queue WHERE LOWER(COALESCE(status, '')) = 'open'"
        ).fetchone()[0],
        "literature_discovery_candidate_count": table_count(conn, "literature_discovery_candidate"),
        "literature_priority_candidate_count": table_count(conn, "literature_priority_candidate"),
        "literature_fulltext_review_queue_count": table_count(conn, "literature_fulltext_review_queue"),
        "literature_evidence_block_count": table_count(conn, "literature_evidence_block"),
        "literature_numeric_evidence_candidate_count": table_count(conn, "literature_numeric_evidence_candidate"),
        "literature_numeric_review_queue_count": table_count(conn, "literature_numeric_review_queue"),
        "literature_source_readiness_summary_count": table_count(conn, "literature_source_readiness_summary"),
        "literature_targeted_source_audit_count": table_count(conn, "literature_targeted_source_audit"),
        "excluded_scope_tables_present": forbidden,
    }


def write_validation_report(path: Path, validation: dict[str, Any], config: dict[str, Any]) -> None:
    orphan_total = sum(validation["orphan_source_links"].values())
    weight_ok = abs((validation["normalized_weight_sum"] or 0.0) - 1.0) < 1e-5
    lines = [
        "# 光引发剂文献先验数据库验证报告",
        "",
        f"数据库版本：{config['database_version']}",
        "",
        "## 结论",
        "",
        "本版仅整合文献先验知识，未导入候选筛选、模型预测、外部验证或量子化学结果。",
        "已核验知识与机器自动提取内容位于不同数据层，自动提取记录不会默认进入论文事实视图。",
        "",
        "## 核心计数",
        "",
        f"- 可追溯来源文献：{validation['source_count']} 篇",
        f"- 统一已核验先验记录：{validation['verified_prior_count']} 条",
        f"- 六任务定义：{validation['six_task_count']} 项",
        f"- 旧版机器提取：{validation['legacy_paper_extract_count']} 篇论文、{validation['legacy_statement_count']} 条待核陈述",
        f"- 旧版提取与来源总表精确连接：{validation['legacy_extract_matched_source_count']} 篇",
        f"- MinerU暂存对象：{validation['mineru_molecule_count']} 个结构、{validation['mineru_visual_count']} 个视觉对象、{validation['mineru_reaction_count']} 个明确反应",
        f"- MinerU开放复核任务：{validation['open_mineru_review_count']} 条",
        f"- 扩展文献发现池：{validation['literature_discovery_candidate_count']} 篇；优先全文回源池：{validation['literature_priority_candidate_count']} 篇；全文审查队列：{validation['literature_fulltext_review_queue_count']} 篇",
        f"- 双光子候选证据块：{validation['literature_evidence_block_count']} 条；数值候选：{validation['literature_numeric_evidence_candidate_count']} 条；人工数值复核：{validation['literature_numeric_review_queue_count']} 条；来源可用性汇总：{validation['literature_source_readiness_summary_count']} 条",
        f"- 定向来源审计：{validation['literature_targeted_source_audit_count']} 条（当前均为未核验暂存）",
        "",
        "## 一致性检查",
        "",
        f"- SQLite完整性：{validation['sqlite_integrity_check']}",
        f"- 六任务名称完整：{'通过' if validation['six_tasks_exact_match'] else '未通过'}",
        f"- 六任务归一化权重之和：{validation['normalized_weight_sum']:.6f}（{'通过' if weight_ok else '需检查'}）",
        f"- 训练配置比例权重之和：{validation['chemprop_scaled_weight_sum']:.6f}",
        f"- 重复数字对象标识符组：{validation['duplicate_source_doi_groups']}",
        f"- 已核验表中无法连接来源的记录：{orphan_total}",
        f"- 被明确排除范围的结果表：{len(validation['excluded_scope_tables_present'])} 个",
        "",
        "## 使用边界",
        "",
        "1. 已核验规则可用于论文方法描述、规则审查和后续计算流程设计，但必须保留证据级别与声明上限。",
        "2. 旧版机器提取与MinerU对象只能用于定位和人工复核，不能直接作为定量结论。",
        "3. 六任务权重表示本研究对不同性质的优先级安排，不证明这些比例具有普遍最优性。",
        "4. 本数据库是文献知识底座；更新筛选规则时应建立独立的下游数据库或版本，不修改本底座。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_readme(path: Path, config: dict[str, Any]) -> None:
    text = f"""# 光引发剂文献先验数据库

版本：{config['database_version']}

## 这是什么

这是研究的“文献知识底座”。它把分散的文献来源、六项性质定义、结构判断、光引发机理、合成路线和任务权重依据放进一个关系型数据库，同时把旧机器提取和MinerU自动识别内容隔离在待复核区。

本版不包含ZINC22候选、筛选排序、模型预测、外部验证和量子化学结果。

本版同时保存了扩展文献发现层：461篇去重候选，其中442篇不在现有45篇核心来源中，78篇进入优先全文回源池。它们仍是元数据和题名/摘要初筛结果，不是已核验科学证据。

本版还保存了5篇P1本地全文的双光子证据暂存层：122个证据块、314个数值候选和139个人工复核任务。严格闸门没有把这些候选自动写入最终数值表。

## 输入文件形式

- 已核验知识表：CSV。每行是一篇来源、一条规则、一个性质定义或一条路线证据。
- 旧版文献提取：JSONL。每行是一篇论文的嵌套提取结果。
- MinerU暂存结果：CSV。保存结构、视觉对象、原文页码与版面坐标以及复核任务。
- 优先文献全文审查队列：CSV。保存全文入口和人工需要填写的证据锚点字段。
- 双光子证据暂存：CSV。保存候选证据块、数值候选、闸门结果和人工复核任务。

所有输入文件只读，构建过程不会修改原文件。

## 输出文件形式

- `photoinitiator_literature_prior.sqlite`：完整主数据库，适合程序查询和长期维护。
- `verified_prior_knowledge.csv`：可直接审查的统一先验知识表。
- `six_task_prior_dictionary.csv`：六项性质的定义、单位、变换、缺失值处理和权重边界。
- `source_evidence_coverage.csv`：每篇来源支持了哪些类型的知识。
- `mechanism_prior.csv`：机理分流规则。
- `synthesis_route_prior.csv`：合成路线证据。
- `unverified_extraction_review.csv`：旧机器提取与MinerU待复核队列。
- `literature_fulltext_review_queue.csv`：扩展优先文献的全文审查队列；完成证据核验前不进入核心来源。
- `literature_evidence_block.csv`、`literature_numeric_evidence_candidate.csv` 和 `literature_numeric_review_queue.csv`：双光子全文证据暂存和严格闸门审查结果。
- `literature_targeted_source_audit.csv`：Pucher 2009 定向来源审计记录；保存表格数值、配方/光源上下文和声明边界，当前不进入最终科学观测表。
- `field_dictionary.csv`：字段解释。
- `database_catalog.csv`：数据库内各数据集的记录单位、用途和边界。
- `validation_report.md`：构建后的完整性与科学边界检查。

CSV可以直接用Excel打开；SQLite是唯一的正式整合主库。JSONL继续作为原始机器提取交换格式，而不是论文结果表。

## 建议使用方式

论文写作优先查询 `verified_prior_knowledge`、`six_task_prior_dictionary`、`mechanism_prior` 和 `synthesis_route_prior` 视图。自动提取内容只有在人工回到原文核对后，才能提升到已核验注册表；提升时应创建新记录并保留原始对象编号，不要覆盖暂存记录。
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    args = parse_args()
    config_path = args.config if args.config.is_absolute() else (REPO_ROOT / args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    configured_output = Path(config["output_directory"])
    output_dir = args.output or configured_output
    if not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(
            f"Output directory already exists: {output_dir}. Choose a new versioned directory."
        )
    output_dir.mkdir(parents=True, exist_ok=False)

    db_path = output_dir / "photoinitiator_literature_prior.sqlite"
    conn = sqlite3.connect(db_path)
    try:
        init_database(conn, config)

        # Source registry must be loaded first because all verified records link to it.
        assets = config["csv_assets"]
        source_asset = next(asset for asset in assets if asset["table"] == "literature_source")
        import_csv_asset(conn, source_asset)
        for asset in assets:
            if asset is source_asset:
                continue
            import_csv_asset(conn, asset)

        import_raw_extracts(conn, config["raw_extract_asset"])
        populate_catalog(conn)
        create_views(conn)
        conn.commit()

        exports = {
            "verified_prior_knowledge.csv": "SELECT * FROM v_verified_prior_knowledge ORDER BY knowledge_type, knowledge_record_id",
            "six_task_prior_dictionary.csv": "SELECT * FROM v_six_task_prior_dictionary ORDER BY item_id",
            "source_evidence_coverage.csv": "SELECT * FROM v_source_evidence_coverage ORDER BY source_id",
            "mechanism_prior.csv": "SELECT * FROM v_mechanism_prior ORDER BY mechanism_rule_id",
            "synthesis_route_prior.csv": "SELECT * FROM v_synthesis_route_prior ORDER BY route_evidence_id",
            "task_weight_prior.csv": "SELECT * FROM v_task_weight_prior ORDER BY task_order",
            "unverified_extraction_review.csv": "SELECT * FROM v_unverified_extraction_review ORDER BY object_source, object_id",
            "literature_discovery_candidates.csv": "SELECT * FROM v_literature_discovery_candidates ORDER BY review_priority, relevance_score DESC, candidate_id",
            "literature_priority_candidates.csv": "SELECT * FROM v_literature_priority_candidates ORDER BY relevance_score DESC, candidate_id",
            "literature_fulltext_review_queue.csv": "SELECT * FROM literature_fulltext_review_queue ORDER BY review_rank, review_id",
            "literature_evidence_block.csv": "SELECT * FROM literature_evidence_block ORDER BY source_id, evidence_id",
            "literature_numeric_evidence_candidate.csv": "SELECT * FROM literature_numeric_evidence_candidate ORDER BY source_id, candidate_id",
            "literature_numeric_review_queue.csv": "SELECT * FROM literature_numeric_review_queue ORDER BY source_id, candidate_id",
            "literature_source_readiness_summary.csv": "SELECT * FROM literature_source_readiness_summary ORDER BY source_id",
            "literature_targeted_source_audit.csv": "SELECT * FROM literature_targeted_source_audit ORDER BY source_id, audit_id",
            "database_catalog.csv": "SELECT * FROM v_database_overview",
            "field_dictionary.csv": "SELECT * FROM field_dictionary ORDER BY table_name, dictionary_id",
            "asset_registry.csv": "SELECT * FROM asset_registry ORDER BY asset_id",
        }
        export_counts = {
            filename: export_query(conn, query, output_dir / filename)
            for filename, query in exports.items()
        }

        validation = validate_database(conn)
        validation["export_row_counts"] = export_counts
        write_validation_report(output_dir / "validation_report.md", validation, config)
        write_readme(output_dir / "README.md", config)
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.execute("PRAGMA journal_mode=DELETE")
        manifest = {
            "database_name": config["database_name"],
            "database_version": config["database_version"],
            "built_at": now_iso(),
            "database_file": db_path.name,
            "database_sha256": sha256_file(db_path),
            "scope": "literature_prior_only",
            "excluded_scopes": config.get("excluded_scopes", []),
            "validation": validation,
            "output_files": sorted(
                {
                    "build_manifest.json",
                    *(
                        path.name
                        for path in output_dir.iterdir()
                        if path.is_file() and not path.name.endswith(("-wal", "-shm"))
                    ),
                }
            ),
        }
        (output_dir / "build_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # concise CLI failure with a nonzero exit code
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
