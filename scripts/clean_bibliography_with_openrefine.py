"""Run explicit, non-destructive bibliography operations on a local OpenRefine server."""
import argparse
import csv
import hashlib
import io
import json
import urllib.parse
import urllib.request
import uuid
from pathlib import Path


def clean(source, output, operations_output, base):
    if output.exists() or operations_output.exists():
        raise ValueError('Fresh output files required.')
    parsed = urllib.parse.urlparse(base)
    if parsed.hostname not in ('127.0.0.1', 'localhost'):
        raise ValueError('This cleaner is restricted to a local server.')
    def get(command):
        return json.load(urllib.request.urlopen(base + '/command/core/' + command, timeout=30))
    version = get('get-version')
    token = get('get-csrf-token')['token']
    records = json.loads(source.read_text(encoding='utf-8'))['records']
    fields = list(records[0])
    buffer = io.StringIO(newline='')
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator='\n')
    writer.writeheader()
    writer.writerows(records)
    data = buffer.getvalue().encode('utf-8')
    boundary = 'lit-' + uuid.uuid4().hex
    parts = []
    for key, value in {'project-name': 'Photoinitiator bibliography cleanup', 'format': 'text/line-based/*sv',
                       'options': json.dumps({'separator': ',', 'ignoreLines': -1, 'headerLines': 1,
                                              'skipDataLines': 0, 'storeBlankRows': False, 'storeBlankCellsAsNulls': False})}.items():
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
    parts.extend([(f'--{boundary}\r\nContent-Disposition: form-data; name="project-file"; filename="bibliography.csv"\r\nContent-Type: text/csv\r\n\r\n').encode(), data,
                  f'\r\n--{boundary}--\r\n'.encode()])
    request = urllib.request.Request(base + '/command/core/create-project-from-upload?csrf_token=' + token,
                                     data=b''.join(parts), headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    with urllib.request.urlopen(request, timeout=60) as response:
        project = urllib.parse.parse_qs(urllib.parse.urlparse(response.url).query)['project'][0]
        response.read()
    operations = []
    expressions = {
        'title': 'grel:if(isBlank(value),"",value.replace(/\\s+/," ").trim())',
        'journal': 'grel:if(isBlank(value),"",value.replace(/\\s+/," ").trim())',
        'doi': 'grel:value.toLowercase().trim()',
    }
    for col, expression in expressions.items():
        operations.append({'op': 'core/column-addition', 'description': 'Retain original and add cleaned ' + col,
                           'engineConfig': {'mode': 'row-based', 'facets': []}, 'newColumnName': col + '_clean',
                           'columnInsertIndex': len(fields) + len(operations), 'baseColumnName': col,
                           'expression': expression, 'onError': 'keep-original'})
    def post(command, payload, query=None):
        params = {'csrf_token': token, 'project': project} | (query or {})
        request = urllib.request.Request(base + '/command/core/' + command + '?' + urllib.parse.urlencode(params),
                                         data=urllib.parse.urlencode(payload).encode())
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    result = json.loads(post('apply-operations', {'operations': json.dumps(operations)}))
    if result.get('code') != 'ok':
        raise ValueError('OpenRefine operations failed: ' + str(result))
    cleaned_bytes = post('export-rows', {'engine': json.dumps({'facets': [], 'mode': 'row-based'})}, {'format': 'csv'})
    cleaned = list(csv.DictReader(io.StringIO(cleaned_bytes.decode('utf-8-sig'))))
    if len(cleaned) != len(records):
        raise ValueError('OpenRefine row count changed.')
    for before, after in zip(records, cleaned):
        if any(before[k] != after[k] for k in fields):
            raise ValueError('Original metadata changed.')
    output.write_bytes(cleaned_bytes)
    changed = {key: sum(r[key] != r[key + '_clean'] for r in cleaned) for key in expressions}
    audit = {'tool': 'OpenRefine', 'tool_version': version, 'operations': operations,
             'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
             'output_sha256': hashlib.sha256(cleaned_bytes).hexdigest(), 'rows': len(cleaned),
             'changed_cells_by_column': changed, 'original_columns_preserved': True,
             'semantic_reconciliation_performed': False, 'chemical_entities_merged': 0}
    operations_output.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'rows': len(cleaned), 'changes': changed, 'version': version}, indent=2))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--audit-output', type=Path, required=True)
    p.add_argument('--server', default='http://127.0.0.1:3335')
    a = p.parse_args()
    clean(a.source, a.output, a.audit_output, a.server)
