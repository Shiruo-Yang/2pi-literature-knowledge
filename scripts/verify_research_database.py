"""Check manuscript tables against their preserved base and current use decisions."""
import argparse
import csv
import hashlib
import json
import sqlite3
from collections import Counter
from decimal import Decimal
from pathlib import Path


def records(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def verify(root, directory, metadata=None):
    manifest = json.loads((directory / 'manifest.json').read_text())
    for name, expected in manifest.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == expected, name
    research = sqlite3.connect('file:' + (directory / 'research.sqlite').resolve().as_posix() + '?mode=ro', uri=True)
    research.row_factory = sqlite3.Row
    base = sqlite3.connect('file:' + (root / 'data/literature/literature.sqlite').resolve().as_posix() + '?mode=ro', uri=True)
    base.row_factory = sqlite3.Row
    assert research.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    assert not research.execute('PRAGMA foreign_key_check').fetchall()
    summary = json.loads((directory / 'summary.json').read_text())
    for table, count in summary['tables'].items():
        actual = [dict(r) for r in research.execute('SELECT * FROM ' + table)]
        assert len(actual) == count and records(directory / (table + '.csv')) == actual, table
    cfg = json.loads((root / 'configs/research_database.json').read_text())
    field_map = {f: g for g in cfg['groups'] for f in g['fields']}
    original = {r['evidence_id']: dict(r) for r in base.execute('SELECT * FROM evidence')}
    current = {r['evidence_id']: dict(r) for r in research.execute('SELECT * FROM evidence_index')}
    assert set(original) == set(current) and len(current) == 9257
    for eid, before in original.items():
        after = current[eid]
        assert after['original_field'] == before['field_name']
        assert after['original_status'] == before['original_status']
        assert after['original_use_status'] == before['use_status']
        assert after['original_page_hint'] == before['page_hint']
        assert after['anchor_sha256'] == before['anchor_sha256']
        assert after['source_key'] == before['source_key']
        assert after['module_id'] == field_map[before['field_name']]['module_id']
        assert after['canonical_property'] == field_map[before['field_name']]['canonical_property']
    overrides = json.loads((root / 'configs/literature_field_use_decisions.json').read_text())
    assert {r['evidence_id'] for r in overrides['records']} == {r['evidence_id'] for r in current.values() if r['component_use_action'] != 'no_component_override'}
    trace = sqlite3.connect('file:' + (root / 'data/literature/traceability/traceability.sqlite').resolve().as_posix() + '?mode=ro', uri=True)
    holds = {r[0] for r in trace.execute("SELECT evidence_id FROM locators WHERE scalar_anchor_check='literal_scalar_not_found_requires_value_anchor_review'")}
    assert holds == {r['evidence_id'] for r in current.values() if r['numeric_use_status'].startswith('withhold_')}
    internal_sources = {r['source_key'] for r in base.execute("SELECT source_key FROM sources WHERE scope='internal_workflow_candidate'")}
    assert {e for e, r in current.items() if r['source_key'] in internal_sources} == {e for e, r in current.items() if r['external_evidence_use'].startswith('exclude_')}
    old_identities = {r['entity_id']: dict(r) for r in base.execute('SELECT * FROM accepted_identities')}
    compound_keys = {r['compound_id']: r['recorded_inchikey'] for r in research.execute('SELECT * FROM compounds')}
    assignment = {r['entity_id']: r['compound_id'] for r in research.execute('SELECT * FROM compound_source_links')}
    assert set(assignment) == set(old_identities)
    assert set(compound_keys.values()) == {r['inchikey'] for r in old_identities.values()}
    for eid, cid in assignment.items():
        assert compound_keys[cid] == old_identities[eid]['inchikey']
    members = [dict(r) for r in research.execute('SELECT * FROM observation_evidence')]
    observations = {r['observation_id']: dict(r) for r in research.execute('SELECT * FROM observations')}
    groups = {}
    for row in members:
        groups.setdefault(row['observation_id'], []).append(row)
        original_row = original[row['evidence_id']]
        observation = observations[row['observation_id']]
        assert observation['source_key'] == original_row['source_key']
        assert observation['anchor_sha256'] == original_row['anchor_sha256']
        assert observation['context_ids'] == current[row['evidence_id']]['context_ids']
        assert observation['measurement_certification'] == 'not_newly_certified'
        assert observation['numeric_use_status'] == current[row['evidence_id']]['numeric_use_status']
        expected = original_row['normalized_value'] if row['value_basis'].startswith('inherited_normalized_value') else original_row['raw_value']
        unit = original_row['normalized_unit'] if row['value_basis'].startswith('inherited_normalized_value') else original_row['raw_unit']
        old_value, value = Decimal(expected), Decimal(observation['value'])
        unit = unit.replace('µ', 'u').replace('μ', 'u')
        if observation['unit'] == unit:
            assert old_value == value
        else:
            factors = {('W', 'mW'): '1000', ('uW', 'mW'): '0.001', ('mm/s', 'um/s'): '1000', ('m/s', 'um/s'): '1000000', ('ps', 'fs'): '1000', ('ns', 'fs'): '1000000', ('s', 'fs'): '1000000000000000', ('s', 'ms'): '1000', ('us', 'ms'): '0.001', ('kHz', 'MHz'): '0.001', ('Hz', 'MHz'): '0.000001', ('um', 'nm'): '1000', ('mm', 'nm'): '1000000'}
            assert old_value * Decimal(factors[(unit, observation['unit'])]) == value
    assert set(groups) == set(observations)
    assert len({r['evidence_id'] for r in members}) == len(members)
    assert Counter(r['module_id'] for r in current.values()) == {r['module_id']: int(r['field_records']) for r in research.execute('SELECT * FROM research_modules')}
    profile = [dict(r) for r in research.execute('SELECT * FROM six_task_profile')]
    assert [r['task'] for r in profile] == cfg['task_order']
    assert all(r['direct_task_labels_created'] == '0' for r in profile)
    weights_path = root / 'study_context/task_weight_policy_registry.csv'
    if not weights_path.exists():
        weights_path = root / 'task_weight_policy_registry.csv'
    weights = {r['task']: r['normalized_mt6_weight'] for r in records(weights_path)}
    assert all(weights[r['task']] == r['task_weight'] for r in profile)
    base_rules = {r['rule_id'] for r in base.execute('SELECT * FROM rules')}
    assert base_rules == {r['rule_id'] for r in research.execute('SELECT * FROM knowledge_rules')}
    assert {tuple(r) for r in base.execute('SELECT rule_id,source_key FROM rule_sources')} == {tuple(r) for r in research.execute('SELECT rule_id,source_key FROM rule_sources')}
    if metadata:
        inputs = {r['asset_id']: r['sha256'] for r in research.execute('SELECT * FROM input_assets')}
        assert hashlib.sha256(metadata.read_bytes()).hexdigest() == inputs['existing_literature_metadata']
        source_rows = records(metadata)
        papers = {r['source_key']: dict(r) for r in research.execute('SELECT * FROM papers')}
        for item in research.execute('SELECT * FROM metadata_provenance'):
            parent = source_rows[int(item['input_row']) - 1]
            assert parent['doi'].strip().lower() == papers[item['source_key']]['doi']
            assert parent[item['field_name']].strip() == item['reported_value']
            assert papers[item['source_key']][item['field_name']] == item['reported_value']
            assert not papers[item['source_key']]['base_' + item['field_name']]
    for path in directory.glob('*.csv'):
        # A drive letter must start a token; the trailing s:/ in https:// is not a local path.
        assert not __import__('re').search(r'(?i)(?<![a-z0-9])[a-z]:[\\/]', path.read_text(encoding='utf-8-sig')), path
    return {'status': 'passed', 'tables_checked': len(summary['tables']), 'preserved_field_records': len(current), 'task_profile_rows': len(profile), 'new_certified_labels': 0}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'data/research')
    p.add_argument('--metadata', type=Path)
    a = p.parse_args()
    print(json.dumps(verify(a.root, a.directory, a.metadata), indent=2))
