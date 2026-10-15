import unittest
from normalize_literature_database import doi, scalar, internal_title, digest, serial


class NormalizationTests(unittest.TestCase):
    def test_doi_case_and_url(self):
        self.assertEqual(doi(" HTTPS://doi.org/10.1021/AB123 "), "10.1021/ab123")

    def test_doi_invalid_not_guessed(self):
        self.assertEqual(doi("10.1234/a 10.1234/b"), "")
        self.assertEqual(doi("unknown"), "")

    def test_scalar_candidates_only(self):
        for s in ("0", "-1.2", "1e-3", ".5"):
            self.assertEqual(scalar(s), s)
        for s in ("<50", "10–20", "sigma=250", "not reported", "NaN", ""):
            self.assertEqual(scalar(s), "")

    def test_internal_title_flag_is_conservative(self):
        self.assertTrue(internal_title("An Evidence-Guided, Mechanism-Aware Workflow for Functional Molecular Materials Discovery"))
        self.assertFalse(internal_title("Two-photon absorption in organic materials"))

    def test_hash_order_independent(self):
        self.assertEqual(digest(serial({"a": "1", "b": "2"})), digest(serial({"b": "2", "a": "1"})))
        self.assertNotEqual(digest(serial({"a": "1"})), digest(serial({"a": "1 "})))


if __name__ == "__main__":
    unittest.main()
