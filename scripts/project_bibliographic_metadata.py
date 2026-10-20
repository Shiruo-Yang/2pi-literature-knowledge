"""Export existing bibliography fields without source-text or local-path columns."""
import argparse
import csv
import hashlib
import json
from pathlib import Path


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--input', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        raise ValueError('Projection already exists.')
    fields = ['paper_id', 'doi', 'title', 'year', 'journal']
    with a.input.open(encoding='utf-8-sig', newline='') as handle:
        rows = [{k: r.get(k, '') for k in fields} for r in csv.DictReader(handle)]
    a.output.parent.mkdir(exist_ok=True)
    with a.output.open('w', encoding='utf-8-sig', newline='') as handle:
        w = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    manifest = {'original_asset_sha256': hashlib.sha256(a.input.read_bytes()).hexdigest(),
                'projected_asset_sha256': hashlib.sha256(a.output.read_bytes()).hexdigest(),
                'records': len(rows), 'fields': fields,
                'row_order': 'preserved_original_data_row_order'}
    a.output.with_suffix('.provenance.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8', newline='\n')
    print('Projected', len(rows), 'bibliographic records.')
