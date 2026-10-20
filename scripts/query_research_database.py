"""Inspect the current research database by manuscript module (read-only)."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def open_database(root):
    directory = root / 'data/research'
    for name, sha in json.loads((directory / 'manifest.json').read_text()).items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != sha:
            raise ValueError('Research snapshot checksum mismatch: ' + name)
    db = sqlite3.connect('file:' + (directory / 'research.sqlite').resolve().as_posix() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--module', choices=['molecular_design', 'property_profile', 'mechanism', 'formulation_processing', 'synthesis'])
    p.add_argument('--kind', choices=['overview', 'rules', 'evidence', 'quantities', 'profile'], default='overview')
    p.add_argument('--limit', type=int, default=5)
    a = p.parse_args()
    if a.limit < 1 or a.limit > 1000:
        p.error('limit must be between 1 and 1000')
    db = open_database(Path(__file__).resolve().parents[1])
    table = {'overview': 'research_modules', 'rules': 'knowledge_rules', 'evidence': 'evidence_index', 'quantities': 'observations', 'profile': 'six_task_profile'}[a.kind]
    where, params = (' WHERE module_id=?', [a.module]) if a.module and a.kind != 'profile' else ('', [])
    data = [dict(r) for r in db.execute('SELECT * FROM ' + table + where + ' LIMIT ?', params + [a.limit])]
    print(json.dumps(data, ensure_ascii=True, indent=2))
