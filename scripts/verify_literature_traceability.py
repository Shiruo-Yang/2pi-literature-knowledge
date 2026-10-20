"""Independent assertions against original inputs; does not import the builder."""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET


def read(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def canonical(text):
    text = re.sub(r'---\s*Page\s+[0-9]+\s*---', '', text)
    return ''.join(unicodedata.normalize('NFKC', text).split()).casefold()


def verify(folder, private, base, archive):
    summary = json.loads((folder / 'summary.json').read_text())
    for destination in (folder, private):
        for name, expected in json.loads((destination / 'manifest.json').read_text()).items():
            assert digest(destination / name) == expected, name
    assert digest(base) == summary['base_database_sha256']
    assert digest(archive) == summary['private_archive_sha256']
    db = sqlite3.connect('file:' + base.resolve().as_posix() + '?mode=ro', uri=True)
    rawdb = sqlite3.connect('file:' + archive.resolve().as_posix() + '?mode=ro', uri=True)
    raw = {r['record_id']: r for (j,) in rawdb.execute("SELECT row_json FROM raw_records WHERE asset_key='candidates'") for r in [json.loads(j)]}
    missing = {r[0] for r in db.execute("SELECT evidence_id FROM evidence WHERE page_hint=''")}
    warnings = {r[0] for r in db.execute("SELECT object_id FROM quality_issues WHERE issue_type='possible_geometry_vs_wavelength_context_collision'")}
    locators = read(folder / 'locators.csv')
    assert len({r['evidence_id'] for r in locators}) == len(locators)
    assert {r['evidence_id'] for r in locators} == missing | warnings
    source_records = {r['paper_id']: r for r in read(folder / 'source_assets.csv')}
    assets = {r['paper_id']: r for r in json.loads((private / 'source_assets_and_blocks.json').read_text(encoding='utf-8'))}
    source_nodes = {}
    original_checks = 0
    for pid, a in assets.items():
        s = source_records[pid]
        if s['source_sha256']:
            original = Path(a['source_path'])
            assert digest(original) == s['source_sha256'], pid
            original_checks += 1
            if original.suffix == '.xml':
                root = ET.parse(original).getroot()
                # Independent breadth-first node address map, not builder recursion.
                nodes, todo = {}, [(root, '/' + root.tag.split('}')[-1] + '[1]')]
                while todo:
                    elem, address = todo.pop(0)
                    nodes[address] = elem
                    seen = Counter()
                    for child in elem:
                        tag = child.tag.split('}')[-1]
                        seen[tag] += 1
                        todo.append((child, address + '/' + tag + '[' + str(seen[tag]) + ']'))
                source_nodes[pid] = nodes
                for address, text in a['blocks']:
                    assert ' '.join(x.strip() for x in nodes[address].itertext() if x.strip()) == text
                if s['source_binding'] == 'doi_in_original_article_metadata':
                    assert s['source_doi'] in [(e.text or '').strip().lower() for e in root.iter() if e.tag.split('}')[-1] == 'article-id' and e.get('pub-id-type') == 'doi']
            elif s['source_binding'] == 'doi_in_first_two_pdf_pages':
                assert canonical(s['source_doi']) in canonical(' '.join(t for _, t in a['direct_pdf_blocks'][:2]))
        if s['cached_text_sha256']:
            cached = Path(a['cached_text_path'])
            assert digest(cached) == s['cached_text_sha256']
            if s['method'] == 'exact_cached_pdf_page_span':
                chunks = re.split(r'---\s*Page\s+(\d+)\s*---', cached.read_text(encoding='utf-8-sig'))
                assert a['blocks'] == [[chunks[i], chunks[i + 1]] for i in range(1, len(chunks), 2)]
        if a['direct_pdf_blocks']:
            assert json.loads((private / (pid + '_original_pdf_pages.json')).read_text(encoding='utf-8')) == a['direct_pdf_blocks']
    verified = 0
    for r in locators:
        original = raw[r['evidence_id']]
        assert r['original_page_hint'] == original['page_hint']
        assert hashlib.sha256(original['evidence_anchor'].encode()).hexdigest() == r['anchor_sha256']
        num = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?'
        unit = original.get('raw_unit', '').strip()
        val = original.get('raw_value', '').strip()
        match = re.fullmatch('(' + num + ')' + (r'\s*' + re.escape(unit) if unit else ''), val) or re.fullmatch('(' + num + ')', val)
        expected_value_check = 'not_applicable_nonscalar_or_empty'
        if match:
            expected_value_check = 'literal_scalar_present_not_endpoint_certified' if re.search(r'(?<![\w.])' + re.escape(match[1]) + r'(?![\w.])', original['evidence_anchor']) else 'literal_scalar_not_found_requires_value_anchor_review'
        assert r['scalar_anchor_check'] == expected_value_check
        a = assets[r['paper_id']]
        needle = canonical(original['evidence_anchor'])
        blocks = a['blocks']
        joined = ''.join(canonical(t) for _, t in blocks)
        hits = [m.start() for m in re.finditer('(?=' + re.escape(needle) + ')', joined)] if len(needle) >= 60 else []
        assert len(hits) == int(r['match_count'])
        if len(hits) == 1:
            start, end = hits[0], hits[0] + len(needle)
            assert (start, end) == (int(r['normalized_start']), int(r['normalized_end']))
            offsets, cursor = [], 0
            for label, text in blocks:
                nxt = cursor + len(canonical(text))
                if cursor < end and nxt > start:
                    offsets.append(label)
                cursor = nxt
            assert offsets[0] == r['locator_start'] and offsets[-1] == r['locator_end']
        else:
            assert not r['locator_start'] and not r['locator_end']
        if r['effective_locator_status'] == 'source_verified_location_only':
            assert len(hits) == 1 and r['source_binding'] != 'not_confirmed'
            assert r['evidence_metadata_doi_agrees'] == 'true'
            assert original['doi'].lower().strip() == source_records[r['paper_id']]['source_doi']
            if r['locator_type'] == 'pdf_page':
                assert r['original_pdf_recheck'] == 'unique_same_page_span'
                page_text = ''.join(canonical(t) for _, t in a['direct_pdf_blocks'])
                starts = [m.start() for m in re.finditer('(?=' + re.escape(needle) + ')', page_text)]
                assert len(starts) == 1
                cursor, labels = 0, []
                for label, text in a['direct_pdf_blocks']:
                    nxt = cursor + len(canonical(text))
                    if cursor < starts[0] + len(needle) and nxt > starts[0]:
                        labels.append(label)
                    cursor = nxt
                assert labels[0] == r['locator_start'] and labels[-1] == r['locator_end']
            verified += 1
    assert dict(Counter(r['effective_locator_status'] for r in locators if r['evidence_id'] in missing)) == summary['missing_page_effective_location_counts']
    assert dict(Counter(r['scalar_anchor_check'] for r in locators)) == summary['scalar_anchor_check_counts']
    assessments = read(folder / 'semantic_assessments.csv')
    assert {r['evidence_id'] for r in assessments} == warnings
    for r in assessments:
        assert r['replacement_value'] == r['replacement_field'] == ''
    check_db = sqlite3.connect('file:' + (folder / 'traceability.sqlite').resolve().as_posix() + '?mode=ro', uri=True)
    assert check_db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    for table in ('locators', 'semantic_assessments', 'source_assets'):
        cur = check_db.execute('SELECT * FROM ' + table)
        keys = [x[0] for x in cur.description]
        assert [dict(zip(keys, row)) for row in cur] == read(folder / (table + '.csv'))
    for f in folder.iterdir():
        if f.suffix in {'.csv', '.json'}:
            assert not re.search(r'(?i)[a-z]:[\\/]', f.read_text(encoding='utf-8-sig'))
    return {'status': 'passed', 'target_rows_checked': len(locators), 'original_source_files_hashed': original_checks,
            'source_verified_locations': verified, 'base_unchanged': digest(base) == summary['base_database_sha256'],
            'measurement_certification': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    for key in ('folder', 'private', 'base', 'archive'):
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(verify(a.folder, a.private, a.base, a.archive), indent=2))
