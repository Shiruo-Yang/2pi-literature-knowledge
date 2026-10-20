"""Optional local recheck of Zotero facts, original files and parser fingerprints.

No text, source images, private paths or model labels are exported. Run locally
against the retained private archive; this is not a semantic-accuracy benchmark.
"""
import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def verify(root, stage):
    public = json.loads((root / 'inputs/zotero_bibliography.json').read_text(encoding='utf-8'))
    private = json.loads((stage / 'zotero_documents.private.json').read_text(encoding='utf-8'))
    assert digest(root / 'inputs/zotero_bibliography.json') == private['public_projection_sha256']
    library = Path(private['library_path'])
    db = sqlite3.connect('file:' + library.resolve().as_posix() + '?mode=ro', uri=True)
    db.execute('PRAGMA query_only=ON')
    db.execute('BEGIN')
    for row in public['records']:
        values = dict(db.execute('''SELECT f.fieldName,v.value FROM items i
            JOIN itemData d USING(itemID) JOIN fields f USING(fieldID)
            JOIN itemDataValues v USING(valueID) WHERE i.key=?''', (row['zotero_item_key'],)))
        native_doi = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', values.get('DOI', '').strip(), flags=re.I).lower()
        assert row['doi'] == native_doi
        assert row['title'] == values.get('title', '').strip()
        assert row['journal'] == values.get('publicationTitle', '').strip()
        years = re.findall(r'\b(?:19|20)\d{2}\b', values.get('date', ''))
        assert row['year'] == (years[0] if years else '')
    db.rollback()
    db.close()
    docs = {r['document_id']: r for r in private['documents']}
    original_hashes = set()
    for row in docs.values():
        assert digest(Path(row['local_pdf'])) == row['document_sha256']
        original_hashes.add(row['document_sha256'])
    checks = json.loads((root / 'inputs/document_binding_checks.json').read_text(encoding='utf-8'))['records']
    for row in checks:
        assert row['document_sha256'] == docs[row['document_id']]['document_sha256']
        path = stage / 'first_pages_checked' / (row['document_sha256'] + '.json')
        assert digest(path) == row['page_output_sha256']
        payload = json.loads(path.read_text(encoding='utf-8'))
        native = unicodedata.normalize('NFKC', payload['text']).casefold()
        literal = re.escape(row['doi'].casefold()) + r'(?![a-z0-9])'
        found = bool(re.search(literal, native) or re.search(literal, ''.join(native.split())))
        assert found == (row['expected_doi_literal_found'] == 'true')
    pilot = json.loads((root / 'inputs/document_parser_pilot.json').read_text(encoding='utf-8'))
    for name, value in pilot['private_artifact_hashes'].items():
        filename = {'selection_manifest_sha256': 'parser_manifest.private.json',
                    'runtime_observations_sha256': 'parser_runtime_observations.json'}.get(name)
        path = stage / filename if filename else stage / name.removesuffix('_status_sha256') / 'status.json'
        assert digest(path) == value
    table_artifacts = {}
    for row in pilot['records']:
        path = stage / row['tool'] / (row['document_id'] + '.json')
        if row['status'] != 'parsed':
            continue
        assert digest(path) == row['output_sha256']
        payload = json.loads(path.read_text(encoding='utf-8'))
        assert row['document_sha256'] == docs[row['document_id']]['document_sha256']
        if row['tool'] == 'docling':
            assert len(payload['tables']) == int(row['table_count'])
            for index, table in enumerate(payload['tables']):
                assert any(int(p['page_no']) == int(row['target_page']) for p in table['prov'])
                csv_path = stage / 'docling' / f'{row["document_id"]}_table_{index}.csv'
                table_artifacts[csv_path.name] = digest(csv_path)
        else:
            assert int(row['target_page']) in {int(p['page_num']) for p in payload['pages']}
    return {'status': 'passed', 'zotero_bibliography_rows_rechecked': len(public['records']),
            'original_pdf_links_rehashed': len(docs), 'unique_pdf_hashes': len(original_hashes),
            'first_page_checks_recomputed': len(checks), 'parser_output_hashes_checked': len(pilot['records']),
            'private_table_artifact_sha256': table_artifacts,
            'scientific_accuracy_measured': False, 'zotero_mutations': 0, 'sealed_labels_read': 0}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--stage', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    if a.report.exists():
        raise ValueError('Fresh verification report required.')
    result = verify(a.root, a.stage)
    a.report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result, indent=2))
