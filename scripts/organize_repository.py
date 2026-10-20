"""Rebase root legacy study files into study_context and maintenance docs into docs.

Moves are recoverable in Git. Existing targets or files outside the repository
are rejected; Markdown links to existing local files are rebased mechanically.
"""
import argparse
import os
import re
from pathlib import Path


def organize(root, apply=False):
    root = root.resolve()
    historical = {'AUDIT_REPORT.md', 'HISTORICAL_STUDY_CONTEXT.md', 'MANUSCRIPT_ALIGNMENT.md',
                  'SUPPLEMENTARY_REGISTRY_SUMMARY.md', 'TASK_WEIGHT_POLICY.md',
                  'local_source_audit_20260822.md', 'panel1_real_source_three_layer_20260822.md'}
    moves = {p: root / 'study_context' / p.name for p in root.glob('*.csv')}
    moves.update({p: root / ('study_context' if p.name in historical else 'docs') / p.name
                  for p in root.glob('*.md') if p.name != 'README.md'})
    for old, new in moves.items():
        if not old.resolve().is_relative_to(root) or not new.resolve().is_relative_to(root) or new.exists():
            raise ValueError('Unsafe or existing move target: ' + new.name)
    edits = []
    for p in root.rglob('*.md'):
        if '.git' in p.parts:
            continue
        current_location = moves.get(p, p)
        def replace(match):
            target = match[2]
            if re.match(r'\w+://|mailto:|#', target) or ' ' in target:
                return match[0]
            path_part, sep, fragment = target.partition('#')
            prior = (p.parent / path_part).resolve()
            if not prior.exists() or not prior.is_relative_to(root):
                return match[0]
            after = moves.get(prior, prior)
            relative = Path(os.path.relpath(after, current_location.parent)).as_posix()
            return match[1] + relative + (sep + fragment if sep else '') + match[3]
        original = p.read_text(encoding='utf-8')
        modified = re.sub(r'(\]\()([^\n()]+)(\))', replace, original)
        if original != modified:
            edits.append((current_location, modified))
    print('Planned moves:', len(moves), '; Markdown paths updated:', len(edits))
    if apply:
        for old, new in moves.items():
            new.parent.mkdir(exist_ok=True)
            old.rename(new)
        for p, content in edits:
            p.write_text(content, encoding='utf-8', newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    organize(Path(__file__).resolve().parents[1], a.apply)
