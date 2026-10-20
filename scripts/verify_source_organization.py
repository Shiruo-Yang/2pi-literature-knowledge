"""Check metadata/document organization against public inputs, independently."""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


def verify(root, directory):
    db = sqlite3.connect('file:' + (directory / 'research.sqlite').resolve().as_posix() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    projection = json.loads((root / 'inputs/zotero_bibliography.json').read_text(encoding='utf-8'))
    with (root / 'inputs/zotero_metadata_cleaned.csv').open(encoding='utf-8-sig', newline='') as handle:
        cleaned = list(csv.DictReader(handle))
    assert len(cleaned) == len(projection['records'])
    cleanup = json.loads((root / 'inputs/openrefine_cleanup.json').read_text(encoding='utf-8'))
    assert cleanup['input_sha256'] == hashlib.sha256((root / 'inputs/zotero_bibliography.json').read_bytes()).hexdigest()
    assert cleanup['output_sha256'] == hashlib.sha256((root / 'inputs/zotero_metadata_cleaned.csv').read_bytes()).hexdigest()
    for r, original in zip(cleaned, projection['records']):
        assert all(r[k] == str(v) for k,v in original.items())
        for field in ('title','journal'):
            assert r[field + '_clean'] == re.sub(r'\s+', ' ', original[field]).strip()
        assert r['doi_clean'] == original['doi'].strip().lower()
    papers = {r['source_key']: dict(r) for r in db.execute('SELECT * FROM papers')}
    updates = [dict(r) for r in db.execute('SELECT * FROM bibliography_updates')]
    for r in updates:
        original = cleaned[int(r['input_row']) - 1]
        field = r['field_name'] + '_clean' if r['field_name'] != 'year' else 'year'
        assert original['doi_clean'] == papers[r['source_key']]['doi']
        assert original['zotero_item_key'] == r['zotero_item_key']
        assert original[field] == r['after_value'] == papers[r['source_key']][r['field_name']]
        assert not r['before_value'] and r['action'] == 'fill_empty_by_exact_doi_without_overwriting_existing'
    docs = {r['document_id']: dict(r) for r in db.execute('SELECT * FROM source_documents')}
    assert len(docs) == len(projection['documents'])
    groups = defaultdict(list)
    for r in projection['documents']:
        assert all(docs[r['document_id']][k] == str(v) for k,v in r.items())
        assert papers[r['source_key']]['doi'] == r['doi']
        if r['document_sha256']:
            groups[r['document_sha256']].append(r)
    for r in docs.values():
        group = groups.get(r['document_sha256'], [])
        assert int(r['same_content_source_count']) == len({d['source_key'] for d in group})
        assert int(r['same_content_attachment_count']) == len(group)
    for r in db.execute('SELECT * FROM document_reuse_groups'):
        group = groups[r['document_sha256']]
        assert len(group) == int(r['attachment_count'])
        assert len({d['source_key'] for d in group}) == int(r['source_count'])
        assert set(r['document_ids'].split(';')) == {d['document_id'] for d in group}
    checks = json.loads((root / 'inputs/document_binding_checks.json').read_text(encoding='utf-8'))['records']
    assert [dict(r) for r in db.execute('SELECT * FROM document_binding_checks')] == checks
    for r in checks:
        assert r['document_sha256'] == docs[r['document_id']]['document_sha256']
        assert r['measurement_certification'] == 'none'
        assert (r['expected_doi_literal_found'] == 'true') == (r['binding_status'] == 'expected_doi_literal_on_first_page_not_unique_identity_certification')
    pilot = json.loads((root / 'inputs/document_parser_pilot.json').read_text(encoding='utf-8'))['records']
    exported = [dict(r) for r in db.execute('SELECT * FROM document_parser_pilot')]
    assert len(pilot) == len(exported)
    for r, original in zip(exported, pilot):
        assert all(r[k] == str(v) for k,v in original.items())
        assert r['scientific_status'] == 'parser_output_only_not_measurement_certification'
        assert r['document_sha256'] == docs[r['document_id']]['document_sha256']
    dossiers = [dict(r) for r in db.execute('SELECT * FROM source_dossiers')]
    assert {r['source_key'] for r in dossiers} == papers.keys()
    for r in dossiers:
        key = r['source_key']
        for field in ('doi','title','year','journal'):
            assert r[field] == papers[key][field]
        related = [d for d in docs.values() if d['source_key'] == key]
        assert int(r['attachment_links']) == len(related)
        assert int(r['local_pdf_links']) == sum(d['availability'] == 'local_pdf_available' for d in related)
        assert int(r['unique_local_file_hashes']) == len({d['document_sha256'] for d in related if d['document_sha256']})
    summary = json.loads((directory / 'summary.json').read_text())['source_organization']
    assert summary['bibliography_cells_filled'] == len({(r['source_key'],r['field_name']) for r in updates})
    assert summary['parser_successes'] == sum(r['status'] == 'parsed' for r in pilot)
    assert summary['docling_candidate_tables'] == sum(int(r.get('table_count') or 0) for r in pilot if r['tool'] == 'docling')
    assert summary['parser_attempts_with_runtime_observations'] == sum(bool(json.loads(r.get('runtime_observations', '[]'))) for r in pilot)
    assert summary['new_experiment_labels'] == summary['zotero_library_mutations'] == 0
    total = json.loads((directory / 'summary.json').read_text())
    previous_fills = {(r['source_key'], r['field_name']) for r in db.execute('SELECT * FROM metadata_provenance')}
    assert total['metadata_cells_filled_by_exact_doi_total'] == len(previous_fills | {(r['source_key'], r['field_name']) for r in updates})
    assert total['missing_year_after'] == sum(not r['year'] for r in papers.values())
    assert total['missing_journal_after'] == sum(not r['journal'] for r in papers.values())
    result = {'status':'passed','bibliography_updates_checked':len(updates),'document_links_checked':len(docs),
              'first_page_checks':len(checks),'parser_attempts':len(pilot),'source_dossiers':len(dossiers),
              'source_documents_or_experiments_certified_by_count':False}
    db.close()
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--directory',type=Path,default=Path(__file__).resolve().parents[1]/'data/research')
    a=p.parse_args()
    print(json.dumps(verify(a.root,a.directory),indent=2))
