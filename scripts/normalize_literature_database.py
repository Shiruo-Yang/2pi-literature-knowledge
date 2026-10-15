"""Build an evidence-preserving literature database; standard library only.

The input JSON maps semantic asset names to existing CSV files. Raw rows and
text anchors are retained only in the separate private output. The public
projection contains metadata, scalar candidates, provenance hashes and links.
No source text is parsed again and no scientific status is upgraded.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def serial(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def doi(value):
    value = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", (value or "").strip(), flags=re.I)
    return value.lower() if re.fullmatch(r"10\.\d{4,9}/\S+", value) else ""


def scalar(value):
    return value if re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", value or "") else ""


def internal_title(value):
    words = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return "evidence guided" in words and "mechanism aware workflow" in words


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE sources(source_key TEXT PRIMARY KEY, doi TEXT, title TEXT, year TEXT, journal TEXT, scope TEXT);
CREATE TABLE source_aliases(alias_id TEXT, source_key TEXT REFERENCES sources, PRIMARY KEY(alias_id,source_key));
CREATE TABLE input_assets(asset_key TEXT PRIMARY KEY, sha256 TEXT, row_count INTEGER);
CREATE TABLE provenance(table_name TEXT, object_key TEXT, asset_key TEXT REFERENCES input_assets, row_number INTEGER, row_sha256 TEXT);
CREATE TABLE evidence(evidence_id TEXT PRIMARY KEY, source_key TEXT REFERENCES sources, field_name TEXT, field_group TEXT, raw_value TEXT, raw_unit TEXT, normalized_value TEXT, normalized_unit TEXT, page_hint TEXT, anchor_sha256 TEXT, anchor_text TEXT, evidence_class TEXT, original_status TEXT, use_status TEXT, condition_scope TEXT, source_lane TEXT, duplicate_group_id TEXT, candidate_value_visibility TEXT);
CREATE TABLE evidence_groups(group_id TEXT PRIMARY KEY, representative_evidence_id TEXT REFERENCES evidence, member_count INTEGER);
CREATE TABLE evidence_group_members(group_id TEXT REFERENCES evidence_groups, evidence_id TEXT REFERENCES evidence, PRIMARY KEY(group_id,evidence_id));
CREATE TABLE public_evidence_crosswalk(public_evidence_id TEXT PRIMARY KEY, evidence_id TEXT REFERENCES evidence, relation TEXT);
CREATE TABLE entities(entity_id TEXT PRIMARY KEY, source_key TEXT REFERENCES sources, label TEXT, entity_scope TEXT, original_status TEXT, identity_class TEXT);
CREATE TABLE accepted_identities(entity_id TEXT PRIMARY KEY REFERENCES entities, canonical_name TEXT, canonical_smiles TEXT, inchikey TEXT, molecular_formula TEXT, original_status TEXT, confidence_tier TEXT, source_location TEXT, source_evidence_id TEXT, use_status TEXT);
CREATE TABLE conditions(cluster_id TEXT PRIMARY KEY, source_key TEXT REFERENCES sources, page_hint TEXT, condition_scope TEXT, cluster_quality TEXT, original_member_count INTEGER);
CREATE TABLE condition_members(cluster_id TEXT REFERENCES conditions, evidence_id TEXT REFERENCES evidence, PRIMARY KEY(cluster_id,evidence_id));
CREATE TABLE formulations(formulation_id TEXT PRIMARY KEY, cluster_id TEXT REFERENCES conditions, original_status TEXT, field_groups TEXT, use_status TEXT);
CREATE TABLE evidence_entity_links(link_id TEXT PRIMARY KEY, evidence_id TEXT REFERENCES evidence, entity_id TEXT REFERENCES entities, cluster_id TEXT REFERENCES conditions, match_basis TEXT, original_status TEXT, confidence TEXT);
CREATE TABLE rules(rule_id TEXT PRIMARY KEY, rule_type TEXT, summary TEXT, rule_text TEXT, scope_limit TEXT, original_status TEXT);
CREATE TABLE rule_sources(rule_id TEXT REFERENCES rules, source_key TEXT REFERENCES sources, PRIMARY KEY(rule_id,source_key));
CREATE TABLE quality_issues(issue_id TEXT PRIMARY KEY, object_type TEXT, object_id TEXT, issue_type TEXT, action TEXT);
"""


def build(config, public_dir, private_dir):
    if sys.version_info < (3, 11):
        raise RuntimeError("Python 3.11+ is required to preserve embedded NUL characters in legacy CSV text.")
    # Fresh destination prevents accidental replacement of a frozen database.
    for out in (public_dir, private_dir):
        if out.exists():
            raise ValueError("Output already exists: use a separate staging directory.")
    assets = {}
    metadata = []
    for name, filename in sorted(config.items()):
        path = Path(filename)
        with path.open(encoding="utf-8-sig", newline="") as handle:
            try:
                assets[name] = list(csv.DictReader(handle))
            except csv.Error as exc:
                raise ValueError("CSV parse error in asset " + name) from exc
        metadata.append((name, hashlib.sha256(path.read_bytes()).hexdigest(), len(assets[name])))
    required = {"source_inventory", "established_sources", "public_sources", "candidates", "canonical_groups", "public_evidence", "source_entities", "accepted_identities", "terminal_entities", "molecule_aliases", "conditions", "condition_members", "formulations", "entity_links", "domain_rules", "mechanism_rules", "route_rules"}
    if required != set(assets):
        raise ValueError("Input asset keys differ: " + str(required ^ set(assets)))
    for out in (public_dir, private_dir):
        out.mkdir(parents=True)
    input_archive = private_dir / "original_inputs"
    input_archive.mkdir()
    for name, filename in config.items():
        (input_archive / (name + ".csv")).write_bytes(Path(filename).read_bytes())
    db = sqlite3.connect(private_dir / "literature.sqlite")
    db.executescript(SCHEMA)
    db.execute("CREATE TABLE raw_records(asset_key TEXT REFERENCES input_assets,row_number INTEGER,row_json TEXT,PRIMARY KEY(asset_key,row_number))")
    db.executemany("INSERT INTO input_assets VALUES(?,?,?)", metadata)
    for name, rows in assets.items():
        db.executemany("INSERT INTO raw_records VALUES(?,?,?)", [(name, i, serial(r)) for i, r in enumerate(rows, 1)])

    def put(table, values):
        db.execute("INSERT INTO " + table + " VALUES(" + ",".join("?" for _ in values) + ")", values)

    def origin(table, key, asset, i, row):
        put("provenance", (table, key, asset, i, digest(serial(row))))

    def issue(kind, key, reason, action="retain_and_flag_no_automatic_correction"):
        issue_id = "ISS-" + digest(serial((kind, key, reason)))[:24]
        db.execute("INSERT OR IGNORE INTO quality_issues VALUES(?,?,?,?,?)", (issue_id, kind, key, reason, action))

    # DOI-first resolution; alias-only resolution is permitted only when one DOI
    # has been observed for that exact source ID. No fuzzy title deduplication.
    alias_dois = defaultdict(set)
    source_rows = []
    for asset, rows in assets.items():
        if asset in {"molecule_aliases", "domain_rules", "mechanism_rules", "route_rules"}:
            continue
        for i, row in enumerate(rows, 1):
            alias = row.get("paper_id") or row.get("source_id") or ""
            d = doi(row.get("doi", ""))
            if alias or d:
                source_rows.append((asset, i, row, alias, d))
                if alias and d:
                    alias_dois[alias].add(d)
    source_map = {}
    for asset, i, row, alias, d in source_rows:
        if not d and len(alias_dois[alias]) == 1:
            d = next(iter(alias_dois[alias]))
        key = "SRC-" + digest("doi:" + d if d else "alias:" + alias)[:24]
        source_map[(asset, i)] = key
        title = row.get("title", "")
        scope = "internal_workflow_candidate" if internal_title(title) else "literature_inventory_not_independence_certified"
        db.execute("INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?,?)", (key, d, title, row.get("year", ""), row.get("journal", ""), scope))
        for field in ("title", "year", "journal"):
            value = row.get(field, "")
            if value:
                db.execute("UPDATE sources SET " + field + "=? WHERE source_key=? AND " + field + "=''", (value, key))
        if internal_title(title):
            db.execute("UPDATE sources SET scope=? WHERE source_key=?", (scope, key))
            issue("source", key, "possible_own_research_document", "exclude_from_external_evidence_view_preserve_for_provenance")
        if alias:
            db.execute("INSERT OR IGNORE INTO source_aliases VALUES(?,?)", (alias, key))
        if row.get("doi") and not doi(row["doi"]):
            issue("source", key, "invalid_or_unsupported_doi_syntax")
        if len(alias_dois[alias]) > 1:
            issue("source_alias", alias, "multiple_dois_for_same_source_alias")
        origin("sources", key, asset, i, row)

    def source(asset, i):
        return source_map.get((asset, i))

    def evidence(asset, i, row, eid, status):
        anchor = row.get("evidence_anchor", "")
        put("evidence", (eid, source(asset, i), row.get("field_name", ""), row.get("field_group", ""), row.get("raw_value", ""), row.get("raw_unit", ""), row.get("normalized_value", ""), row.get("normalized_unit", ""), row.get("page_hint", ""), digest(anchor) if anchor else "", anchor, row.get("evidence_class", row.get("evidence_lane", "")), row.get("automatic_status", ""), status, row.get("condition_scope", ""), row.get("source_lane", ""), row.get("duplicate_group_id", ""), "private_original"))
        origin("evidence", eid, asset, i, row)
        if not row.get("page_hint"):
            issue("evidence", eid, "missing_page_locator")
        if not anchor:
            issue("evidence", eid, "missing_text_anchor")
        if not doi(row.get("doi", "")):
            issue("evidence", eid, "doi_not_recorded_on_input_row")
        field = row.get("field_name", "")
        if "wavelength" in field or "wavelength_nm=" in row.get("raw_value", ""):
            if re.search(r"line\s*width|line\s*widths|voxel|spatial resolution", anchor, re.I):
                issue("evidence", eid, "possible_geometry_vs_wavelength_context_collision")

    candidates_by_origin = defaultdict(list)
    for i, row in enumerate(assets["candidates"], 1):
        eid = row["record_id"]
        evidence("candidates", i, row, eid, "machine_candidate_not_measurement_certified")
        candidates_by_origin[row.get("source_record_id", "")].append((eid, row, source("candidates", i)))
    for i, row in enumerate(assets["public_evidence"], 1):
        # Do not merge by scalar value or title. Require preserved origin ID,
        # resolved source, endpoint, raw value and unit to agree uniquely.
        matches = [e for e, old, src in candidates_by_origin[row.get("source_record_id", "")]
                   if src == source("public_evidence", i) and all(old.get(k, "") == row.get(k, "") for k in ("field_name", "raw_value", "raw_unit"))]
        legacy = row.get("record_origin") == "legacy_registry"
        if len(matches) == 1 and not legacy:
            eid = matches[0]
            relation = "same_preserved_extraction_origin"
            origin("evidence", eid, "public_evidence", i, row)
        else:
            eid = "PUB-" + row["evidence_id"]
            evidence("public_evidence", i, row, eid, "legacy_audit_status_inherited_not_reaudited" if legacy else "unmatched_public_candidate")
            relation = "retained_separate_audit_layer" if legacy else "retained_unresolved_origin_match"
            if not legacy:
                issue("evidence", eid, "public_to_local_origin_match_not_unique")
        put("public_evidence_crosswalk", (row["evidence_id"], eid, relation))
    groups = defaultdict(list)
    for row in assets["candidates"]:
        groups[row["duplicate_group_id"]].append(row["record_id"])
    for row in assets["canonical_groups"]:
        gid = row["duplicate_group_id"]
        if row["record_id"] not in groups[gid]:
            raise ValueError("Canonical representative not in candidate group")
        put("evidence_groups", (gid, row["record_id"], len(groups[gid])))
        for eid in groups[gid]:
            put("evidence_group_members", (gid, eid))
    if set(groups) != {r["duplicate_group_id"] for r in assets["canonical_groups"]}:
        raise ValueError("Canonical group coverage mismatch")

    accepted = {r["entity_id"] for r in assets["accepted_identities"]}
    terminal = {r["entity_id"]: r["terminal_status"] for r in assets["terminal_entities"]}
    for i, row in enumerate(assets["source_entities"], 1):
        eid = row["entity_id"]
        identity = "accepted_single_molecule_identity_only" if eid in accepted else terminal.get(eid, "unresolved_identity")
        put("entities", (eid, source("source_entities", i), row["raw_label"], "source_local", row.get("entity_status", ""), identity))
        origin("entities", eid, "source_entities", i, row)
    for i, row in enumerate(assets["molecule_aliases"], 1):
        eid = row["molecule_id"]
        db.execute("INSERT OR IGNORE INTO entities VALUES(?,?,?,?,?,?)", (eid, None, row["preferred_name"], "existing_alias_not_source_structure_confirmation", row.get("identity_status", ""), "alias_reference_only"))
        origin("entities", eid, "molecule_aliases", i, row)
    for i, row in enumerate(assets["accepted_identities"], 1):
        eid = row["entity_id"]
        put("accepted_identities", (eid, row["canonical_name"], row["canonical_smiles"], row["inchikey"], row["molecular_formula"], row["identity_status"], row["confidence_tier"], row["source_location"], row["source_evidence_id"], "identity_only_inherited_not_numeric_certification"))
        origin("accepted_identities", eid, "accepted_identities", i, row)
    for i, row in enumerate(assets["conditions"], 1):
        put("conditions", (row["cluster_id"], source("conditions", i), row["page_hint"], row["condition_scope"], row["cluster_quality"], int(row["member_count"])))
        origin("conditions", row["cluster_id"], "conditions", i, row)
    for i, row in enumerate(assets["condition_members"], 1):
        put("condition_members", (row["cluster_id"], row["record_id"]))
        origin("condition_members", row["cluster_id"] + ":" + row["record_id"], "condition_members", i, row)
    for i, row in enumerate(assets["formulations"], 1):
        put("formulations", (row["formulation_cluster_id"], row["cluster_id"], row["formulation_status"], row["field_groups"], "context_cluster_not_certified_recipe"))
        origin("formulations", row["formulation_cluster_id"], "formulations", i, row)
    for i, row in enumerate(assets["entity_links"], 1):
        for table, column, value in (("evidence", "evidence_id", row["record_id"]), ("entities", "entity_id", row["entity_id"]), ("conditions", "cluster_id", row["cluster_id"])):
            if table == "conditions" and not value:
                continue
            if not db.execute("SELECT 1 FROM " + table + " WHERE " + column + "=?", (value,)).fetchone():
                raise ValueError("Missing link target: " + table + " " + value + " for " + row["link_id"])
        put("evidence_entity_links", (row["link_id"], row["record_id"], row["entity_id"], row["cluster_id"] or None, row["match_basis"], row["link_status"], row["link_confidence"]))
        origin("evidence_entity_links", row["link_id"], "entity_links", i, row)
    for asset, idcol, kind in (("domain_rules", "knowledge_id", "domain_prior"), ("mechanism_rules", "mechanism_rule_id", "mechanism_prior"), ("route_rules", "route_evidence_id", "synthesis_route_prior")):
        for i, row in enumerate(assets[asset], 1):
            rid = row[idcol]
            put("rules", (rid, kind, row["evidence_summary"], row.get("normalized_rule", row.get("normalized_route_rule", "")), row.get("exclusion_or_claim_limit", row.get("scope_limit", row.get("scientific_rationale", ""))), row["status"]))
            origin("rules", rid, asset, i, row)
            for raw_doi in row["supporting_dois"].split(";"):
                d = doi(raw_doi)
                sid = "SRC-" + digest("doi:" + d)[:24]
                put("rule_sources", (rid, sid))

    # New conservative views; raw candidate rows and historical statuses stay intact.
    db.executescript("""
    CREATE VIEW literature_candidates_excluding_flagged_internal_docs AS SELECT e.* FROM evidence e JOIN sources s USING(source_key) WHERE s.scope!='internal_workflow_candidate';
    CREATE VIEW source_local_identity_summary AS SELECT identity_class,COUNT(*) AS records FROM entities WHERE entity_scope='source_local' GROUP BY identity_class;
    """)
    db.commit()
    if db.execute("PRAGMA foreign_key_check").fetchall() or db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise ValueError("Database integrity failed")
    # Copy only declared relational tables into the public projection. Neither
    # private raw records nor their local file paths are copied into this file.
    pub = sqlite3.connect(public_dir / "literature.sqlite")
    pub.executescript(SCHEMA)
    tables = [r[0] for r in pub.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid")]
    for table in tables:
        cur = db.execute("SELECT * FROM " + table)
        columns = [d[0] for d in cur.description]
        rows = [dict(zip(columns, r)) for r in cur]
        if table == "evidence":
            for row in rows:
                original = row["raw_value"]
                row["anchor_text"] = ""
                row["raw_value"] = scalar(original)
                row["normalized_value"] = scalar(row["normalized_value"])
                row["candidate_value_visibility"] = "scalar_candidate" if row["raw_value"] else ("empty_in_input" if not original else "nonscalar_retained_in_private_archive")
        pub.executemany("INSERT INTO " + table + " VALUES(" + ",".join("?" for _ in columns) + ")", [tuple(r[c] for c in columns) for r in rows])
        write_csv(public_dir / (table + ".csv"), rows, columns)
        if table == "evidence":
            with (public_dir / "evidence.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
                for row in rows:
                    handle.write(serial(row) + "\n")
    for name, sql in db.execute("SELECT name,sql FROM sqlite_master WHERE type='view'"):
        pub.execute(sql)
    pub.commit()
    counts = {t: pub.execute("SELECT COUNT(*) FROM " + t).fetchone()[0] for t in tables}
    summary = {
        "schema": "normalized_literature_database", "table_counts": counts,
        "inventory_source_records": len(assets["source_inventory"]),
        "distinct_recorded_dois": pub.execute("SELECT COUNT(DISTINCT doi) FROM sources WHERE doi!=''").fetchone()[0],
        "sources_with_evidence": pub.execute("SELECT COUNT(DISTINCT source_key) FROM evidence").fetchone()[0],
        "sources_without_field_evidence": pub.execute("SELECT COUNT(*) FROM sources s WHERE NOT EXISTS(SELECT 1 FROM evidence e WHERE e.source_key=s.source_key)").fetchone()[0],
        "internal_document_evidence_records": pub.execute("SELECT COUNT(*) FROM evidence e JOIN sources s USING(source_key) WHERE s.scope='internal_workflow_candidate'").fetchone()[0],
        "source_local_identity_classes": dict(pub.execute("SELECT * FROM source_local_identity_summary")),
        "accepted_distinct_recorded_inchikeys": pub.execute("SELECT COUNT(DISTINCT inchikey) FROM accepted_identities WHERE inchikey!=''").fetchone()[0],
        "evidence_status_counts": dict(pub.execute("SELECT use_status,COUNT(*) FROM evidence GROUP BY use_status")),
        "public_crosswalk_counts": dict(pub.execute("SELECT relation,COUNT(*) FROM public_evidence_crosswalk GROUP BY relation")),
        "source_scope_counts": dict(pub.execute("SELECT scope,COUNT(*) FROM sources GROUP BY scope")),
        "quality_issue_counts": dict(pub.execute("SELECT issue_type,COUNT(*) FROM quality_issues GROUP BY issue_type")),
        "new_certified_measurements": 0, "new_training_labels": 0,
        "structure_validation": "Inherited identifiers preserved; no chemical structure revalidation performed by this builder.",
        "rights": "No new licence granted over third-party material. Full text, source PDFs and private raw rows are not in this projection.",
        "foreign_key_check": pub.execute("PRAGMA foreign_key_check").fetchall(),
        "integrity_check": pub.execute("PRAGMA integrity_check").fetchone()[0],
    }
    (public_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    dictionary = []
    for table in tables:
        for _, name, dtype, required, _, pk in pub.execute("PRAGMA table_info(" + table + ")"):
            dictionary.append({"table": table, "column": name, "storage_type": dtype, "primary_key": str(bool(pk)).lower(), "missing_value": "NULL for absent relationships; empty string for unreported text", "unit_policy": "raw_unit/normalized_unit accompany evidence values; no new unit conversion" if table == "evidence" else "not_applicable", "definition": FIELD_HELP.get(name, "Inherited or descriptive " + name.replace("_", " ") + "; see database guide.")})
    write_csv(public_dir / "data_dictionary.csv", dictionary, list(dictionary[0]))
    pub.close()
    db.close()
    for out in (public_dir, private_dir):
        manifest = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob("*")) if p.is_file()}
        (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2, ensure_ascii=False))


FIELD_HELP = {
    "source_key": "Stable hash of normalized DOI; otherwise exact source alias. Not a certificate of independent publication.",
    "evidence_id": "Preserved automatic candidate ID or PUB-prefixed retained public evidence ID.",
    "anchor_sha256": "SHA-256 of original text anchor; public anchor text withheld, not missing from private archive.",
    "anchor_text": "Original extraction context, private only. Public column is intentionally empty.",
    "original_status": "Status inherited from input; not a new audit result.",
    "use_status": "Explicit permitted-use boundary, independent of inherited confidence.",
    "raw_value": "Original value privately; only a syntactically numeric scalar publicly. A scalar is not necessarily a valid measurement.",
    "normalized_value": "Previously normalized input value; no new conversion or correction by this build.",
    "group_id": "Inherited candidate duplicate group; not deduplication of experimental measurements.",
    "row_sha256": "SHA-256 of sorted-key compact UTF-8 JSON for the complete original input row.",
    "row_number": "One-based CSV data row, excluding header.",
    "condition_scope": "Inherited locality of extraction context; not proof that all fields belong to one experiment.",
    "identity_class": "Source-local single molecule, terminal material/nonchemical, unresolved, or global alias-only reference.",
    "candidate_value_visibility": "Whether public scalar is exposed, input is empty, or nonscalar text is retained privately.",
}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    args = parser.parse_args()
    build(json.loads(args.inputs.read_text(encoding="utf-8")), args.public_output, args.private_output)
