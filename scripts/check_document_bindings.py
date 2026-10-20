"""Local first-page DOI checks; no OCR, fuzzy title merge or identity certification."""
import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


def check(manifest, output, private):
    from liteparse import LiteParse
    import importlib.metadata
    if output.exists() or private.exists():
        raise ValueError('Fresh output files required.')
    private.mkdir(parents=True)
    docs = json.loads(manifest.read_text(encoding='utf-8'))['documents']
    groups = defaultdict(list)
    for row in docs:
        groups[row['document_sha256']].append(row)
    parser = LiteParse(ocr_enabled=False, target_pages='1', quiet=True, num_workers=2)
    records = []
    for index, (digest, members) in enumerate(sorted(groups.items()), 1):
        path = Path(members[0]['local_pdf'])
        result_sha, parsed, compact, native_text, error = '', False, '', '', ''
        try:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
            result = parser.parse(str(path))
            first = next(p for p in result.pages if p.page_num == 1)
            payload = {'page': 1, 'text': first.text,
                       'items': [{'text': t.text, 'x': t.x, 'y': t.y, 'width': t.width, 'height': t.height} for t in first.text_items]}
            target = private / (digest + '.json')
            target.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            result_sha = hashlib.sha256(target.read_bytes()).hexdigest()
            native_text = unicodedata.normalize('NFKC', first.text).casefold()
            compact = ''.join(native_text.split())
            parsed = bool(first.text.strip())
        except Exception as exc:
            error = type(exc).__name__
        source_count = len({r['source_key'] for r in members})
        for row in members:
            expected = row['doi'].casefold()
            # Preserve native word boundaries; whitespace removal alone can join
            # a DOI suffix to the following heading and produce a false absence.
            pattern = re.escape(expected) + r'(?![a-z0-9])'
            found = parsed and bool(re.search(pattern, native_text) or re.search(pattern, compact))
            records.append({'document_id': row['document_id'], 'source_key': row['source_key'], 'doi': row['doi'],
                            'document_sha256': digest, 'checked_page': '1', 'first_page_text_available': str(parsed).lower(),
                            'expected_doi_literal_found': str(found).lower(), 'page_output_sha256': result_sha,
                            'tool': 'LiteParse', 'tool_version': importlib.metadata.version('liteparse'),
                            'cross_source_shared_file': str(source_count > 1).lower(),
                            'binding_status': 'expected_doi_literal_on_first_page_not_unique_identity_certification' if found else
                            'expected_doi_not_found_requires_binding_review' if parsed else 'native_first_page_text_unavailable_no_ocr_attempted',
                            'failure_category': error, 'measurement_certification': 'none'})
        if index % 50 == 0:
            print(json.dumps({'unique_pdfs_checked': index, 'total': len(groups)}), flush=True)
    records.sort(key=lambda r: r['document_id'])
    summary = {'unique_pdf_contents_checked': len(groups), 'attachment_links_checked': len(records),
               'binding_status': dict(Counter(r['binding_status'] for r in records)),
               'distinct_source_identity_certification': False, 'new_measurement_labels': 0}
    output.write_text(json.dumps({'schema': 'first_page_doi_literal_checks', 'records': records, 'summary': summary}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--private-output', type=Path, required=True)
    a = p.parse_args()
    check(a.manifest, a.output, a.private_output)
