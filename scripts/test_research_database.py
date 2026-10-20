import unittest
from decimal import Decimal
from build_research_database import normalize_quantity, observation_key, number


class ResearchNormalizationTests(unittest.TestCase):
    def test_explicit_power_conversion(self):
        self.assertEqual(normalize_quantity('reported_power_unspecified', Decimal('0.2'), 'W')[:2], ('200', 'mW'))

    def test_loading_units_do_not_cross_convert(self):
        self.assertEqual(normalize_quantity('initiator_loading', Decimal('1'), 'phr')[:2], ('1', 'phr'))
        self.assertEqual(normalize_quantity('initiator_loading', Decimal('1'), 'wt%')[:2], ('1', 'wt%'))

    def test_energy_not_implicitly_power(self):
        self.assertEqual(normalize_quantity('polymerization_threshold_energy', Decimal('2'), 'J')[:2], ('2', 'J'))

    def test_ranges_and_inequalities_remain_unparsed(self):
        for value in ('<10', '1-3', '3 +/- 1', '', 'NaN'):
            self.assertIsNone(number(value))

    def test_missing_unit_not_guessed(self):
        self.assertEqual(normalize_quantity('pulse_duration', Decimal('80'), '')[:2], ('80', ''))

    def test_measurement_context_cannot_merge(self):
        row = {'field_name': 'power_raw', 'source_key': 'source', 'evidence_id': 'one', 'anchor_sha256': 'anchor', 'component_use_action': 'none', 'numeric_use_status': 'candidate', 'external_evidence_use': 'not_certified', 'use_status': 'machine'}
        taxonomy = {'canonical_property': 'reported_power_unspecified'}
        first = observation_key(row, taxonomy, '10', 'mW', 'context_A')
        second = observation_key(row, taxonomy, '10', 'mW', 'context_B')
        self.assertNotEqual(first, second)

    def test_same_field_without_context_retains_identity(self):
        row = {'field_name': 'power_raw', 'source_key': 'source', 'evidence_id': 'one', 'anchor_sha256': 'anchor', 'component_use_action': 'none', 'numeric_use_status': 'candidate', 'external_evidence_use': 'not_certified', 'use_status': 'machine'}
        taxonomy = {'canonical_property': 'reported_power_unspecified'}
        first = observation_key(row, taxonomy, '10', 'mW', '')
        row['evidence_id'] = 'two'
        self.assertNotEqual(first, observation_key(row, taxonomy, '10', 'mW', ''))


if __name__ == '__main__':
    unittest.main()
