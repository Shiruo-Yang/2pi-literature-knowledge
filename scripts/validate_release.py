from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures = []
for line in (ROOT / "checksums.sha256").read_text(encoding="utf-8").splitlines():
    digest, relative = line.split("  ", 1)
    path = ROOT / relative
    if not path.exists():
        failures.append(f"missing: {relative}")
        continue
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != digest:
        failures.append(f"checksum mismatch: {relative}")
for path in ROOT.rglob("*"):
    if not path.is_file() or path.name in {"checksums.sha256", "package_manifest.json"}:
        continue
    if path.relative_to(ROOT).as_posix() == "scripts/validate_release.py":
        continue
    if path.suffix.lower() not in {".csv", ".md", ".json", ".txt", ".py"} and path.name != "VERSION":
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pattern in (r"[A-Z]:\\", r"/share/home/", r"(?i)round\s*29", r"(?i)methods_c1|#\s*C1\b|\bC1 formalises"):
        if re.search(pattern, text):
            failures.append(f"sensitive/internal token in {path.relative_to(ROOT)}: {pattern}")

def rows(name):
    with (ROOT / name).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))

source_ids = {row["source_id"] for row in rows("source_registry.csv")}
for registry in ("domain_knowledge_registry.csv", "mechanism_decision_registry.csv", "synthesis_route_evidence_registry.csv"):
    for row in rows(registry):
        dois = [value for value in row["supporting_dois"].split(";") if value]
        ids = [value for value in row["supporting_source_ids"].split(";") if value]
        if not dois or not ids:
            failures.append(f"empty citation cluster: {registry} {next(iter(row.values()))}")
        if len(dois) != len(set(dois)) or len(ids) != len(set(ids)):
            failures.append(f"duplicate citation-cluster member: {registry} {next(iter(row.values()))}")
        if len(dois) != len(ids) or len(dois) != int(row["supporting_source_count"]):
            failures.append(f"citation-cluster count mismatch: {registry} {next(iter(row.values()))}")
        if not set(ids).issubset(source_ids):
            failures.append(f"unresolved supporting source: {registry} {next(iter(row.values()))}")

required_endpoint_fields = (
    "definition", "original_unit", "training_unit", "valid_label_count", "transformation",
    "inverse_transformation", "invalid_value_handling", "source",
)
endpoints = [row for row in rows("endpoint_representation_registry.csv") if row["item_type"] == "endpoint"]
if len(endpoints) != 6:
    failures.append(f"expected 6 endpoints, found {len(endpoints)}")
for row in endpoints:
    for field in required_endpoint_fields:
        if not row[field].strip():
            failures.append(f"missing endpoint field {field}: {row['item_id']}")
    try:
        if int(row["valid_label_count"]) <= 0:
            failures.append(f"invalid endpoint label count: {row['item_id']}")
    except ValueError:
        failures.append(f"non-integer endpoint label count: {row['item_id']}")

route_levels = {row["route_evidence_class"] for row in rows("synthesis_route_evidence_registry.csv")}
allowed_route_levels = {"direct_route_precedent", "qualified_close_analogue", "contextual_or_analogous_support"}
if not route_levels.issubset(allowed_route_levels):
    failures.append(f"undefined route evidence class(es): {sorted(route_levels - allowed_route_levels)}")

ablations = [row for row in rows("model_evaluation_registry.csv") if row["evidence_class"] == "descriptor_ablation"]
if len(ablations) != 7:
    failures.append(f"expected 7 descriptor ablations, found {len(ablations)}")
if any(row["status"] != "completed" for row in ablations):
    failures.append("descriptor-ablation registry contains a non-completed row")
if any(row["n_folds"] != "5" for row in ablations):
    failures.append("descriptor-ablation registry contains an incomplete fold count")
if any(row["fold_consistency"] != "all validation-set hashes matched graph_only" for row in ablations):
    failures.append("descriptor-ablation fold-consistency check failed")
if ablations:
    best = min(ablations, key=lambda row: float(row["rmse"]))
    if best["model_or_experiment"] != "dense_plus_pi_core":
        failures.append(f"unexpected lowest-RMSE ablation: {best['model_or_experiment']}")
if failures:
    raise SystemExit("\n".join(failures))
print("Release validation passed.")
