"""Inspect the current research database by manuscript module (read-only)."""
import argparse
import hashlib
import json
import sqlite3
from pathlib import Path


def open_database(root, directory=None):
    directory = directory or root / 'data/research'
    for name, sha in json.loads((directory / 'manifest.json').read_text()).items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != sha:
            raise ValueError('Research snapshot checksum mismatch: ' + name)
    db = sqlite3.connect('file:' + (directory / 'research.sqlite').resolve().as_posix() + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return db


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--module', choices=['molecular_design', 'property_profile', 'mechanism', 'formulation_processing', 'synthesis'])
    tables = {'overview': 'research_modules', 'rules': 'knowledge_rules', 'evidence': 'evidence_index',
              'quantities': 'observations', 'profile': 'six_task_profile', 'core': 'paper_core',
              'readiness': 'evidence_readiness', 'rule-readiness': 'rule_readiness',
              'source-measurements': 'source_optical_cases', 'structures': 'source_structures',
              'lineage': 'source_lineage', 'coverage': 'quality_coverage',
              'sources': 'source_dossiers', 'documents': 'source_documents',
              'document-bindings': 'document_binding_checks', 'document-reuse': 'document_reuse_groups',
              'metadata-updates': 'bibliography_updates', 'metadata-differences': 'bibliography_differences',
              'parser-pilot': 'document_parser_pilot'}
    p.add_argument('--kind', choices=list(tables), default='overview')
    p.add_argument('--query', help='Case-insensitive substring search in textual columns; does not change record status.')
    p.add_argument('--directory', type=Path, help='Optional checked research snapshot directory.')
    p.add_argument('--limit', type=int, default=5)
    a = p.parse_args()
    if a.limit < 1 or a.limit > 1000:
        p.error('limit must be between 1 and 1000')
    db = open_database(Path(__file__).resolve().parents[1], a.directory)
    table = tables[a.kind]
    columns = [r[1] for r in db.execute('PRAGMA table_info(' + table + ')')]
    clauses, params = [], []
    if a.module:
        if 'module_id' in columns:
            clauses.append('module_id=?')
            params.append(a.module)
        elif 'research_modules' in columns:
            clauses.append("instr(';' || research_modules || ';', ';' || ? || ';')>0")
            params.append(a.module)
        else:
            p.error('This record kind has no module column; omit --module.')
    if a.query:
        # Column names come from this checked SQLite schema, never user input.
        clauses.append('(' + ' OR '.join('instr(lower("' + col + '"),lower(?))>0' for col in columns) + ')')
        params.extend([a.query] * len(columns))
    where = ' WHERE ' + ' AND '.join(clauses) if clauses else ''
    data = [dict(r) for r in db.execute('SELECT * FROM ' + table + where + ' LIMIT ?', params + [a.limit])]
    print(json.dumps(data, ensure_ascii=True, indent=2))
    db.close()
