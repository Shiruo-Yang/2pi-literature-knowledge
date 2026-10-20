"""Parse selected source pages locally; raw text/table outputs stay private."""
import argparse
import hashlib
import importlib.metadata
import json
import logging
import time
from pathlib import Path


class WarningCollector(logging.Handler):
    """Retain parser warnings without interpreting them as scientific QC."""
    def __init__(self):
        super().__init__(logging.WARNING)
        self.messages = []

    def emit(self, record):
        self.messages.append({'logger': record.name, 'message': record.getMessage()})


def run(manifest, output, tool):
    if output.exists():
        raise ValueError('Fresh parser output directory required.')
    output.mkdir(parents=True)
    selected = json.loads(manifest.read_text(encoding='utf-8'))['documents']
    if tool == 'liteparse':
        from liteparse import LiteParse
    else:
        import torch
        torch.set_num_threads(2)
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions
        options = PdfPipelineOptions()
        options.do_ocr = False  # This pilot is intentionally limited to text-native PDFs.
        options.do_table_structure = True
        converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)})
    reports = []
    for row in selected:
        target = row['target_page']
        started = time.monotonic()
        status = {'document_id': row['document_id'], 'source_key': row['source_key'], 'doi': row['doi'],
                  'document_sha256': row['document_sha256'], 'target_page': target, 'tool': tool,
                  'tool_version': importlib.metadata.version(tool), 'scientific_status': 'parser_output_only_not_measurement_certification'}
        warning_handler = WarningCollector()
        logging.getLogger().addHandler(warning_handler)
        try:
            assert hashlib.sha256(Path(row['local_pdf']).read_bytes()).hexdigest() == row['document_sha256']
            if tool == 'liteparse':
                parser = LiteParse(ocr_enabled=False, target_pages=','.join(map(str, sorted({1, target}))), quiet=True, num_workers=2)
                result = parser.parse(row['local_pdf'])
                payload = {'text': result.text, 'pages': [p.model_dump() if hasattr(p, 'model_dump') else {
                    'page_num': p.page_num, 'width': p.width, 'height': p.height, 'text': p.text,
                    'text_items': [{'text': t.text, 'x': t.x, 'y': t.y, 'width': t.width, 'height': t.height} for t in p.text_items]
                } for p in result.pages]}
                path = output / (row['document_id'] + '.json')
                path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding='utf-8')
                status.update(status='parsed', page_count=len(result.pages), table_count='',
                              text_items=sum(len(p.text_items) for p in result.pages), output_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            else:
                result = converter.convert(row['local_pdf'], page_range=(target, target))
                path = output / (row['document_id'] + '.json')
                result.document.save_as_json(path)
                tables = []
                for index, table in enumerate(result.document.tables):
                    table.export_to_dataframe(doc=result.document).to_csv(output / f'{row["document_id"]}_table_{index}.csv', index=False, encoding='utf-8-sig')
                    tables.append({'table_index': index, 'rows': table.data.num_rows, 'columns': table.data.num_cols,
                                   'provenance': [p.model_dump(mode='json') for p in table.prov]})
                status.update(status='parsed', page_count=len(result.document.pages), table_count=len(tables),
                              tables=tables, output_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        except Exception as exc:
            status.update(status='failed', error_type=type(exc).__name__, failure_reason=str(exc)[:800])
        finally:
            logging.getLogger().removeHandler(warning_handler)
        status['runtime_warnings'] = warning_handler.messages
        status['elapsed_seconds'] = round(time.monotonic() - started, 3)
        reports.append(status)
        (output / 'status.json').write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({k: status[k] for k in ('doi', 'tool', 'status', 'elapsed_seconds')}, ensure_ascii=True), flush=True)
    return reports


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--tool', choices=['liteparse', 'docling'], required=True)
    a = p.parse_args()
    run(a.manifest, a.output, a.tool)
