"""Read-only current evidence view: preserved base + auditable traceability overlay."""
import csv
import hashlib
import json
import sqlite3
from pathlib import Path


def connect(root):
    base = root / 'data/literature/literature.sqlite'
    overlay = root / 'data/literature/traceability'
    summary = json.loads((overlay / 'summary.json').read_text())
    if hashlib.sha256(base.read_bytes()).hexdigest() != summary['base_database_sha256']:
        raise ValueError('Overlay applies to a different base snapshot.')
    for name, expected in json.loads((overlay / 'manifest.json').read_text()).items():
        if hashlib.sha256((overlay / name).read_bytes()).hexdigest() != expected:
            raise ValueError('Overlay checksum mismatch: ' + name)
    db = sqlite3.connect(':memory:', uri=True)
    db.execute('ATTACH DATABASE ? AS base', ('file:' + base.resolve().as_posix() + '?mode=ro',))
    db.execute('ATTACH DATABASE ? AS trace', ('file:' + (overlay / 'traceability.sqlite').resolve().as_posix() + '?mode=ro',))
    decisions = json.loads((root / 'configs/literature_field_use_decisions.json').read_text())
    if decisions['base_database_sha256'] != summary['base_database_sha256']:
        raise ValueError('Field-use decisions apply to a different base.')
    db.execute('CREATE TEMP TABLE overrides(evidence_id TEXT PRIMARY KEY, field_name TEXT, action TEXT, review_basis TEXT)')
    for r in decisions['records']:
        if not db.execute('SELECT 1 FROM base.evidence WHERE evidence_id=?', (r['evidence_id'],)).fetchone():
            raise ValueError('Unknown override record')
        location = db.execute('SELECT source_sha256,effective_locator_status FROM trace.locators WHERE evidence_id=?', (r['evidence_id'],)).fetchone()
        if location != (r['source_sha256'], 'source_verified_location_only'):
            raise ValueError('Field decision lacks its source-verified location')
        db.execute('INSERT INTO overrides VALUES(?,?,?,?)', (r['evidence_id'], r['affected_component'], r['action'], r['review_basis']))
    db.executescript('''
    CREATE TEMP VIEW current_evidence AS
    SELECT e.*, s.doi, s.scope AS source_scope,
      CASE WHEN l.effective_locator_status='source_verified_location_only' THEN l.locator_type ELSE '' END AS recovered_locator_type,
      CASE WHEN l.effective_locator_status='source_verified_location_only' THEN l.locator_start ELSE '' END AS recovered_locator_start,
      CASE WHEN l.effective_locator_status='source_verified_location_only' THEN l.locator_end ELSE '' END AS recovered_locator_end,
      CASE WHEN l.effective_locator_status='source_verified_location_only' THEN 'source_verified_location_only'
           WHEN e.page_hint!='' THEN 'original_page_hint_not_newly_verified' ELSE 'unresolved_location' END AS effective_location_status,
      CASE WHEN s.scope='internal_workflow_candidate' THEN 'exclude_flagged_internal_document'
           ELSE 'not_independence_certified' END AS external_evidence_use,
      COALESCE(o.action,'no_component_override') AS component_use_action,
      COALESCE(o.field_name,'') AS affected_component,
      COALESCE(o.review_basis,'') AS component_review_basis,
      COALESCE(l.scalar_anchor_check,'not_assessed_in_this_batch') AS scalar_anchor_check,
      COALESCE(l.original_page_relation,'not_assessed_in_this_batch') AS original_page_relation,
      CASE WHEN l.scalar_anchor_check='literal_scalar_not_found_requires_value_anchor_review'
           THEN 'withhold_numeric_use_pending_value_anchor_review'
           ELSE 'inherit_original_status_no_new_measurement_certification' END AS numeric_use_status
    FROM base.evidence e JOIN base.sources s USING(source_key)
    LEFT JOIN trace.locators l USING(evidence_id) LEFT JOIN overrides o USING(evidence_id);
    ''')
    db.execute('PRAGMA query_only=ON')
    return db


if __name__ == '__main__':
    db = connect(Path(__file__).resolve().parents[1])
    print(json.dumps({
        'current_records': db.execute('SELECT COUNT(*) FROM current_evidence').fetchone()[0],
        'location_status': dict(db.execute('SELECT effective_location_status,COUNT(*) FROM current_evidence GROUP BY 1')),
        'component_use_actions': dict(db.execute('SELECT component_use_action,COUNT(*) FROM current_evidence GROUP BY 1')),
        'external_evidence_use': dict(db.execute('SELECT external_evidence_use,COUNT(*) FROM current_evidence GROUP BY 1')),
        'numeric_use_status': dict(db.execute('SELECT numeric_use_status,COUNT(*) FROM current_evidence GROUP BY 1')),
    }, indent=2))
