"""Read-only Zotero snapshot, restricted to exact DOIs in the research corpus.

Exports bibliographic facts and document fingerprints, never PDFs, private
paths, notes or credentials. Duplicate parent items remain separate candidates.
"""
import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def doi(value):
    value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', value.strip(), flags=re.I).lower()
    return value if re.fullmatch(r'10\.\d{4,9}/\S+', value) else ''


def read_only(path):
    db = sqlite3.connect('file:' + path.resolve().as_posix() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db


def export(research, library, public, private):
    if public.exists() or private.exists():
        raise ValueError('Fresh output files required.')
    scientific = read_only(research)
    papers = {r['doi']: r['source_key'] for r in scientific.execute('SELECT * FROM papers') if r['doi'] and not r['scope'].startswith('internal_')}
    scientific.close()
    zot = read_only(library)
    zot.execute('BEGIN')
    candidates = defaultdict(list)
    for row in zot.execute('''SELECT d.itemID,v.value,i.key FROM itemData d JOIN fields f USING(fieldID)
       JOIN itemDataValues v USING(valueID) JOIN items i USING(itemID)
       WHERE f.fieldName='DOI' AND d.itemID NOT IN (SELECT itemID FROM deletedItems)'''):
        normalized = doi(row['value'])
        if normalized in papers:
            candidates[normalized].append((row['itemID'], row['key']))
    records, documents, private_documents = [], [], []
    seen_documents = set()
    for normalized in sorted(candidates):
        for item_id, key in sorted(candidates[normalized]):
            data = dict(zot.execute('''SELECT f.fieldName,v.value FROM itemData d JOIN fields f USING(fieldID)
                       JOIN itemDataValues v USING(valueID) WHERE d.itemID=?''', (item_id,)))
            year = re.search(r'\b(?:19|20)\d{2}\b', data.get('date', ''))
            records.append({'source_key': papers[normalized], 'doi': normalized, 'zotero_item_key': key,
                            'title': data.get('title', '').strip(), 'year': year.group() if year else '',
                            'journal': data.get('publicationTitle', '').strip(),
                            'item_status': 'exact_doi_metadata_not_source_fact_certification'})
            for att in zot.execute('''SELECT a.*,i.key AS attachment_key FROM itemAttachments a JOIN items i USING(itemID)
                         WHERE parentItemID=? AND a.itemID NOT IN (SELECT itemID FROM deletedItems)''', (item_id,)):
                if att['attachment_key'] in seen_documents:
                    continue
                seen_documents.add(att['attachment_key'])
                recorded_path = att['path'] or ''
                if recorded_path.startswith('storage:'):
                    path = library.parent / 'storage' / att['attachment_key'] / recorded_path[len('storage:'):]
                elif recorded_path and not recorded_path.startswith('attachments:'):
                    path = Path(recorded_path)
                else:
                    path = None
                exists = bool(path and path.is_file())
                is_pdf = exists and (path.suffix.lower() == '.pdf' or att['contentType'] == 'application/pdf')
                digest = sha(path) if is_pdf else ''
                # Name-based role suggestions never certify an SI/main relationship.
                role = 'supporting_information_candidate' if path and re.search(r'supplement|supporting|(?:^|[_ -])si(?:[_ .-]|$)', path.name, re.I) else 'main_or_unspecified_attachment'
                row = {'document_id': 'ZDOC-' + att['attachment_key'], 'source_key': papers[normalized], 'doi': normalized,
                       'zotero_parent_key': key, 'zotero_attachment_key': att['attachment_key'],
                       'document_sha256': digest, 'document_role': role,
                       'availability': 'local_pdf_available' if is_pdf else 'not_a_locally_resolved_pdf',
                       'source_binding': 'zotero_parent_doi_only_not_original_document_verified',
                       'access': 'private_local_attachment_not_redistributed'}
                documents.append(row)
                if is_pdf:
                    private_documents.append(row | {'local_pdf': str(path.resolve())})
    zot.rollback()
    zot.close()
    result = {'schema': 'exact_doi_zotero_bibliography_and_documents', 'records': records, 'documents': documents,
              'summary': {'matched_source_dois': len(candidates), 'matched_parent_items': len(records),
                          'duplicate_doi_groups': sum(len(v) > 1 for v in candidates.values()),
                          'local_pdf_attachments': len(private_documents),
                          'unique_local_pdf_hashes': len({r['document_sha256'] for r in private_documents})},
              'reader_sha256': sha(Path(__file__)), 'library_mutations': 0}
    public.parent.mkdir(parents=True, exist_ok=True)
    private.parent.mkdir(parents=True, exist_ok=True)
    public.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    private.write_text(json.dumps({'documents': private_documents, 'library_path': str(library),
                                 'public_projection_sha256': sha(public)}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--research', type=Path, required=True)
    p.add_argument('--library', type=Path, required=True)
    p.add_argument('--public-output', type=Path, required=True)
    p.add_argument('--private-output', type=Path, required=True)
    a = p.parse_args()
    export(a.research, a.library, a.public_output, a.private_output)
