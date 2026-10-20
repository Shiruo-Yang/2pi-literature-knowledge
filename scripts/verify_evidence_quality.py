"""Independent SQLite/CSV/source-projection checks; does not import the builder."""
import argparse
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path


def verify(root, directory):
    for name, sha in json.loads((directory / 'manifest.json').read_text()).items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == sha, name
    audit = json.loads((root / 'inputs/source_audit_records.json').read_text())
    policy = json.loads((root / 'configs/evidence_use_policy.json').read_text())
    db = sqlite3.connect('file:' + (directory / 'research.sqlite').resolve().as_posix() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    assert not db.execute('PRAGMA foreign_key_check').fetchall()
    index = {r['evidence_id']: dict(r) for r in db.execute('SELECT * FROM evidence_index')}
    readiness = {r['evidence_id']: dict(r) for r in db.execute('SELECT * FROM evidence_readiness')}
    assert index.keys() == readiness.keys()
    for eid, r in readiness.items():
        e = index[eid]
        assert (r['source_key'], r['module_id'], r['canonical_property'], r['observation_id']) == tuple(e[k] for k in ('source_key', 'module_id', 'canonical_property', 'observation_id'))
        assert r['training_ready'] == r['quantitative_comparison_ready'] == 'false'
        reasons = set(json.loads(r['missing_requirements']))
        expected_use = 'source_review_candidate'
        if e['numeric_use_status'].startswith('withhold_') or e['component_use_action'] != 'no_component_override':
            expected_use = 'retrieval_only_with_component_or_numeric_hold'
        if e['external_evidence_use'].startswith('exclude_'):
            expected_use = 'provenance_only_internal_excluded'
        assert r['max_permitted_use'] == expected_use
        assert ('scalar_anchor_gap_pending_review' in reasons) == e['numeric_use_status'].startswith('withhold_')
        assert ('source_review_component_hold' in reasons) == (e['component_use_action'] != 'no_component_override')
        assert ('internal_document_not_external_evidence' in reasons) == e['external_evidence_use'].startswith('exclude_')
        assert ('wavelength_role_unresolved' in reasons) == (e['canonical_property'] == policy['unresolved_wavelength_property'])
        assert ('source_verified_location_missing' in reasons) == (e['location_status'] != 'source_verified_location_only')
        if e['observation_id']:
            assert set(policy['candidate_quantitative_requirements']) <= reasons
            unit = db.execute('SELECT unit FROM observations WHERE observation_id=?', (e['observation_id'],)).fetchone()[0]
            assert ('explicit_unit_missing' in reasons) == (not unit)
        else:
            assert 'source_statement_interpretation_not_adjudicated' in reasons
    for name, key in (('source_audits', 'audit_sources'), ('source_structures', 'structures'),
                      ('source_measurements', 'measurements'), ('measurement_conditions', 'measurement_conditions'),
                      ('source_lineage', 'source_lineage')):
        actual = [dict(r) for r in db.execute('SELECT * FROM ' + name)]
        assert len(actual) == len(audit[key])
        for r, a in zip(actual, audit[key]):
            assert all(r[k] == str(v) for k, v in a.items()), (name, r)
    measurements = [dict(r) for r in db.execute('SELECT * FROM source_measurements')]
    for r in measurements:
        assert all(r[k] == 'false' for k in ('training_eligible', 'final_test_eligible', 'global_sigma_max_eligible', 'independent_new_sample_claim', 'existing_training_record_replacement', 'original_database_curve_history_certified', 'cross_source_comparison_ready'))
        assert r['source_fact_use'] == 'citation_and_within_source_descriptive_comparison_with_conditions_and_limits'
        struct = db.execute('SELECT * FROM source_structures WHERE structure_record_id=?', (r['structure_record_id'],)).fetchone()
        assert r['doi'] == struct['doi']
        assert r['source_key'] == struct['source_key']
        assert r['peak_definition'] == 'reported_maximum_within_750_850_nm_measurement_window'
        assert r['value_qualifier'] == 'reported_window_maximum'
        assert r['sample_solvent'] == 'THF'
        conditions = {c['condition_name']: dict(c) for c in db.execute('SELECT * FROM measurement_conditions WHERE measurement_id=?', (r['measurement_id'],))}
        assert conditions['reference_solvent']['value'] == 'methanol'
        assert conditions['sample_concentration']['value'] == conditions['reference_concentration']['value'] == '0.0001'
        assert conditions['measurement_window_lower']['value'] == '750' and conditions['measurement_window_upper']['value'] == '850'
        for k in ('pulse_duration', 'repetition_rate'):
            assert not conditions[k]['value'] and conditions[k]['condition_status'] == 'not_recovered_from_main_article'
    for r in db.execute('SELECT * FROM source_lineage'):
        assert r['bibliographic_link_verified'] == 'true'
        assert r['individual_measurement_chain_verified'] == r['independence_certified'] == 'false'
        assert db.execute('SELECT doi FROM papers WHERE source_key=?', (r['review_source_key'],)).fetchone()[0] == r['review_doi']
        assert db.execute('SELECT doi FROM papers WHERE source_key=?', (r['primary_source_key'],)).fetchone()[0] == r['primary_doi']
    rules = {r['rule_id']: dict(r) for r in db.execute('SELECT * FROM knowledge_rules')}
    assessments = [dict(r) for r in db.execute('SELECT * FROM rule_readiness')]
    assert set(rules) == {r['rule_id'] for r in assessments}
    for r in assessments:
        assert int(r['supporting_source_count']) == db.execute('SELECT count(*) FROM rule_sources WHERE rule_id=?', (r['rule_id'],)).fetchone()[0]
        assert r['scope_limit_present'] == str(bool(rules[r['rule_id']]['scope_limit'])).lower()
        assert r['primary_experimental_support'] == 'not_systematically_adjudicated'
        assert r['counterevidence_status'] == 'not_systematically_assessed'
        assert r['candidate_specific_mechanism_proof'] == r['weight_optimality_evidence'] == 'false'
    types = Counter(r[0] for r in db.execute('SELECT record_type FROM paper_core'))
    assert types == {'knowledge_rule': len(rules), 'endpoint_definition': 6, 'source_measurement': len(measurements), 'source_identity_case': 3}
    for r in db.execute('SELECT * FROM quality_coverage'):
        args = (r['module_id'], r['canonical_property'])
        def count(condition='1'):
            return db.execute('SELECT count(*) FROM evidence_index WHERE module_id=? AND canonical_property=? AND ' + condition, args).fetchone()[0]
        assert int(r['field_candidates']) == count()
        assert int(r['scalar_candidates']) == count("observation_id!=''")
        assert int(r['source_verified_locator_records']) == count("location_status='source_verified_location_only'")
        assert int(r['accepted_identity_link_records']) == count("accepted_compound_ids!=''")
        assert int(r['numeric_hold_records']) == count("numeric_use_status LIKE 'withhold_%'")
        assert int(r['component_hold_records']) == count("component_use_action!='no_component_override'")
        assert int(r['internal_excluded_records']) == count("external_evidence_use LIKE 'exclude_%'")
        assert int(r['source_count']) == db.execute('SELECT count(DISTINCT source_key) FROM evidence_index WHERE module_id=? AND canonical_property=?', args).fetchone()[0]
    summary = json.loads((directory / 'summary.json').read_text())
    assert summary['evidence_quality']['semantic_accuracy_evaluation'] == 'not_measured_against_independent_reference_annotations'
    assert summary['new_certified_measurements'] == summary['new_training_labels'] == 0
    assert summary['evidence_quality']['paper_core_entries'] == sum(types.values())
    result = {'status': 'passed', 'field_assessments_checked': len(readiness), 'rule_assessments_checked': len(assessments),
              'source_measurements_checked': len(measurements), 'core_types_checked': dict(types),
              'semantic_accuracy_measured': False, 'training_labels_created': 0}
    db.close()
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--directory', type=Path, default=Path(__file__).resolve().parents[1] / 'data/research')
    a = p.parse_args()
    print(json.dumps(verify(a.root, a.directory), indent=2))
