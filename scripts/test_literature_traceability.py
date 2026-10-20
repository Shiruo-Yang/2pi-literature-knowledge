import unittest
from improve_literature_traceability import locate, normalize, pdf_cache_blocks, semantic, scalar_anchor_check


class TraceabilityTests(unittest.TestCase):
    def test_exact_unique(self):
        text = 'A long source passage explicitly identifying the experimental material and the conditions used.'
        r = locate(text, [('3', text)])
        self.assertEqual((r['match_count'], r['locator_start'], r['locator_end']), (1, '3', '3'))

    def test_ambiguous_never_first_match(self):
        text = 'A sufficiently long experimental description is repeated on more than one page of this paper.'
        r = locate(text, [('1', text), ('2', text)])
        self.assertEqual(r['match_count'], 2)
        self.assertEqual(r['locator_start'], '')

    def test_short_anchor_not_accepted(self):
        self.assertEqual(locate('250 nm', [('1', '250 nm')])['match_count'], 0)

    def test_spanning_pages(self):
        a = 'A sufficiently long paragraph begins here describing an experimental '
        b = 'procedure and then continues on the next source page.'
        r = locate(a + '--- Page 2 ---' + b, [('1', a), ('2', b)])
        self.assertEqual((r['locator_start'], r['locator_end']), ('1', '2'))

    def test_parser_marker_not_printed_page(self):
        r = pdf_cache_blocks('--- Page 9 ---\nPrinted journal page 6527\n--- Page 10 ---\nNext page')
        self.assertEqual([x[0] for x in r], ['9', '10'])

    def test_same_scalar_required(self):
        r = {'field_name': 'experimental_context', 'raw_value': 'wavelength_nm=250;other=x', 'evidence_anchor': 'Line widths of about 250 nm were obtained.'}
        self.assertEqual(semantic(r)[1], 'same_scalar_in_explicit_geometry_phrase')
        r['raw_value'] = 'wavelength_nm=800;other=x'
        self.assertEqual(semantic(r)[1], 'broad_context_flag_only')

    def test_geometry_field_not_changed(self):
        r = {'field_name': 'line_width', 'raw_value': '250', 'evidence_anchor': 'Line widths of about 250 nm were obtained.'}
        self.assertEqual(semantic(r), ('', 'broad_context_flag_only'))

    def test_unicode_whitespace_only_normalization(self):
        self.assertEqual(normalize('Ａ B\nC'), 'abc')
        self.assertNotEqual(normalize('250 nm'), normalize('250 um'))

    def test_literal_value_not_in_anchor(self):
        r = {'raw_value': '65 nm', 'raw_unit': 'nm', 'evidence_anchor': 'Resolution is 650 nm, not a wavelength.'}
        self.assertEqual(scalar_anchor_check(r), 'literal_scalar_not_found_requires_value_anchor_review')
        r['evidence_anchor'] = 'A value of 65 nm is mentioned.'
        self.assertEqual(scalar_anchor_check(r), 'literal_scalar_present_not_endpoint_certified')


if __name__ == '__main__':
    unittest.main()
