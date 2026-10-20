"""Publish parser status and fingerprints, keeping all source content private."""
import argparse
import hashlib
import json
from pathlib import Path


def project(stage, output):
    if output.exists():
        raise ValueError('Fresh public pilot output required.')
    fields = ['document_id','source_key','doi','document_sha256','target_page','tool','tool_version','status',
              'page_count','table_count','text_items','output_sha256','scientific_status']
    records, hashes = [], {}
    observation_path = stage / 'parser_runtime_observations.json'
    observations = json.loads(observation_path.read_text(encoding='utf-8')) if observation_path.exists() else []
    for tool in ('liteparse','docling'):
        path = stage / tool / 'status.json'
        statuses = json.loads(path.read_text(encoding='utf-8'))
        hashes[tool + '_status_sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
        for r in statuses:
            relevant = [o for o in observations if o['document_id'] == r['document_id'] and o['tool'] == tool]
            records.append({k: str(r[k]) for k in fields if k in r} |
                           {'failure_category': r.get('error_type', ''),
                            'runtime_observations': json.dumps(relevant, ensure_ascii=False, sort_keys=True)})
    original = stage / 'parser_manifest.private.json'
    hashes['selection_manifest_sha256'] = hashlib.sha256(original.read_bytes()).hexdigest()
    if observation_path.exists():
        hashes['runtime_observations_sha256'] = hashlib.sha256(observation_path.read_bytes()).hexdigest()
    payload = {'schema':'local_document_parser_pilot_status','records':records,'private_artifact_hashes':hashes,
               'scope':'Selected native-PDF pages; parser success/table counts are not extraction accuracy or complete experimental records.'}
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'records':len(records),'successes':sum(r['status']=='parsed' for r in records)}))


if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--stage',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    project(a.stage,a.output)
