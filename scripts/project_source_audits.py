"""Project existing local source audits into path-free, reproducible public facts.

This imports no model targets or dataset split files. Original audit inputs are
checked against their saved manifests; their scientific status is not upgraded.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_jsonl(directory, name, manifest):
    path = directory / name
    matches = [h for p, h in manifest['outputs'].items() if p.replace('\\', '/').split('/')[-1] == name]
    if matches != [sha(path)]:
        raise ValueError('Audit output checksum mismatch: ' + name)
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def project(cvejn, lineage, output):
    if output.exists():
        raise ValueError('Projection output must be a fresh file.')
    cm = json.loads((cvejn / 'manifest.json').read_text())
    lm = json.loads((lineage / 'manifest.json').read_text())
    measurements = checked_jsonl(cvejn, 'source_observations.jsonl', cm)
    structures = checked_jsonl(lineage, 'rumi_source_structures.jsonl', lm)
    links = checked_jsonl(lineage, 'bibliographic_links.jsonl', lm)
    if len(measurements) != 2 or len(structures) != 3 or len(links) != 3:
        raise ValueError('Unexpected source audit cohort.')
    audit_sources = [
        {'audit_id': 'cvejn_source_audit', 'input_sha256': sha(cvejn / 'source_observations.jsonl'),
         'original_manifest_sha256': sha(cvejn / 'manifest.json'), 'source_document_sha256': cm['main_pdf_sha256'],
         'review_basis': 'existing_assistant_source_review_with_computational_checks',
         'human_review_status': 'not_performed'},
        {'audit_id': 'rumi_structure_audit', 'input_sha256': sha(lineage / 'rumi_source_structures.jsonl'),
         'original_manifest_sha256': sha(lineage / 'manifest.json'),
         'source_document_sha256': next(h for p, h in lm['source_assets'].items() if p.replace('\\', '/').endswith('/rumi_support.pdf')),
         'review_basis': 'existing_assistant_source_review_with_internal_drawing_conflict_recorded',
         'human_review_status': 'not_performed'},
        {'audit_id': 'review_primary_lineage_audit', 'input_sha256': sha(lineage / 'bibliographic_links.jsonl'),
         'original_manifest_sha256': sha(lineage / 'manifest.json'), 'source_document_sha256': '',
         'review_basis': 'existing_accessible_review_text_and_reference_list_check',
         'human_review_status': 'not_performed'},
    ]
    public_structures, public_measurements, conditions = [], [], []
    for r in measurements:
        sid = 'STRUCT-CVEJN2015-' + str(r['source_compound_id'])
        if r['training_eligible'] or r['final_test_eligible'] or r['global_sigma_max_certified']:
            raise ValueError('Unexpected use-status upgrade in source input.')
        public_structures.append({
            'structure_record_id': sid, 'doi': r['source_doi'], 'source_compound_number': str(r['source_compound_id']),
            'canonical_smiles': r['canonical_smiles'], 'molecular_formula': r['source_formula'],
            'structure_locator': r['structure_locator'], 'structure_basis': r['structure_basis'],
            'source_internal_conflict': '', 'conflict_resolution': '', 'audit_id': 'cvejn_source_audit',
            'human_review_status': r['human_review_status'], 'identity_status': 'assistant_source_linked_not_author_certified',
        })
        public_measurements.append({
            'measurement_id': r['source_observation_id'], 'structure_record_id': sid, 'doi': r['source_doi'],
            'canonical_property': 'two_photon_cross_section', 'value': str(r['reported_cross_section_gm']), 'unit': 'GM',
            'measurement_wavelength_nm': str(r['reported_wavelength_nm']), 'sample_solvent': r['sample_solvent'],
            'measurement_method': r['measurement_method'], 'value_qualifier': 'reported_window_maximum',
            'peak_definition': r['endpoint'], 'numeric_locator': r['numeric_locator'],
            'condition_locator': r['condition_locator'], 'numeric_evidence_class': r['numeric_evidence_class'],
            'audit_id': 'cvejn_source_audit', 'human_review_status': r['human_review_status'],
            'global_sigma_max_eligible': 'false', 'training_eligible': 'false', 'final_test_eligible': 'false',
            'independent_new_sample_claim': 'false', 'existing_training_record_replacement': 'false',
            'original_database_curve_history_certified': 'false',
            'development_connectivity_overlap': 'existing_development_match' if r['matching_development_connectivity_rows'] else 'no_match_in_previously_checked_development_pool_not_proof_of_independence',
            'measurement_status': 'assistant_source_checked_with_missing_laser_specifications',
            'use_scope': 'source_reported_optical_context_not_global_peak_or_polymerization_efficiency',
        })
        for name, value, unit, role in (
            ('sample_concentration', r['sample_concentration_mol_l'], 'mol/L', 'sample'),
            ('reference_dye', r['reference_dye'], '', 'reference'),
            ('reference_solvent', r['reference_solvent'], '', 'reference'),
            ('reference_concentration', r['reference_concentration_mol_l'], 'mol/L', 'reference'),
            ('measurement_window_lower', 750, 'nm', 'measurement_range'),
            ('measurement_window_upper', 850, 'nm', 'measurement_range'),
            ('pulse_duration', r['pulse_width_fs'], 'fs', 'laser'),
            ('repetition_rate', r['repetition_rate_hz'], 'Hz', 'laser'),
        ):
            conditions.append({'measurement_id': r['source_observation_id'], 'condition_name': name,
                               'value': '' if value is None else str(value), 'unit': unit, 'role': role,
                               'condition_status': 'not_recovered_from_main_article' if value is None else 'reported_source_condition',
                               'source_locator': r['condition_locator'], 'audit_id': 'cvejn_source_audit'})
    for r in structures:
        if r['training_eligible'] or r['optical_label_certified']:
            raise ValueError('Structure-only audit cannot carry an optical label.')
        public_structures.append({
            'structure_record_id': 'STRUCT-RUMI2000-' + str(r['source_compound_id']), 'doi': r['source_doi'],
            'source_compound_number': str(r['source_compound_id']), 'canonical_smiles': r['canonical_smiles'],
            'molecular_formula': r['source_formula'],
            'structure_locator': 'Supporting information PDF page ' + str(r['pdf_page']) + ' printed ' + r['printed_page'] + '; ' + r['evidence_locator'],
            'structure_basis': r['structure_basis'], 'source_internal_conflict': r['source_internal_conflict'],
            'conflict_resolution': r['conflict_resolution'], 'audit_id': 'rumi_structure_audit',
            'human_review_status': r['human_review_status'], 'identity_status': 'assistant_source_linked_with_recorded_source_conflict',
        })
    public_links = []
    for r in links:
        if not r['bibliographic_link_verified'] or r['individual_record_structure_value_chain_verified']:
            raise ValueError('Unexpected source-chain status.')
        public_links.append({
            'review_doi': r['review_doi'], 'primary_doi': r['primary_doi'], 'reference_number': str(r['reference_number']),
            'locator': r['locator'], 'evidence_url': r['evidence_url'], 'access_basis': r['access'],
            'bibliographic_link_verified': 'true', 'individual_measurement_chain_verified': 'false',
            'independence_certified': 'false', 'audit_id': 'review_primary_lineage_audit',
        })
    result = {'schema': 'source_audit_public_projection', 'audit_sources': audit_sources,
              'structures': public_structures, 'measurements': public_measurements,
              'measurement_conditions': conditions, 'source_lineage': public_links,
              'projector_sha256': sha(Path(__file__)),
              'limits': 'Previously audited facts only; no new human certification, training labels or final-test membership.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({k: len(result[k]) for k in ('structures', 'measurements', 'measurement_conditions', 'source_lineage')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--cvejn-audit', required=True, type=Path)
    p.add_argument('--lineage-audit', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    project(args.cvejn_audit, args.lineage_audit, args.output)
