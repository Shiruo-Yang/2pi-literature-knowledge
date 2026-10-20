"""Select a bounded source-quality pilot without using model predictions/labels."""
import argparse
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path


def prepare(research, documents, old_assets, output, limit):
    if output.exists():
        raise ValueError('Fresh pilot manifest required.')
    docs = json.loads(documents.read_text(encoding='utf-8'))['documents']
    assets = json.loads(old_assets.read_text(encoding='utf-8'))
    old = {str(Path(r['source_path']).resolve()): r for r in assets if r.get('source_path')}
    content_sources = defaultdict(set)
    for r in docs:
        content_sources[r['document_sha256']].add(r['source_key'])
    db = sqlite3.connect('file:' + research.resolve().as_posix() + '?mode=ro', uri=True)
    scores = dict(db.execute('''SELECT source_key,
        SUM(CASE WHEN numeric_use_status LIKE 'withhold_%' THEN 100 ELSE 0 END)+
        SUM(CASE WHEN module_id='property_profile' THEN 10 WHEN module_id='mechanism' THEN 3 ELSE 0 END)+
        SUM(CASE WHEN location_status='unresolved_location' THEN 1 ELSE 0 END)
        FROM evidence_index GROUP BY source_key'''))
    db.close()
    ordered = sorted(docs, key=lambda r: (-scores.get(r['source_key'], 0), r['source_key'],
                                         r['document_role'] != 'main_or_unspecified_attachment', r['document_id']))
    selected, used_sources, used_hashes = [], set(), set()
    for r in ordered:
        if r['source_key'] in used_sources or r['document_sha256'] in used_hashes or len(content_sources[r['document_sha256']]) > 1:
            continue
        cache = old.get(str(Path(r['local_pdf']).resolve()))
        if not cache or not cache.get('direct_pdf_blocks'):
            continue
        blocks = cache['direct_pdf_blocks']
        def table_score(block):
            text = block[1]
            return 10 * bool(re.search(r'(?im)^\s*Table\s*\d', text)) + 5 * bool(re.search(r'\bGM\b', text)) + 2 * bool(re.search(r'cross.section|solvent|triplet', text, re.I))
        target = max(blocks, key=lambda b: (table_score(b), -int(b[0])))
        selected.append({k: r[k] for k in ('document_id', 'source_key', 'doi', 'document_sha256', 'local_pdf')} |
                        {'target_page': int(target[0]), 'selection_basis': 'source_quality_gaps_and_table_keywords_not_prediction_error',
                         'prior_source_page_count': len(blocks), 'prior_table_keyword_score': table_score(target)})
        used_sources.add(r['source_key'])
        used_hashes.add(r['document_sha256'])
        if len(selected) == limit:
            break
    if len(selected) < limit:
        raise ValueError('Too few distinct eligible original PDFs: ' + str(len(selected)))
    payload = {'schema': 'bounded_document_parser_pilot', 'documents': selected,
               'policy': {'document_limit': limit, 'source_grouping': 'one_known_private_original_per_source_and_hash',
                          'shared_cross_source_hashes_excluded': True, 'new_label_certification': False}}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps([{k: r[k] for k in ('doi', 'target_page', 'prior_source_page_count')} for r in selected], indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--research', type=Path, required=True)
    p.add_argument('--documents', type=Path, required=True)
    p.add_argument('--old-assets', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--limit', type=int, default=10)
    a = p.parse_args()
    prepare(a.research, a.documents, a.old_assets, a.output, a.limit)
