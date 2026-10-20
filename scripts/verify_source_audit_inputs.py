"""Optional local-original check for the path-free source-audit projection.

Only source audit facts, source files and their manifests are read. Model
datasets, predictions, split assignments and sealed test labels are not opened.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(cvejn, lineage, projection):
    public = json.loads(projection.read_text())
    cm = json.loads((cvejn / 'manifest.json').read_text())
    lm = json.loads((lineage / 'manifest.json').read_text())
    checked_assets = 0
    for manifest, key in ((cm, 'assets'), (lm, 'source_assets')):
        for name, expected in manifest[key].items():
            assert sha(Path(name)) == expected, Path(name).name
            checked_assets += 1
    original = [json.loads(line) for line in (cvejn / 'source_observations.jsonl').read_text().splitlines() if line.strip()]
    assets = {Path(name).name: Path(name) for name in cm['assets']}
    retrieval = json.loads(assets['retrieval.json'].read_text())
    assert sha(Path(retrieval['main_pdf'])) == cm['main_pdf_sha256']
    table = assets['main_page_4.txt'].read_text(encoding='utf-8')
    methods = assets['main_page_6.txt'].read_text(encoding='utf-8')
    formulas = ''.join(assets['main_page_8.txt'].read_text(encoding='utf-8').split())
    assert '750 to 850 nm' in ' '.join(methods.split())
    assert 'Rhodamine B in methanol' in ' '.join(methods.split())
    assert 'THF' in methods and '10' in methods and '/C04 M' in ' '.join(methods.split())
    public_m = {r['measurement_id']: r for r in public['measurements']}
    public_s = {r['structure_record_id']: r for r in public['structures']}
    for r in original:
        line = next(line for line in table.splitlines() if line.startswith(str(r['source_compound_id']) + ' '))
        gm, wave = line.split()[-2:]
        p = public_m[r['source_observation_id']]
        assert p['value'] == gm == str(r['reported_cross_section_gm'])
        assert p['measurement_wavelength_nm'] == wave.strip('()') == str(r['reported_wavelength_nm'])
        s = public_s[p['structure_record_id']]
        assert s['canonical_smiles'] == r['canonical_smiles']
        assert s['molecular_formula'] == r['source_formula'] and r['source_formula'] in formulas
        assert p['doi'] == s['doi'] == r['source_doi']
    for audit_id, directory, filename, manifest in (
        ('cvejn_source_audit', cvejn, 'source_observations.jsonl', cm),
        ('rumi_structure_audit', lineage, 'rumi_source_structures.jsonl', lm),
        ('review_primary_lineage_audit', lineage, 'bibliographic_links.jsonl', lm),
    ):
        a = next(r for r in public['audit_sources'] if r['audit_id'] == audit_id)
        assert a['input_sha256'] == sha(directory / filename)
        assert a['original_manifest_sha256'] == sha(directory / 'manifest.json')
        expected = next(h for p, h in manifest['outputs'].items() if p.replace('\\', '/').split('/')[-1] == filename)
        assert a['input_sha256'] == expected
    original_structures = [json.loads(line) for line in (lineage / 'rumi_source_structures.jsonl').read_text().splitlines() if line.strip()]
    for r in original_structures:
        p = public_s['STRUCT-RUMI2000-' + str(r['source_compound_id'])]
        for target, source in (('doi', 'source_doi'), ('canonical_smiles', 'canonical_smiles'),
                               ('molecular_formula', 'source_formula'), ('source_internal_conflict', 'source_internal_conflict'),
                               ('conflict_resolution', 'conflict_resolution')):
            assert p[target] == r[source]
        assert not r['optical_label_certified'] and not r['training_eligible']
    result = {'status': 'passed', 'original_source_asset_hashes': checked_assets,
              'main_pdf_hash_checked': True, 'table_values_reparsed': len(original),
              'source_structure_facts_preserved': len(original_structures),
              'original_audit_inputs_checked': 3, 'test_labels_read': False,
              'scope': 'source_facts_and_provenance_consistency_not_new_human_or_global_accuracy_certification'}
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--cvejn-audit', type=Path, required=True)
    p.add_argument('--lineage-audit', type=Path, required=True)
    p.add_argument('--projection', type=Path, default=Path(__file__).resolve().parents[1] / 'inputs/source_audit_records.json')
    a = p.parse_args()
    print(json.dumps(verify(a.cvejn_audit, a.lineage_audit, a.projection), indent=2))
