import sqlite3
import unittest
from pathlib import Path
from open_literature_database import connect


class CurrentViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = connect(Path(__file__).resolve().parents[1])

    def test_no_record_loss(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM current_evidence').fetchone()[0], 9257)

    def test_raw_values_unchanged(self):
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM current_evidence c JOIN base.evidence e USING(evidence_id) WHERE c.raw_value!=e.raw_value OR c.page_hint!=e.page_hint').fetchone()[0], 0)

    def test_source_verified_locator_count(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM current_evidence WHERE effective_location_status='source_verified_location_only'").fetchone()[0], 1092)

    def test_component_overrides_only(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM current_evidence WHERE component_use_action='withhold_250_nm_wavelength_component' AND affected_component='wavelength_nm'").fetchone()[0], 4)

    def test_missing_literal_scalar_held_not_corrected(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM current_evidence WHERE numeric_use_status='withhold_numeric_use_pending_value_anchor_review'").fetchone()[0], 33)

    def test_no_write_access(self):
        with self.assertRaises(sqlite3.OperationalError):
            self.db.execute("UPDATE base.evidence SET raw_value=raw_value WHERE 0")

    def test_internal_documents_not_reintroduced(self):
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM current_evidence WHERE external_evidence_use='exclude_flagged_internal_document'").fetchone()[0], 32)


if __name__ == '__main__':
    unittest.main()
