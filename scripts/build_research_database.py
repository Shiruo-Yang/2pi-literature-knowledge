"""Build manuscript-aligned scientific tables from preserved literature evidence."""
import argparse
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from open_literature_database import connect
from research_evidence_quality import add_audit_sources, append_quality_tables
from literature_source_organization import apply_bibliography, append_source_tables


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity(prefix, payload):
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return prefix + hashlib.sha256(encoded.encode()).hexdigest()[:24]


def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))


def study_asset(root, name):
    current = root / 'study_context' / name
    return current if current.exists() else root / name


def normalize_doi(value):
    return re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', (value or '').strip(), flags=re.I).lower()


def number(value):
    if not re.fullmatch(r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?', value or ''):
        return None
    try:
        result = Decimal(value)
        return result if result.is_finite() else None
    except InvalidOperation:
        return None


def normalize_quantity(prop, value, unit):
    """Convert only explicit, recognized units; no inferred units or values."""
    unit = unit.strip().replace('µ', 'u').replace('μ', 'u')
    conversions = {}
    if 'power' in prop:
        conversions = {'W': ('mW', '1000'), 'mW': ('mW', '1'), 'uW': ('mW', '0.001')}
    elif prop == 'scan_speed':
        conversions = {'mm/s': ('um/s', '1000'), 'um/s': ('um/s', '1'), 'm/s': ('um/s', '1000000')}
    elif prop == 'pulse_duration':
        conversions = {'fs': ('fs', '1'), 'ps': ('fs', '1000'), 'ns': ('fs', '1000000'), 's': ('fs', '1000000000000000')}
    elif prop == 'dwell_time':
        conversions = {'ms': ('ms', '1'), 's': ('ms', '1000'), 'us': ('ms', '0.001')}
    elif prop == 'repetition_rate':
        conversions = {'MHz': ('MHz', '1'), 'kHz': ('MHz', '0.001'), 'Hz': ('MHz', '0.000001')}
    elif prop in {'line_width', 'line_height', 'static_voxel_width', 'static_voxel_height', 'reported_wavelength_unspecified', 'laser_wavelength_reported'}:
        conversions = {'nm': ('nm', '1'), 'um': ('nm', '1000'), 'mm': ('nm', '1000000')}
    target, factor = conversions.get(unit, (unit, '1'))
    quantity = value * Decimal(factor)
    text = format(quantity.normalize(), 'f') if quantity else '0'
    method = 'explicit_unit_scale' if factor != '1' else 'identity_or_reported_unit_retained'
    return text, target, method


EQUIVALENT_REPRESENTATIONS = {
    'power_raw': 'reported_power_unspecified', 'power_mW': 'reported_power_unspecified',
    'scan_speed_raw': 'scan_speed', 'scan_speed_um_s': 'scan_speed',
    'threshold_power_raw': 'polymerization_threshold_power', 'threshold_power_mW': 'polymerization_threshold_power',
    'objective_NA': 'objective_numerical_aperture', 'objective_na': 'objective_numerical_aperture',
}


def observation_key(row, taxonomy, value, unit, contexts):
    # Known raw/converted pairs may merge only when source, exact anchor,
    # full context membership, quantity and restriction status also agree.
    variant = EQUIVALENT_REPRESENTATIONS.get(row['field_name'], row['field_name'])
    unique = '' if row['field_name'] in EQUIVALENT_REPRESENTATIONS and contexts and unit and row['anchor_sha256'] else row['evidence_id']
    return [row['source_key'], taxonomy['canonical_property'], variant, value, unit,
            row['anchor_sha256'] or row['evidence_id'], contexts,
            row['component_use_action'], row['numeric_use_status'], row['external_evidence_use'], row['use_status'], unique]


def export_table(db, directory, name, data, fields, constraints=''):
    db.execute('CREATE TABLE ' + name + '(' + ','.join(f + ' TEXT' for f in fields) + (',' + constraints if constraints else '') + ')')
    serialized = [{k: str(r.get(k, '')) for k in fields} for r in data]
    db.executemany('INSERT INTO ' + name + ' VALUES(' + ','.join('?' for _ in fields) + ')', [tuple(r[k] for k in fields) for r in serialized])
    with (directory / (name + '.csv')).open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(serialized)
    return len(serialized)


def build(root, output, metadata=None):
    if output.exists():
        raise ValueError('Fresh staging output required.')
    cfg_path = root / 'configs/research_database.json'
    cfg = json.loads(cfg_path.read_text())
    dictionary = {}
    for group in cfg['groups']:
        for field in group['fields']:
            if field in dictionary:
                raise ValueError('Duplicate field taxonomy: ' + field)
            dictionary[field] = {k: v for k, v in group.items() if k != 'fields'} | {'original_field': field}
    source = connect(root)
    source.row_factory = sqlite3.Row
    evidence = [dict(r) for r in source.execute('SELECT * FROM current_evidence ORDER BY evidence_id')]
    if set(dictionary) != {r['field_name'] for r in evidence}:
        raise ValueError('Field dictionary must cover precisely all current original fields.')
    output.mkdir(parents=True)
    assets = []
    def asset(label, path):
        assets.append({'asset_id': label, 'sha256': fingerprint(path)})
    asset('base_database', root / 'data/literature/literature.sqlite')
    asset('traceability_database', root / 'data/literature/traceability/traceability.sqlite')
    asset('field_use_decisions', root / 'configs/literature_field_use_decisions.json')
    asset('research_taxonomy', cfg_path)
    asset('builder', Path(__file__))
    audit_path = root / 'inputs/source_audit_records.json'
    policy_path = root / 'configs/evidence_use_policy.json'
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    policy = json.loads(policy_path.read_text(encoding='utf-8'))
    asset('source_audit_projection', audit_path)
    asset('evidence_use_policy', policy_path)
    asset('evidence_quality_builder', Path(__file__).with_name('research_evidence_quality.py'))
    zotero_path = root / 'inputs/zotero_bibliography.json'
    cleaned_path = root / 'inputs/zotero_metadata_cleaned.csv'
    cleanup_path = root / 'inputs/openrefine_cleanup.json'
    pilot_path = root / 'inputs/document_parser_pilot.json'
    bindings_path = root / 'inputs/document_binding_checks.json'
    zotero = json.loads(zotero_path.read_text(encoding='utf-8'))
    cleanup = json.loads(cleanup_path.read_text(encoding='utf-8'))
    parser_reports = json.loads(pilot_path.read_text(encoding='utf-8'))['records']
    binding_checks = json.loads(bindings_path.read_text(encoding='utf-8'))['records']
    if cleanup['input_sha256'] != fingerprint(zotero_path) or cleanup['output_sha256'] != fingerprint(cleaned_path):
        raise ValueError('OpenRefine projection checksums do not match bibliography inputs.')
    for label, path in (('zotero_bibliography', zotero_path), ('zotero_metadata_cleaned', cleaned_path),
                        ('openrefine_cleanup', cleanup_path), ('document_parser_pilot', pilot_path),
                        ('document_binding_checks', bindings_path),
                        ('source_organization_builder', Path(__file__).with_name('literature_source_organization.py'))):
        asset(label, path)
    metadata_by_doi = defaultdict(list)
    if metadata:
        asset('existing_literature_metadata', metadata)
        for i, r in enumerate(rows(metadata), 1):
            if normalize_doi(r.get('doi')):
                metadata_by_doi[normalize_doi(r['doi'])].append((i, r))
    metadata_links, conflicts, papers = [], [], []
    for r in source.execute('SELECT * FROM base.sources ORDER BY source_key'):
        paper = dict(r)
        paper['base_year'] = paper['year']
        paper['base_journal'] = paper['journal']
        paper['publication_type'] = 'not_classified'
        paper['primary_experiment_source_status'] = 'not_assessed'
        paper['field_evidence_count'] = sum(e['source_key'] == paper['source_key'] for e in evidence)
        for field in ('year', 'journal'):
            candidates = [(i, m[field].strip()) for i, m in metadata_by_doi[paper['doi']] if m.get(field, '').strip()]
            if field == 'year':
                candidates = [(i, v) for i, v in candidates if re.fullmatch(r'\d{4}', v)]
            values = sorted({v for _, v in candidates})
            if not paper[field] and len(values) == 1:
                paper[field] = values[0]
                for i, value in candidates:
                    metadata_links.append({'source_key': paper['source_key'], 'field_name': field, 'reported_value': value, 'asset_id': 'existing_literature_metadata', 'input_row': i, 'action': 'fill_empty_by_exact_doi'})
            elif values and (len(values) > 1 or paper[field] not in values):
                format_key = lambda value: re.sub(r'[^a-z0-9]', '', value.casefold())
                formatting_only = bool(paper[field]) and all(format_key(v) == format_key(paper[field]) for v in values)
                conflicts.append({'source_key': paper['source_key'], 'field_name': field, 'base_value': paper[field], 'candidate_values': ';'.join(values), 'difference_type': 'formatting_variant' if formatting_only else 'unresolved_content_conflict', 'action': 'retain_base_spelling' if formatting_only else 'retain_base_and_flag_conflict'})
        papers.append(paper)
    added_audit_sources = add_audit_sources(papers, audit)
    bibliography_updates, bibliography_differences = apply_bibliography(papers, rows(cleaned_path))
    entities = [dict(r) for r in source.execute('SELECT * FROM base.entities ORDER BY entity_id')]
    accepted = [dict(r) for r in source.execute('SELECT * FROM base.accepted_identities ORDER BY entity_id')]
    compounds, assignments, compound_by_entity = {}, [], {}
    for row in accepted:
        cid = identity('CMP-', row['inchikey'])
        compound_by_entity[row['entity_id']] = cid
        compounds.setdefault(cid, {'compound_id': cid, 'recorded_inchikey': row['inchikey'], 'display_name': row['canonical_name'], 'canonical_smiles': row['canonical_smiles'], 'molecular_formula': row['molecular_formula'], 'identity_status': 'inherited_accepted_identity_not_revalidated'})
        assignments.append({'entity_id': row['entity_id'], 'compound_id': cid, 'source_key': next(e['source_key'] for e in entities if e['entity_id'] == row['entity_id']), 'source_location': row['source_location'], 'original_identity_status': row['original_status'], 'confidence_tier': row['confidence_tier']})
    condition_ids = defaultdict(list)
    for r in source.execute('SELECT * FROM base.condition_members ORDER BY cluster_id,evidence_id'):
        condition_ids[r['evidence_id']].append(r['cluster_id'])
    accepted_links = defaultdict(set)
    evidence_compounds = []
    for r in source.execute('SELECT * FROM base.evidence_entity_links ORDER BY link_id'):
        if r['entity_id'] in compound_by_entity:
            accepted_links[r['evidence_id']].add(compound_by_entity[r['entity_id']])
            evidence_compounds.append({'link_id': r['link_id'], 'evidence_id': r['evidence_id'], 'entity_id': r['entity_id'], 'compound_id': compound_by_entity[r['entity_id']], 'original_link_status': r['original_status'], 'match_basis': r['match_basis'], 'confidence': r['confidence'], 'measurement_ownership': 'not_certified_by_identity_link'})
    prepared, bucket_fields = {}, defaultdict(Counter)
    for row in evidence:
        value = number(row['normalized_value'])
        unit = row['normalized_unit']
        if value is None:
            value, unit = number(row['raw_value']), row['raw_unit']
        if value is not None:
            scalar, unit, _ = normalize_quantity(dictionary[row['field_name']]['canonical_property'], value, unit)
            contexts = ';'.join(sorted(condition_ids[row['evidence_id']]))
            key = observation_key(row, dictionary[row['field_name']], scalar, unit, contexts) + [sorted(accepted_links[row['evidence_id']])]
            token = json.dumps(key)
            prepared[row['evidence_id']] = (key, token)
            bucket_fields[token][row['field_name']] += 1
    observations, members, index = {}, [], []
    for row in evidence:
        definition = dictionary[row['field_name']]
        contexts = ';'.join(sorted(condition_ids[row['evidence_id']]))
        value = number(row['normalized_value'])
        unit, value_basis = row['normalized_unit'], 'inherited_normalized_value'
        if value is None:
            value = number(row['raw_value'])
            unit, value_basis = row['raw_unit'], 'public_raw_scalar'
        elif not unit:
            # A missing normalized unit is not inferred from raw units.
            value_basis = 'inherited_normalized_value_unit_missing'
        oid = ''
        if value is not None:
            scalar, unit, conversion = normalize_quantity(definition['canonical_property'], value, unit)
            key, token = prepared[row['evidence_id']]
            if any(n > 1 for n in bucket_fields[token].values()):
                key = key + [row['evidence_id']]
            oid = identity('OBS-', key)
            if oid not in observations:
                observations[oid] = {'observation_id': oid, 'source_key': row['source_key'], 'module_id': definition['module_id'], 'canonical_property': definition['canonical_property'], 'scientific_class': definition['scientific_class'], 'reported_variant': EQUIVALENT_REPRESENTATIONS.get(row['field_name'], row['field_name']), 'value': scalar, 'unit': unit, 'value_qualifier': 'not_resolved_from_public_projection', 'measurement_wavelength_nm': '', 'measurement_solvent': '', 'measurement_method': '', 'temperature_K': '', 'peak_definition': '', 'condition_assignment_status': 'context_links_only_not_measurement_conditions', 'context_ids': contexts, 'anchor_sha256': row['anchor_sha256'], 'value_status': 'reported_scalar_candidate', 'interpretation': definition['interpretation'], 'compound_ids': ';'.join(sorted(accepted_links[row['evidence_id']])), 'identity_link_status': 'source_local_identity_link_only' if accepted_links[row['evidence_id']] else 'unresolved_measurement_identity', 'component_use_action': row['component_use_action'], 'numeric_use_status': row['numeric_use_status'], 'external_evidence_use': row['external_evidence_use'], 'measurement_certification': 'not_newly_certified'}
            else:
                ids = set(observations[oid]['compound_ids'].split(';')) - {''}
                ids.update(accepted_links[row['evidence_id']])
                observations[oid]['compound_ids'] = ';'.join(sorted(ids))
                observations[oid]['identity_link_status'] = 'source_local_identity_link_only' if ids else 'unresolved_measurement_identity'
            members.append({'observation_id': oid, 'evidence_id': row['evidence_id'], 'original_field': row['field_name'], 'value_basis': value_basis, 'unit_normalization': conversion})
        index.append({'evidence_id': row['evidence_id'], 'source_key': row['source_key'], 'module_id': definition['module_id'], 'original_field': row['field_name'], 'canonical_property': definition['canonical_property'], 'scientific_class': definition['scientific_class'], 'related_tasks': definition['related_tasks'], 'interpretation': definition['interpretation'], 'observation_id': oid, 'context_ids': contexts, 'accepted_compound_ids': ';'.join(sorted(accepted_links[row['evidence_id']])), 'original_page_hint': row['page_hint'], 'recovered_locator_type': row['recovered_locator_type'], 'recovered_locator_start': row['recovered_locator_start'], 'recovered_locator_end': row['recovered_locator_end'], 'location_status': row['effective_location_status'], 'original_status': row['original_status'], 'original_use_status': row['use_status'], 'component_use_action': row['component_use_action'], 'numeric_use_status': row['numeric_use_status'], 'external_evidence_use': row['external_evidence_use'], 'scalar_anchor_check': row['scalar_anchor_check'], 'anchor_sha256': row['anchor_sha256'], 'candidate_value_visibility': row['candidate_value_visibility']})
    knowledge = []
    for filename, idcol, kind in (('domain_knowledge_registry.csv', 'knowledge_id', 'domain_prior'), ('mechanism_decision_registry.csv', 'mechanism_rule_id', 'mechanism_prior'), ('synthesis_route_evidence_registry.csv', 'route_evidence_id', 'synthesis_route_prior')):
        p = study_asset(root, filename)
        asset(filename, p)
        for row in rows(p):
            knowledge.append({'rule_id': row[idcol], 'module_id': cfg['rule_modules'][kind], 'rule_type': kind, 'family_or_criterion': row.get('normalized_criterion', row.get('family_scope', row.get('route_family', ''))), 'mechanism_lane': row.get('mechanism_lane', row.get('applicable_mechanism_lane', '')), 'statement': row['evidence_summary'], 'rule': row.get('normalized_rule', row.get('normalized_route_rule', '')), 'scope_limit': row.get('exclusion_or_claim_limit', row.get('scope_limit', row.get('scientific_rationale', ''))), 'coinitiator_context': row.get('coinitiator_context', ''), 'evidence_class': row.get('evidence_level', row.get('route_evidence_class', '')), 'original_status': row['status'], 'paper_use': row['computational_use'], 'downstream_use': row['downstream_use']})
    endpoints_path = study_asset(root, 'endpoint_representation_registry.csv')
    weights_path = study_asset(root, 'task_weight_policy_registry.csv')
    asset('endpoint_definitions', endpoints_path)
    asset('frozen_task_weight_policy', weights_path)
    endpoint_rows = {r['machine_readable_field']: r for r in rows(endpoints_path) if r['item_type'] == 'endpoint'}
    weight_rows = {r['task']: r for r in rows(weights_path)}
    profile = []
    profile_sources = []
    source_alias_map = {r['alias_id']: r['source_key'] for r in source.execute('SELECT * FROM base.source_aliases')}
    for task in cfg['task_order']:
        row, weight = endpoint_rows[task], weight_rows[task]
        profile.append({'task': task, 'display_name': row['human_readable_name'], 'definition': row['definition'], 'label_source': row['source'], 'original_unit': row['original_unit'], 'task_weight': weight['normalized_mt6_weight'], 'weight_role': 'frozen_deployment_utility_policy', 'related_context_evidence_count': sum(task in r['related_tasks'].split(';') for r in index), 'direct_task_labels_created': 0, 'scientific_role': row['computational_use'], 'interpretation': 'Literature records supply rationale or related context; no automatic assignment to this model endpoint.'})
        for alias in sorted(set(re.findall(r'\bSRC\d{3}\b', row['source']))):
            profile_sources.append({'task': task, 'source_key': source_alias_map[alias], 'inherited_source_alias': alias, 'support_role': 'endpoint_rationale_not_value_label_source'})
    context_rows = []
    conditions = {r['cluster_id']: dict(r) for r in source.execute('SELECT * FROM base.conditions')}
    for f in source.execute('SELECT * FROM base.formulations ORDER BY formulation_id'):
        c = conditions[f['cluster_id']]
        context_rows.append({'context_id': f['cluster_id'], 'formulation_id': f['formulation_id'], 'source_key': c['source_key'], 'page_hint': c['page_hint'], 'original_status': f['original_status'], 'context_quality': c['cluster_quality'], 'member_records': c['original_member_count'], 'scope': c['condition_scope'], 'experimental_status': 'extraction_context_not_confirmed_single_experiment'})
    module_rows = []
    for row in cfg['modules']:
        module_rows.append(row | {'field_records': sum(e['module_id'] == row['module_id'] for e in index), 'scalar_observation_candidates': sum(e['module_id'] == row['module_id'] for e in observations.values()), 'prior_rules': sum(e['module_id'] == row['module_id'] for e in knowledge)})
    db = sqlite3.connect(output / 'research.sqlite')
    db.execute('PRAGMA foreign_keys=ON')
    tables = {}
    def table(name, data, fields=None, constraints=''):
        tables[name] = export_table(db, output, name, data, fields or list(data[0]), constraints)
    table('papers', papers, constraints='PRIMARY KEY(source_key)')
    table('research_modules', module_rows, constraints='PRIMARY KEY(module_id)')
    table('compounds', sorted(compounds.values(), key=lambda r: r['compound_id']), constraints='PRIMARY KEY(compound_id)')
    table('compound_source_links', assignments, constraints='PRIMARY KEY(entity_id),FOREIGN KEY(compound_id) REFERENCES compounds(compound_id),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    table('formulation_contexts', context_rows, constraints='PRIMARY KEY(context_id),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    table('observations', sorted(observations.values(), key=lambda r: r['observation_id']), constraints='PRIMARY KEY(observation_id),FOREIGN KEY(source_key) REFERENCES papers(source_key),FOREIGN KEY(module_id) REFERENCES research_modules(module_id)')
    table('evidence_index', index, constraints='PRIMARY KEY(evidence_id),FOREIGN KEY(source_key) REFERENCES papers(source_key),FOREIGN KEY(module_id) REFERENCES research_modules(module_id)')
    table('evidence_compounds', evidence_compounds, constraints='PRIMARY KEY(link_id),FOREIGN KEY(evidence_id) REFERENCES evidence_index(evidence_id),FOREIGN KEY(compound_id) REFERENCES compounds(compound_id),FOREIGN KEY(entity_id) REFERENCES compound_source_links(entity_id)')
    table('observation_evidence', members, constraints='PRIMARY KEY(observation_id,evidence_id),FOREIGN KEY(observation_id) REFERENCES observations(observation_id),FOREIGN KEY(evidence_id) REFERENCES evidence_index(evidence_id)')
    table('knowledge_rules', knowledge, constraints='PRIMARY KEY(rule_id),FOREIGN KEY(module_id) REFERENCES research_modules(module_id)')
    table('rule_sources', [dict(r) for r in source.execute('SELECT * FROM base.rule_sources')], constraints='PRIMARY KEY(rule_id,source_key),FOREIGN KEY(rule_id) REFERENCES knowledge_rules(rule_id),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    table('six_task_profile', profile, constraints='PRIMARY KEY(task)')
    table('profile_sources', profile_sources, ['task', 'source_key', 'inherited_source_alias', 'support_role'], 'PRIMARY KEY(task,source_key),FOREIGN KEY(task) REFERENCES six_task_profile(task),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    table('field_dictionary', [dictionary[k] for k in sorted(dictionary)], constraints='PRIMARY KEY(original_field),FOREIGN KEY(module_id) REFERENCES research_modules(module_id)')
    table('metadata_provenance', metadata_links, ['source_key', 'field_name', 'reported_value', 'asset_id', 'input_row', 'action'], 'FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    table('metadata_conflicts', conflicts, ['source_key', 'field_name', 'base_value', 'candidate_values', 'difference_type', 'action'], 'FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    table('input_assets', assets, constraints='PRIMARY KEY(asset_id)')
    quality_summary = append_quality_tables(db, table, papers, audit, policy)
    organization_summary = append_source_tables(db, table, papers, zotero, bibliography_updates, bibliography_differences, parser_reports, binding_checks)
    db.executescript('''
    CREATE VIEW structural_priors AS SELECT * FROM knowledge_rules WHERE module_id='molecular_design';
    CREATE VIEW mechanism_rules AS SELECT * FROM knowledge_rules WHERE module_id='mechanism';
    CREATE VIEW synthesis_routes AS SELECT * FROM knowledge_rules WHERE module_id='synthesis';
    CREATE VIEW property_evidence AS SELECT * FROM evidence_index WHERE module_id='property_profile';
    CREATE VIEW processing_evidence AS SELECT * FROM evidence_index WHERE module_id='formulation_processing';
    ''')
    db.commit()
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
    summary = {'schema': cfg['schema'], 'tables': tables,
               'modules': module_rows,
               'field_records': len(index), 'original_field_names': len(dictionary),
               'canonical_properties': len({r['canonical_property'] for r in dictionary.values()}),
               'records_with_scalar_candidates': len(members), 'scalar_observation_candidates': len(observations),
               'representation_rows_linked_without_duplication': len(members) - len(observations),
               'accepted_structure_identifiers': len(compounds), 'source_local_identity_assignments': len(assignments),
               'metadata_cells_filled_by_exact_doi': len({(r['source_key'], r['field_name']) for r in metadata_links}),
               'metadata_cells_filled_by_exact_doi_total': len({(r['source_key'], r['field_name']) for r in metadata_links + bibliography_updates}),
               'missing_year_before': sum(not r['base_year'] for r in papers),
               'missing_year_after': sum(not r['year'] for r in papers),
               'missing_journal_before': sum(not r['base_journal'] for r in papers),
               'missing_journal_after': sum(not r['journal'] for r in papers),
               'metadata_content_conflicts': sum(r['difference_type'] == 'unresolved_content_conflict' for r in conflicts),
               'metadata_format_variants_retained': sum(r['difference_type'] == 'formatting_variant' for r in conflicts),
               'numerical_use_holds_preserved': sum(r['numeric_use_status'].startswith('withhold_') for r in index),
               'component_holds_preserved': sum(r['component_use_action'] != 'no_component_override' for r in index),
               'internal_document_exclusions_preserved': sum(r['external_evidence_use'].startswith('exclude_') for r in index),
               'new_certified_measurements': 0, 'new_training_labels': 0,
               'existing_audit_sources_added': len(added_audit_sources),
               'evidence_quality': quality_summary,
               'source_organization': organization_summary,
               'observation_definition': 'A source-anchored scalar candidate; compound ownership and experimental conditions may still be unresolved.',
               'foreign_key_check': [], 'integrity_check': 'ok'}
    (output / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8', newline='\n')
    db.close()
    source.close()
    (output / 'manifest.json').write_text(json.dumps({p.name: fingerprint(p) for p in sorted(output.iterdir())}, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--metadata', type=Path, default=Path(__file__).resolve().parents[1] / 'inputs/bibliographic_metadata.csv')
    a = p.parse_args()
    build(a.root, a.output, a.metadata)
