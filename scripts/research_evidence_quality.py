"""Use-specific evidence assessment; deliberately no extraction of new labels."""
import hashlib
import json
from collections import Counter, defaultdict


def source_key(doi):
    return 'SRC-' + hashlib.sha256(('doi:' + doi.strip().lower()).encode()).hexdigest()[:24]


def add_audit_sources(papers, audit):
    """Add exact DOI references, never invent unavailable bibliographic metadata."""
    by_doi = {r['doi']: r for r in papers if r['doi']}
    roles = defaultdict(set)
    for r in audit['structures']:
        roles[r['doi']].add('structure_audit')
    for r in audit['measurements']:
        roles[r['doi']].add('source_measurement_audit')
    for r in audit['source_lineage']:
        roles[r['review_doi']].add('review_bibliographic_chain')
        roles[r['primary_doi']].add('referenced_primary_source')
    added = []
    for doi in sorted(roles):
        if doi in by_doi:
            continue
        row = {k: '' for k in papers[0]}
        row.update(source_key=source_key(doi), doi=doi, scope='existing_local_audit_reference_not_independence_certified',
                   publication_type='review' if 'review_bibliographic_chain' in roles[doi] else 'not_classified',
                   primary_experiment_source_status='source_measurement_audit_available' if 'source_measurement_audit' in roles[doi] else 'not_assessed',
                   field_evidence_count=0)
        papers.append(row)
        by_doi[doi] = row
        added.append(row['source_key'])
    papers.sort(key=lambda r: r['source_key'])
    return added


def assess_field(row, observation, policy):
    """A source-located candidate remains a candidate unless ownership is checked."""
    reasons = []
    internal = row['external_evidence_use'].startswith('exclude_')
    numeric_hold = row['numeric_use_status'].startswith('withhold_')
    component_hold = row['component_use_action'] != 'no_component_override'
    located = row['location_status'] == 'source_verified_location_only'
    if internal:
        reasons.append('internal_document_not_external_evidence')
    if numeric_hold:
        reasons.append('scalar_anchor_gap_pending_review')
    if component_hold:
        reasons.append('source_review_component_hold')
    if not located:
        reasons.append('source_verified_location_missing')
    if observation:
        if not observation['unit']:
            reasons.append('explicit_unit_missing')
        reasons.extend(policy['candidate_quantitative_requirements'])
    else:
        reasons.append('source_statement_interpretation_not_adjudicated')
    if row['canonical_property'] == policy['unresolved_wavelength_property']:
        reasons.append('wavelength_role_unresolved')
    return {
        'evidence_id': row['evidence_id'], 'source_key': row['source_key'], 'module_id': row['module_id'],
        'canonical_property': row['canonical_property'], 'observation_id': row['observation_id'],
        'record_kind': 'scalar_candidate' if observation else 'nonscalar_field_candidate',
        'source_location_check': 'verified_locator_only' if located else 'requires_source_location',
        'identity_link_check': 'source_local_identity_link_not_measurement_ownership' if row['accepted_compound_ids'] else 'no_accepted_identity_link',
        'unit_check': ('explicit_unit_present_not_semantically_certified' if observation['unit'] else 'missing') if observation else 'not_applicable_to_nonscalar_candidate',
        'max_permitted_use': 'provenance_only_internal_excluded' if internal else 'retrieval_only_with_component_or_numeric_hold' if numeric_hold or component_hold else 'source_review_candidate',
        'quantitative_comparison_ready': 'false', 'training_ready': 'false',
        'missing_requirements': json.dumps(reasons, separators=(',', ':')),
        'assessment_basis': 'deterministic_completeness_and_inherited_restrictions_not_semantic_accuracy',
    }


def append_quality_tables(db, table, papers, audit, policy):
    db.row_factory = __import__('sqlite3').Row
    index = [dict(r) for r in db.execute('SELECT * FROM evidence_index ORDER BY evidence_id')]
    obs = {r['observation_id']: dict(r) for r in db.execute('SELECT * FROM observations')}
    papers_by_doi = {r['doi']: r['source_key'] for r in papers if r['doi']}
    assessments = [assess_field(r, obs.get(r['observation_id']), policy) for r in index]
    table('evidence_readiness', assessments, constraints='PRIMARY KEY(evidence_id),FOREIGN KEY(evidence_id) REFERENCES evidence_index(evidence_id)')
    table('source_audits', audit['audit_sources'], constraints='PRIMARY KEY(audit_id)')
    structures = []
    for r in audit['structures']:
        structures.append(r | {'source_key': papers_by_doi[r['doi']], 'module_id': 'molecular_design',
                               'training_eligible': 'false', 'optical_label_created': 'false'})
    table('source_structures', structures, constraints='PRIMARY KEY(structure_record_id),FOREIGN KEY(source_key) REFERENCES papers(source_key),FOREIGN KEY(audit_id) REFERENCES source_audits(audit_id)')
    structure_map = {r['structure_record_id']: r for r in structures}
    measurements = []
    for r in audit['measurements']:
        if r['doi'] != structure_map[r['structure_record_id']]['doi']:
            raise ValueError('Measurement and structure source mismatch.')
        for k in ('training_eligible', 'final_test_eligible', 'global_sigma_max_eligible', 'independent_new_sample_claim', 'existing_training_record_replacement', 'original_database_curve_history_certified'):
            if r[k] != 'false':
                raise ValueError('Source-audit use boundary must remain false: ' + k)
        measurements.append(r | {'source_key': papers_by_doi[r['doi']], 'module_id': 'property_profile',
                                 'source_fact_use': 'citation_and_within_source_descriptive_comparison_with_conditions_and_limits',
                                 'cross_source_comparison_ready': 'false',
                                 'missing_conditions': 'pulse_duration;repetition_rate',
                                 'linked_field_observation_id': '', 'cross_database_duplicate_status': 'not_equated_or_deduplicated_with_legacy_field_candidates'})
    table('source_measurements', measurements, constraints='PRIMARY KEY(measurement_id),FOREIGN KEY(structure_record_id) REFERENCES source_structures(structure_record_id),FOREIGN KEY(source_key) REFERENCES papers(source_key),FOREIGN KEY(audit_id) REFERENCES source_audits(audit_id)')
    table('measurement_conditions', audit['measurement_conditions'], constraints='PRIMARY KEY(measurement_id,condition_name),FOREIGN KEY(measurement_id) REFERENCES source_measurements(measurement_id),FOREIGN KEY(audit_id) REFERENCES source_audits(audit_id)')
    lineage = [r | {'review_source_key': papers_by_doi[r['review_doi']], 'primary_source_key': papers_by_doi[r['primary_doi']]} for r in audit['source_lineage']]
    table('source_lineage', lineage, constraints='PRIMARY KEY(review_source_key,reference_number),FOREIGN KEY(review_source_key) REFERENCES papers(source_key),FOREIGN KEY(primary_source_key) REFERENCES papers(source_key),FOREIGN KEY(audit_id) REFERENCES source_audits(audit_id)')
    rule_links = defaultdict(set)
    for r in db.execute('SELECT * FROM rule_sources'):
        rule_links[r['rule_id']].add(r['source_key'])
    rule_assessments, core = [], []
    for r in db.execute('SELECT * FROM knowledge_rules ORDER BY rule_id'):
        support = sorted(rule_links[r['rule_id']])
        rule_assessments.append({
            'rule_id': r['rule_id'], 'module_id': r['module_id'], 'supporting_source_count': len(support),
            'scope_limit_present': str(bool(r['scope_limit'])).lower(),
            'coinitiator_context_present': str(bool(r['coinitiator_context'])).lower(),
            'source_link_completeness': 'citation_links_present' if support else 'missing_citation_links',
            'primary_experimental_support': 'not_systematically_adjudicated',
            'counterevidence_status': 'not_systematically_assessed',
            'candidate_specific_mechanism_proof': 'false', 'weight_optimality_evidence': 'false',
            'max_permitted_use': policy['core_rule_use'],
        })
        core.append({'record_id': r['rule_id'], 'record_type': 'knowledge_rule', 'module_id': r['module_id'],
                     'source_keys': ';'.join(support),
                     'description': r['statement'] + ' Scope: ' + r['scope_limit'] + (' Partner context: ' + r['coinitiator_context'] if r['coinitiator_context'] else ''),
                     'allowed_use': policy['core_rule_use'],
                     'readiness': 'existing_source_linked_prior_not_independently_revalidated',
                     'prohibited_use': 'candidate_mechanism_or_performance_proof;optimal_task_weights;training_label'})
    table('rule_readiness', rule_assessments, constraints='PRIMARY KEY(rule_id),FOREIGN KEY(rule_id) REFERENCES knowledge_rules(rule_id)')
    for r in db.execute('SELECT * FROM six_task_profile ORDER BY task'):
        keys = [s[0] for s in db.execute('SELECT source_key FROM profile_sources WHERE task=? ORDER BY source_key', (r['task'],))]
        core.append({'record_id': r['task'], 'record_type': 'endpoint_definition', 'module_id': 'property_profile',
                     'source_keys': ';'.join(keys), 'description': r['definition'], 'allowed_use': policy['core_profile_use'],
                     'readiness': 'frozen_definition_with_separate_computational_label_provenance',
                     'prohibited_use': 'six_tasks_proven_minimal;weight_optimality;new_experimental_label'})
    for r in measurements:
        core.append({'record_id': r['measurement_id'], 'record_type': 'source_measurement', 'module_id': r['module_id'],
                     'source_keys': r['source_key'], 'description': r['value'] + ' ' + r['unit'] + ' at ' + r['measurement_wavelength_nm'] + ' nm; ' + r['peak_definition'],
                     'allowed_use': policy['core_measurement_use'], 'readiness': r['measurement_status'],
                     'prohibited_use': 'global_sigma_max;independent_final_test;production_training;polymerization_efficiency'})
    measured_structures = {r['structure_record_id'] for r in measurements}
    for r in structures:
        if r['structure_record_id'] not in measured_structures:
            core.append({'record_id': r['structure_record_id'], 'record_type': 'source_identity_case', 'module_id': r['module_id'],
                         'source_keys': r['source_key'], 'description': r['molecular_formula'] + '; ' + r['conflict_resolution'],
                         'allowed_use': policy['core_identity_use'], 'readiness': r['identity_status'],
                         'prohibited_use': 'optical_label;certified_global_maximum;independent_human_validation'})
    table('paper_core', core, constraints='PRIMARY KEY(record_type,record_id),FOREIGN KEY(module_id) REFERENCES research_modules(module_id)')
    coverage = []
    for module in db.execute('SELECT module_id FROM research_modules ORDER BY module_id'):
        for prop in sorted({r['canonical_property'] for r in index if r['module_id'] == module['module_id']}):
            group = [r for r in index if r['module_id'] == module['module_id'] and r['canonical_property'] == prop]
            assessed = [r for r in assessments if r['module_id'] == module['module_id'] and r['canonical_property'] == prop]
            coverage.append({'module_id': module['module_id'], 'canonical_property': prop,
                             'field_candidates': len(group), 'source_count': len({r['source_key'] for r in group}),
                             'scalar_candidates': sum(bool(r['observation_id']) for r in group),
                             'source_verified_locator_records': sum(r['source_location_check'] == 'verified_locator_only' for r in assessed),
                             'accepted_identity_link_records': sum(bool(r['accepted_compound_ids']) for r in group),
                             'numeric_hold_records': sum(r['numeric_use_status'].startswith('withhold_') for r in group),
                             'component_hold_records': sum(r['component_use_action'] != 'no_component_override' for r in group),
                             'internal_excluded_records': sum(r['external_evidence_use'].startswith('exclude_') for r in group),
                             'quantitative_comparison_ready': 0, 'training_ready': 0})
    table('quality_coverage', coverage, constraints='PRIMARY KEY(module_id,canonical_property),FOREIGN KEY(module_id) REFERENCES research_modules(module_id)')
    db.executescript('''
    CREATE VIEW core_mechanism_evidence AS SELECT c.*, r.scope_limit, r.coinitiator_context
      FROM paper_core c JOIN knowledge_rules r ON c.record_type='knowledge_rule' AND c.record_id=r.rule_id
      WHERE c.module_id='mechanism';
    CREATE VIEW source_optical_cases AS SELECT m.*,s.canonical_smiles,s.molecular_formula,s.source_compound_number
      FROM source_measurements m JOIN source_structures s USING(structure_record_id);
    ''')
    return {
        'source_audit_structures': len(structures), 'source_audit_measurements': len(measurements),
        'source_audit_condition_fields': len(audit['measurement_conditions']),
        'verified_bibliographic_lineage_links': len(lineage),
        'verified_measurement_lineage_links': sum(r['individual_measurement_chain_verified'] == 'true' for r in lineage),
        'paper_core_entries': len(core), 'paper_core_types': dict(Counter(r['record_type'] for r in core)),
        'field_use_assessments': len(assessments), 'rule_use_assessments': len(rule_assessments),
        'field_quantitative_comparison_ready': 0, 'source_case_cross_source_comparison_ready': 0,
        'semantic_accuracy_evaluation': policy['accuracy_evaluation_status'],
        'core_definition': 'Use-specific priors, endpoint definitions and source-audit cases; not a set of independently certified experiments.',
    }
