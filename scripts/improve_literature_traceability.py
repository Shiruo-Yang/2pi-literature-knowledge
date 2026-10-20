"""Add reversible source-location and semantic assessments; never edit base data."""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def normalize(text):
    text = re.sub(r"---\s*Page\s+\d+\s*---", "", text)
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text)).casefold()


def occurrences(text, needle):
    if len(needle) < 60:
        return []
    hits = []
    pos = text.find(needle)
    while pos >= 0:
        hits.append(pos)
        pos = text.find(needle, pos + 1)
    return hits


def xml_blocks(path):
    root = ET.parse(path).getroot()
    paths = {}
    def visit(elem, address):
        paths[id(elem)] = address
        counts = Counter()
        for child in elem:
            tag = child.tag.split("}")[-1]
            counts[tag] += 1
            visit(child, address + "/" + tag + "[" + str(counts[tag]) + "]")
    visit(root, "/" + root.tag.split("}")[-1] + "[1]")
    blocks = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag in {"article-title", "title", "p", "caption", "td", "th"}:
            text = " ".join(p.strip() for p in elem.itertext() if p.strip())
            if text:
                blocks.append((paths[id(elem)], text))
    return blocks


def pdf_cache_blocks(text):
    markers = list(re.finditer(r"---\s*Page\s+(\d+)\s*---", text))
    return [(m.group(1), text[m.end():markers[i + 1].start() if i + 1 < len(markers) else len(text)])
            for i, m in enumerate(markers)]


def locate(anchor, blocks):
    spans = []
    joined = ""
    for label, text in blocks:
        start = len(joined)
        joined += normalize(text)
        spans.append((start, len(joined), label))
    needle = normalize(anchor)
    hits = occurrences(joined, needle)
    if len(hits) != 1:
        return {"match_count": len(hits), "locator_start": "", "locator_end": "",
                "normalized_start": "", "normalized_end": ""}
    start = hits[0]
    end = start + len(needle)
    labels = [label for a, b, label in spans if a < end and b > start]
    return {"match_count": 1, "locator_start": labels[0], "locator_end": labels[-1],
            "normalized_start": start, "normalized_end": end}


def semantic(row):
    """Narrow pattern flags only; no value correction or field reassignment."""
    field = row["field_name"]
    raw = row["raw_value"]
    if "wavelength" in field and re.fullmatch(r"\d+(?:\.\d+)?", raw):
        value = raw
    else:
        match = re.search(r"(?:^|;)wavelength_nm=(\d+(?:\.\d+)?)(?:;|$)", raw)
        value = match.group(1) if match else ""
    if not value:
        return "", "broad_context_flag_only"
    # Requires the same recorded scalar to occur in an explicit geometry phrase.
    pattern = r"(?:line\s*widths?|voxel\s*(?:size|diameter)|spatial\s*resolution)\s+(?:(?:of|about|approximately|around|as\s+small\s+as)\s+){0,3}" + re.escape(value) + r"\s*nm\b"
    if re.search(pattern, row["evidence_anchor"], re.I):
        return value, "same_scalar_in_explicit_geometry_phrase"
    return value, "broad_context_flag_only"


def scalar_anchor_check(row):
    number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
    raw = row.get("raw_value", "").strip()
    unit = row.get("raw_unit", "").strip()
    m = re.fullmatch("(" + number + ")" + (r"\s*" + re.escape(unit) if unit else ""), raw)
    if not m:
        m = re.fullmatch("(" + number + ")", raw)
    if not m:
        return "not_applicable_nonscalar_or_empty"
    # Conservative literal check: spelling differences remain unresolved, not errors.
    found = re.search(r"(?<![\w.])" + re.escape(m.group(1)) + r"(?![\w.])", row["evidence_anchor"])
    return "literal_scalar_present_not_endpoint_certified" if found else "literal_scalar_not_found_requires_value_anchor_review"


def csv_write(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def build(base, archive, workspace, out, private, pdf_python):
    if out.exists() or private.exists():
        raise ValueError("Fresh staging destinations required.")
    out.mkdir(parents=True)
    private.mkdir(parents=True)
    base_db = sqlite3.connect("file:" + base.resolve().as_posix() + "?mode=ro", uri=True)
    raw_db = sqlite3.connect("file:" + archive.resolve().as_posix() + "?mode=ro", uri=True)
    records = {r["record_id"]: r for (j,) in raw_db.execute(
        "SELECT row_json FROM raw_records WHERE asset_key='candidates'") for r in [json.loads(j)]}
    missing = {e for (e,) in base_db.execute("SELECT evidence_id FROM evidence WHERE page_hint=''")}
    warnings = {e for (e,) in base_db.execute("SELECT object_id FROM quality_issues WHERE issue_type='possible_geometry_vs_wavelength_context_collision'")}
    target = sorted(missing | warnings)
    meta_path = workspace / "outputs/two_photon_fulltext_20260630/automated_structured_extraction_20260905/paper_metadata.csv"
    with meta_path.open(encoding="utf-8-sig", newline="") as f:
        metadata = {r["paper_id"]: r for r in csv.DictReader(f)}
    def resolve(value):
        p = Path(value)
        return p if p.is_absolute() else workspace / p
    # Fallback uses exact original extraction paths, not title/fuzzy searches.
    cache, source_assets, private_assets = {}, [], []
    from liteparse import LiteParse
    parser = LiteParse(ocr_enabled=False, quiet=True, num_workers=2)
    locators = []
    semantics = []
    for eid in target:
        row = records.get(eid)
        if row is None:
            raise ValueError("Target not in preserved automatic input: " + eid)
        pid = row["paper_id"]
        if pid not in cache:
            m = metadata.get(pid, {})
            original = resolve(m["source_pdf_path"]) if m.get("source_pdf_path") else None
            text_path = resolve(m.get("text_path") or row["source_text_path"]) if (m.get("text_path") or row.get("source_text_path")) else None
            blocks, secondary, direct, method, error = [], [], [], "unavailable_source", ""
            original_hash, text_hash = "", ""
            original_doi = (m.get("doi") or row.get("doi", "")).strip().lower()
            source_binding = "not_confirmed"
            try:
                if original and original.is_file():
                    original_hash = sha(original)
                    if original.suffix.lower() == ".xml":
                        blocks = xml_blocks(original)
                        method = "exact_publisher_xml_node_span"
                        tree = ET.parse(original)
                        article_dois = [(e.text or "").strip().lower() for e in tree.iter()
                                        if e.tag.split("}")[-1] == "article-id" and e.get("pub-id-type") == "doi"]
                        if original_doi in article_dois and original_doi:
                            source_binding = "doi_in_original_article_metadata"
                    elif original.suffix.lower() == ".pdf":
                        parsed = parser.parse(original)
                        secondary = [(str(p.page_num), p.text) for p in parsed.pages]
                        blocks = secondary
                        method = "exact_reparsed_pdf_page_span"
                        direct_path = private / (pid + "_original_pdf_pages.json")
                        subprocess.run([str(pdf_python), str(Path(__file__).with_name("read_pdf_pages_for_traceability.py")), str(original), str(direct_path)], check=True, capture_output=True, timeout=90)
                        direct = json.loads(direct_path.read_text(encoding="utf-8"))
                        if original_doi and normalize(original_doi) in normalize(" ".join(t for _, t in direct[:2])):
                            source_binding = "doi_in_first_two_pdf_pages"
                if text_path and text_path.is_file():
                    text_hash = sha(text_path)
                    if not blocks or method == "exact_reparsed_pdf_page_span":
                        cached = pdf_cache_blocks(text_path.read_text(encoding="utf-8-sig"))
                        if cached:
                            blocks = cached
                            method = "exact_cached_pdf_page_span"
            except Exception as exc:
                error = type(exc).__name__ + ": " + str(exc)
            cache[pid] = (blocks, secondary, direct, method, original_hash, error, source_binding, original_doi)
            source_assets.append({"paper_id": pid, "source_sha256": original_hash,
                                  "cached_text_sha256": text_hash, "method": method,
                                  "source_status": "loaded" if blocks else "unavailable",
                                  "source_doi": original_doi, "source_binding": source_binding})
            private_assets.append({"paper_id": pid, "source_path": str(original or ""),
                                   "cached_text_path": str(text_path or ""), "error": error,
                                   "blocks": blocks, "secondary_blocks": secondary,
                                   "direct_pdf_blocks": direct})
        blocks, secondary, direct, method, original_hash, error, source_binding, original_doi = cache[pid]
        hit = locate(row["evidence_anchor"], blocks)
        secondary_hit = locate(row["evidence_anchor"], secondary) if secondary else {"match_count": 0, "locator_start": "", "locator_end": ""}
        direct_hit = locate(row["evidence_anchor"], direct) if direct else {"match_count": 0, "locator_start": "", "locator_end": ""}
        if hit["match_count"] == 1:
            state = "resolved_xml_node_span" if method == "exact_publisher_xml_node_span" else "resolved_cached_page_span"
        elif hit["match_count"] > 1:
            state = "ambiguous_multiple_matches"
        else:
            state = "unresolved_no_exact_match" if blocks else "unresolved_source_unavailable"
        crosscheck = "not_applicable_xml" if method == "exact_publisher_xml_node_span" else "not_reproduced_in_secondary_parser"
        if secondary_hit["match_count"] == 1:
            crosscheck = ("secondary_unique_primary_not_unique" if hit["match_count"] != 1 else
                          "secondary_unique_same_page_span" if all(secondary_hit[k] == hit[k] for k in ("locator_start", "locator_end")) else "secondary_locator_disagrees")
        direct_agrees = direct_hit["match_count"] == 1 and hit["match_count"] == 1 and all(direct_hit[k] == hit[k] for k in ("locator_start", "locator_end"))
        doi_agrees = original_doi == row.get("doi", "").strip().lower() and bool(original_doi)
        effective = hit["match_count"] == 1 and source_binding != "not_confirmed" and doi_agrees and (method == "exact_publisher_xml_node_span" or direct_agrees) and crosscheck != "secondary_locator_disagrees"
        original_page_relation = "no_original_page_or_not_comparable"
        if effective and "xml" not in method and row["page_hint"].isdigit():
            original_page_relation = "original_page_inside_recovered_span" if int(hit["locator_start"]) <= int(row["page_hint"]) <= int(hit["locator_end"]) else "original_page_outside_recovered_anchor_span"
        locators.append({"evidence_id": eid, "paper_id": pid, "original_page_hint": row["page_hint"],
                         "locator_status": state, "locator_type": "xml_node" if "xml" in method else "pdf_page",
                         **hit, "source_sha256": original_hash, "anchor_sha256": hashlib.sha256(row["evidence_anchor"].encode()).hexdigest(),
                         "method": method, "secondary_parser_check": crosscheck,
                         "original_pdf_recheck": "unique_same_page_span" if direct_agrees else "not_confirmed" if direct else "not_applicable_or_unavailable",
                         "source_binding": source_binding, "evidence_metadata_doi_agrees": str(doi_agrees).lower(),
                         "effective_locator_status": "source_verified_location_only" if effective else "provisional_or_unresolved",
                         "original_page_relation": original_page_relation,
                         "scalar_anchor_check": scalar_anchor_check(row),
                         "scientific_status": "location_only_not_measurement_certification"})
        if eid in warnings:
            value, flag = semantic(row)
            semantics.append({"evidence_id": eid, "recorded_wavelength_scalar": value,
                              "semantic_assessment": flag, "source_location_status": state,
                              "action": "withhold_wavelength_use_pending_field_resolution" if flag == "same_scalar_in_explicit_geometry_phrase" else "retain_broad_warning",
                              "replacement_value": "", "replacement_field": "",
                              "assessment_status": "automatic_diagnostic_not_human_certified"})
    tables = {"locators": locators, "semantic_assessments": semantics, "source_assets": source_assets}
    db = sqlite3.connect(out / "traceability.sqlite")
    for name, rows in tables.items():
        fields = list(rows[0])
        db.execute("CREATE TABLE " + name + "(" + ",".join(f + " TEXT" for f in fields) + ")")
        db.executemany("INSERT INTO " + name + " VALUES(" + ",".join("?" for _ in fields) + ")",
                       [tuple(str(r[k]) for k in fields) for r in rows])
        csv_write(out / (name + ".csv"), rows, fields)
    db.execute("CREATE UNIQUE INDEX locator_identity ON locators(evidence_id)")
    db.execute("CREATE UNIQUE INDEX assessment_identity ON semantic_assessments(evidence_id)")
    db.commit()
    db.close()
    summary = {"base_database_sha256": sha(base), "private_archive_sha256": sha(archive),
               "source_metadata_sha256": sha(meta_path), "target_records": len(target),
               "original_missing_page_records": len(missing),
               "target_sources": len(source_assets),
               "location_status_counts": dict(Counter(r["locator_status"] for r in locators)),
               "missing_page_location_status": dict(Counter(r["locator_status"] for r in locators if r["evidence_id"] in missing)),
               "secondary_parser_checks": dict(Counter(r["secondary_parser_check"] for r in locators if r["locator_type"] == "pdf_page")),
               "semantic_counts": dict(Counter(r["semantic_assessment"] for r in semantics)),
               "effective_location_counts": dict(Counter(r["effective_locator_status"] for r in locators)),
               "missing_page_effective_location_counts": dict(Counter(r["effective_locator_status"] for r in locators if r["evidence_id"] in missing)),
               "source_binding_counts": dict(Counter(r["source_binding"] for r in source_assets)),
               "original_page_relation_counts": dict(Counter(r["original_page_relation"] for r in locators)),
               "scalar_anchor_check_counts": dict(Counter(r["scalar_anchor_check"] for r in locators)),
               "new_certified_measurements": 0, "original_rows_modified": 0}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    (private / "source_assets_and_blocks.json").write_text(json.dumps(private_assets, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    for dest in (out, private):
        (dest / "manifest.json").write_text(json.dumps({p.name: sha(p) for p in sorted(dest.iterdir())}, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for k in ("base", "archive", "workspace", "output", "private-output", "pdf-python"):
        p.add_argument("--" + k, type=Path, required=True)
    a = p.parse_args()
    build(a.base, a.archive, a.workspace, a.output, a.private_output, a.pdf_python)
