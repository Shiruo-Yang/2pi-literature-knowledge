"""Independently check exported tables and provenance, without importing builder."""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def verify(directory, private=None):
    manifest = json.loads((directory / "manifest.json").read_text())
    for name, sha in manifest.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == sha, name
    db = sqlite3.connect("file:" + (directory / "literature.sqlite").resolve().as_posix() + "?mode=ro", uri=True)
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert not db.execute("SELECT name FROM sqlite_master WHERE name='raw_records'").fetchall()
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    for table, count in summary["table_counts"].items():
        rows = read_csv(directory / (table + ".csv"))
        cur = db.execute("SELECT * FROM " + table)
        fields = [c[0] for c in cur.description]
        expected = [dict(zip(fields, ("" if v is None else str(v) for v in row))) for row in cur]
        assert rows == expected and len(rows) == count, table
    jsonl = [json.loads(line) for line in (directory / "evidence.jsonl").read_text(encoding="utf-8").splitlines()]
    assert jsonl == read_csv(directory / "evidence.csv")
    assert not db.execute("SELECT 1 FROM evidence WHERE anchor_text!=''").fetchone()
    assert not db.execute("SELECT 1 FROM evidence_group_members m JOIN evidence e USING(evidence_id) WHERE m.group_id!=e.duplicate_group_id").fetchone()
    assert not db.execute("SELECT 1 FROM evidence_groups g WHERE member_count!=(SELECT COUNT(*) FROM evidence_group_members m WHERE m.group_id=g.group_id)").fetchone()
    assert not db.execute("SELECT 1 FROM conditions c WHERE original_member_count!=(SELECT COUNT(*) FROM condition_members m WHERE m.cluster_id=c.cluster_id)").fetchone()
    assert not db.execute("SELECT 1 FROM condition_members m JOIN conditions c USING(cluster_id) JOIN evidence e USING(evidence_id) WHERE c.source_key!=e.source_key").fetchone()
    assert not db.execute("SELECT 1 FROM evidence_entity_links l JOIN entities n USING(entity_id) JOIN evidence e USING(evidence_id) WHERE n.entity_scope='source_local' AND n.source_key!=e.source_key").fetchone()
    assert db.execute("SELECT COUNT(*) FROM source_local_identity_summary").fetchone()[0] == 4
    assert dict(db.execute("SELECT * FROM source_local_identity_summary")) == summary["source_local_identity_classes"]
    for row in read_csv(directory / "evidence.csv"):
        assert not row["raw_value"] or re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?", row["raw_value"])
    # Scan every textual public export; data files must not disclose local paths.
    for p in directory.glob("*"):
        if p.suffix in {".csv", ".json", ".jsonl"}:
            text = p.read_text(encoding="utf-8-sig")
            assert not re.search(r"(?i)(?:[a-z]:[\\/]|/users/|/home/)", text), p.name
    provenance_verified = 0
    if private:
        original = sqlite3.connect("file:" + (private / "literature.sqlite").resolve().as_posix() + "?mode=ro", uri=True)
        raw = {(a, i): r for a, i, r in original.execute("SELECT * FROM raw_records")}
        for asset, sha, count in db.execute("SELECT * FROM input_assets"):
            f = private / "original_inputs" / (asset + ".csv")
            assert hashlib.sha256(f.read_bytes()).hexdigest() == sha
            rows = read_csv(f)
            assert len(rows) == count
            for i, row in enumerate(rows, 1):
                canonical = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                assert raw[(asset, i)] == canonical
        for asset, i, sha in db.execute("SELECT asset_key,row_number,row_sha256 FROM provenance"):
            assert hashlib.sha256(raw[(asset, i)].encode()).hexdigest() == sha
            provenance_verified += 1
        # Verify full public candidate crosswalk against the original inputs.
        mapping = dict(db.execute("SELECT public_evidence_id,evidence_id FROM public_evidence_crosswalk"))
        for row in read_csv(private / "original_inputs/public_evidence.csv"):
            eid = mapping[row["evidence_id"]]
            value = original.execute("SELECT raw_value,raw_unit,field_name FROM evidence WHERE evidence_id=?", (eid,)).fetchone()
            assert value == (row["raw_value"], row["raw_unit"], row["field_name"])
        original.close()
    db.close()
    return {"status": "passed", "tables_checked": len(summary["table_counts"]), "provenance_rows_checked": provenance_verified, "scientific_recertification": False}


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("directory", type=Path)
    p.add_argument("--private", type=Path)
    a = p.parse_args()
    print(json.dumps(verify(a.directory, a.private), indent=2))
