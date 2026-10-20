import unittest
import sqlite3
from copy import deepcopy
from literature_source_organization import apply_bibliography, append_source_tables


class SourceOrganizationTests(unittest.TestCase):
    def setUp(self):
        self.paper = {'source_key': 'source', 'doi': '10.1000/example', 'title': '', 'year': '', 'journal': ''}
        self.row = {'doi_clean': '10.1000/example', 'title_clean': 'Example', 'year': '2020',
                    'journal_clean': 'Journal', 'zotero_item_key': 'ABCDEFGH'}

    def test_exact_doi_empty_cells_can_fill(self):
        u, d = apply_bibliography([self.paper], [self.row])
        self.assertEqual(len(u), 3)
        self.assertEqual(d, [])
        self.assertEqual(self.paper['year'], '2020')

    def test_different_doi_cannot_fill(self):
        self.row['doi_clean'] = '10.1000/other'
        self.assertEqual(apply_bibliography([self.paper], [self.row]), ([], []))
        self.assertFalse(self.paper['title'])

    def test_existing_year_never_overwritten(self):
        self.paper['year'] = '2019'
        u, d = apply_bibliography([self.paper], [self.row])
        self.assertEqual(self.paper['year'], '2019')
        self.assertEqual(next(r for r in d if r['field_name'] == 'year')['difference_type'], 'content_difference_not_adjudicated')

    def test_format_variants_are_not_claimed_content_errors(self):
        self.paper['journal'] = 'JOURNAL.'
        _, d = apply_bibliography([self.paper], [self.row])
        self.assertEqual(next(r for r in d if r['field_name'] == 'journal')['difference_type'], 'formatting_variant')
        self.assertEqual(self.paper['journal'], 'JOURNAL.')

    def test_conflicting_candidates_do_not_fill(self):
        other = deepcopy(self.row)
        other['year'] = '2021'
        u, d = apply_bibliography([self.paper], [self.row, other])
        self.assertEqual(self.paper['year'], '')
        self.assertFalse(any(r['field_name'] == 'year' for r in u))

    def test_missing_fields_not_invented(self):
        self.row['year'] = ''
        apply_bibliography([self.paper], [self.row])
        self.assertEqual(self.paper['year'], '')


class DocumentOrganizationTests(unittest.TestCase):
    def organize(self, documents, pilot=None):
        db = sqlite3.connect(':memory:')
        db.row_factory = sqlite3.Row
        db.executescript('''CREATE TABLE evidence_index(source_key,module_id);
            CREATE TABLE rule_sources(source_key,rule_id);
            CREATE TABLE knowledge_rules(rule_id,module_id);
            CREATE TABLE profile_sources(source_key);
            CREATE TABLE source_structures(source_key,module_id);
            CREATE TABLE source_measurements(source_key,module_id);
            INSERT INTO evidence_index VALUES ('s1','mechanism');''')
        saved = {}
        def table(name, rows, *args, **kwargs):
            saved[name] = rows
        papers = [{'source_key': k, 'doi': '10.1000/' + k, 'title': '', 'year': '', 'journal': '', 'field_evidence_count': 0}
                  for k in ('s1', 's2')]
        result = append_source_tables(db, table, papers,
            {'documents': documents, 'summary': {'matched_source_dois': 2}}, [], [], pilot or [], [])
        db.close()
        return saved, result

    def document(self, key, source, digest):
        return {'document_id': key, 'source_key': source, 'document_sha256': digest,
                'availability': 'local_pdf_available' if digest else 'not_a_locally_resolved_pdf'}

    def test_duplicate_attachments_are_retained_but_not_independent(self):
        saved, result = self.organize([self.document('a', 's1', 'hash'), self.document('b', 's1', 'hash')])
        self.assertEqual(len(saved['source_documents']), 2)
        self.assertEqual(result['same_source_duplicate_file_groups'], 1)
        self.assertEqual(saved['source_dossiers'][0]['unique_local_file_hashes'], 1)
        self.assertTrue(all(r['reuse_status'] == 'same_source_duplicate_attachment' for r in saved['source_documents']))

    def test_cross_source_same_file_requires_review_not_automatic_merge(self):
        saved, result = self.organize([self.document('a', 's1', 'hash'), self.document('b', 's2', 'hash')])
        self.assertEqual(result['cross_source_shared_file_groups'], 1)
        self.assertEqual(saved['document_reuse_groups'][0]['source_count'], 2)
        self.assertTrue(all(r['reuse_status'] == 'cross_source_same_file_requires_binding_review' for r in saved['source_documents']))

    def test_missing_hashes_are_not_a_duplicate_group(self):
        saved, result = self.organize([self.document('a', 's1', ''), self.document('b', 's1', '')])
        self.assertEqual(saved['document_reuse_groups'], [])
        self.assertEqual(result['unique_local_pdf_hashes'], 0)
        self.assertEqual(saved['source_dossiers'][0]['research_modules'], 'mechanism')

    def test_parser_warnings_do_not_create_labels(self):
        _, result = self.organize([], [{'tool': 'docling', 'status': 'parsed', 'table_count': '1',
                                       'runtime_observations': '[{"warning_category":"unmatched_cell"}]'}])
        self.assertEqual(result['parser_attempts_with_runtime_observations'], 1)
        self.assertEqual(result['docling_candidate_tables'], 1)
        self.assertEqual(result['new_experiment_labels'], 0)


if __name__ == '__main__':
    unittest.main()
