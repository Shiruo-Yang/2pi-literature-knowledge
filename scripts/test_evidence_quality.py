import json
import unittest
from copy import deepcopy
from pathlib import Path

from research_evidence_quality import add_audit_sources, assess_field, source_key

ROOT = Path(__file__).resolve().parents[1]
POLICY = json.loads((ROOT / 'configs/evidence_use_policy.json').read_text())


class EvidenceQualityTests(unittest.TestCase):
    def setUp(self):
        self.field = {'evidence_id': 'test', 'source_key': 'source', 'module_id': 'property_profile',
                      'canonical_property': 'two_photon_cross_section', 'observation_id': 'obs',
                      'external_evidence_use': 'not_independence_certified',
                      'numeric_use_status': 'inherit_original_status_no_new_measurement_certification',
                      'component_use_action': 'no_component_override',
                      'location_status': 'source_verified_location_only', 'accepted_compound_ids': 'one_compound'}
        self.observation = {'unit': 'GM'}

    def assess(self):
        return assess_field(self.field, self.observation, POLICY)

    def test_locator_does_not_certify_measurement(self):
        self.assertEqual(self.assess()['quantitative_comparison_ready'], 'false')
        self.assertIn('source_checked_value_and_unit', json.loads(self.assess()['missing_requirements']))

    def test_single_identity_link_does_not_certify_ownership(self):
        self.assertIn('unique_scientific_ownership', json.loads(self.assess()['missing_requirements']))
        self.assertEqual(self.assess()['training_ready'], 'false')

    def test_internal_exclusion_takes_precedence(self):
        self.field['external_evidence_use'] = 'exclude_flagged_internal_document'
        self.field['numeric_use_status'] = 'withhold_numeric_use_pending_value_anchor_review'
        self.assertEqual(self.assess()['max_permitted_use'], 'provenance_only_internal_excluded')
        self.assertIn('scalar_anchor_gap_pending_review', json.loads(self.assess()['missing_requirements']))

    def test_numeric_hold_not_automatically_cleared(self):
        self.field['numeric_use_status'] = 'withhold_numeric_use_pending_value_anchor_review'
        self.assertEqual(self.assess()['max_permitted_use'], 'retrieval_only_with_component_or_numeric_hold')

    def test_component_hold_separate_from_entire_record(self):
        self.field['component_use_action'] = 'withhold_misassigned_wavelength'
        self.assertIn('source_review_component_hold', json.loads(self.assess()['missing_requirements']))
        self.assertNotIn('internal_document_not_external_evidence', json.loads(self.assess()['missing_requirements']))

    def test_unresolved_wavelength_role_is_visible(self):
        self.field['canonical_property'] = 'reported_wavelength_unspecified'
        self.assertIn('wavelength_role_unresolved', json.loads(self.assess()['missing_requirements']))

    def test_missing_unit_is_not_filled(self):
        self.observation['unit'] = ''
        self.assertEqual(self.assess()['unit_check'], 'missing')

    def test_text_statement_not_assumed_mechanism_proof(self):
        row = assess_field(self.field, None, POLICY)
        self.assertIn('source_statement_interpretation_not_adjudicated', json.loads(row['missing_requirements']))
        self.assertEqual(row['record_kind'], 'nonscalar_field_candidate')

    def test_assessment_does_not_mutate_original(self):
        before = deepcopy(self.field)
        self.assess()
        self.assertEqual(self.field, before)

    def test_doi_source_hash_matches_preserved_scheme(self):
        import hashlib
        self.assertEqual(source_key('10.1039/C5TC01293G'), 'SRC-' + hashlib.sha256(b'doi:10.1039/c5tc01293g').hexdigest()[:24])

    def test_missing_source_metadata_not_guessed(self):
        papers = [{'source_key': 'old', 'doi': '10.1000/old', 'title': '', 'year': '', 'journal': '',
                   'scope': '', 'publication_type': '', 'primary_experiment_source_status': '', 'field_evidence_count': 1}]
        audit = {'structures': [{'doi': '10.1000/new'}], 'measurements': [], 'source_lineage': []}
        add_audit_sources(papers, audit)
        new = next(r for r in papers if r['doi'] == '10.1000/new')
        self.assertEqual((new['title'], new['year'], new['journal']), ('', '', ''))
        self.assertEqual(new['field_evidence_count'], 0)

    def test_exact_existing_doi_is_not_added_twice(self):
        papers = [{'source_key': 'old', 'doi': '10.1000/old'}]
        audit = {'structures': [{'doi': '10.1000/old'}], 'measurements': [], 'source_lineage': []}
        self.assertEqual(add_audit_sources(papers, audit), [])

    def test_public_url_not_confused_with_windows_drive(self):
        import re
        pattern = r'(?i)(?<![a-z0-9])[a-z]:[\\/]'
        self.assertIsNone(re.search(pattern, 'https://example.org/source'))
        self.assertIsNotNone(re.search(pattern, '"C:/private/source"'))


if __name__ == '__main__':
    unittest.main()
