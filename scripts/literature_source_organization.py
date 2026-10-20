"""Exact-DOI bibliography fills and manuscript-aligned document dossiers."""
import json
import re
from collections import Counter, defaultdict


def comparison_key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold())


def apply_bibliography(papers, metadata):
    by_doi = defaultdict(list)
    for index, row in enumerate(metadata, 1):
        by_doi[row['doi_clean']].append((index, row))
    updates, differences = [], []
    for paper in papers:
        for field in ('title', 'year', 'journal'):
            cleaned = field + '_clean' if field in ('title', 'journal') else field
            candidates = [(index, row, row[cleaned]) for index, row in by_doi[paper['doi']] if row[cleaned]]
            values = sorted({v for _, _, v in candidates})
            if not paper[field] and len(values) == 1:
                paper[field] = values[0]
                for index, row, value in candidates:
                    updates.append({'source_key': paper['source_key'], 'field_name': field, 'before_value': '',
                                    'after_value': value, 'input_row': index, 'zotero_item_key': row['zotero_item_key'],
                                    'asset_id': 'zotero_metadata_cleaned', 'action': 'fill_empty_by_exact_doi_without_overwriting_existing'})
            elif values and (len(values) > 1 or paper[field] not in values):
                formatted = bool(paper[field]) and all(comparison_key(value) == comparison_key(paper[field]) for value in values)
                differences.append({'source_key': paper['source_key'], 'field_name': field, 'retained_value': paper[field],
                                    'candidate_values': json.dumps(values, ensure_ascii=False),
                                    'difference_type': 'formatting_variant' if formatted else 'content_difference_not_adjudicated',
                                    'action': 'retain_existing_value_and_report_difference'})
    return updates, differences


def append_source_tables(db, table, papers, projection, updates, differences, parser_reports, binding_checks):
    table('bibliography_updates', updates, ['source_key','field_name','before_value','after_value','input_row','zotero_item_key','asset_id','action'],
          'PRIMARY KEY(source_key,field_name,input_row),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    table('bibliography_differences', differences, ['source_key','field_name','retained_value','candidate_values','difference_type','action'],
          'PRIMARY KEY(source_key,field_name),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    document_groups = defaultdict(list)
    for row in projection['documents']:
        if row['document_sha256']:
            document_groups[row['document_sha256']].append(row)
    documents = []
    for row in projection['documents']:
        group = document_groups.get(row['document_sha256'], [])
        source_count = len({r['source_key'] for r in group})
        documents.append(row | {'same_content_attachment_count': len(group), 'same_content_source_count': source_count,
                                'reuse_status': 'content_not_fingerprinted_non_pdf_or_missing' if not row['document_sha256'] else
                                'cross_source_same_file_requires_binding_review' if source_count > 1 else
                                'same_source_duplicate_attachment' if len(group) > 1 else 'no_duplicate_content_detected_in_snapshot'})
    table('source_documents', documents, constraints='PRIMARY KEY(document_id),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    table('document_binding_checks', binding_checks, constraints='PRIMARY KEY(document_id),FOREIGN KEY(document_id) REFERENCES source_documents(document_id),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    reuse = []
    for digest, group in sorted(document_groups.items()):
        if len(group) > 1:
            keys = sorted({r['source_key'] for r in group})
            reuse.append({'document_sha256': digest, 'attachment_count': len(group), 'source_count': len(keys),
                          'source_keys': ';'.join(keys), 'document_ids': ';'.join(sorted(r['document_id'] for r in group)),
                          'classification': 'cross_source_reuse_pending_binding_review' if len(keys) > 1 else 'same_source_duplicate_attachment',
                          'action': 'retain_all_links_do_not_count_as_independent_originals'})
    table('document_reuse_groups', reuse, ['document_sha256','attachment_count','source_count','source_keys','document_ids','classification','action'],
          'PRIMARY KEY(document_sha256)')
    modules = defaultdict(set)
    for row in db.execute('SELECT source_key,module_id FROM evidence_index UNION SELECT s.source_key,r.module_id FROM rule_sources s JOIN knowledge_rules r USING(rule_id) UNION SELECT source_key,\'property_profile\' FROM profile_sources UNION SELECT source_key,module_id FROM source_structures UNION SELECT source_key,module_id FROM source_measurements'):
        modules[row['source_key']].add(row['module_id'])
    dossiers = []
    for paper in papers:
        related = [r for r in documents if r['source_key'] == paper['source_key']]
        dossiers.append({'source_key': paper['source_key'], 'doi': paper['doi'], 'title': paper['title'],
                         'year': paper['year'], 'journal': paper['journal'], 'research_modules': ';'.join(sorted(modules[paper['source_key']])),
                         'field_evidence_count': paper['field_evidence_count'], 'attachment_links': len(related),
                         'local_pdf_links': sum(r['availability'] == 'local_pdf_available' for r in related),
                         'unique_local_file_hashes': len({r['document_sha256'] for r in related if r['document_sha256']}),
                         'cross_source_shared_file_links': sum(r['reuse_status'] == 'cross_source_same_file_requires_binding_review' for r in related),
                         'dossier_status': 'bibliography_and_document_inventory_not_full_experiment_extraction'})
    table('source_dossiers', dossiers, constraints='PRIMARY KEY(source_key),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    fields = ['document_id','source_key','doi','document_sha256','target_page','tool','tool_version','status',
              'page_count','table_count','text_items','output_sha256','failure_category','scientific_status','runtime_observations']
    table('document_parser_pilot', parser_reports, fields,
          'PRIMARY KEY(document_id,tool),FOREIGN KEY(document_id) REFERENCES source_documents(document_id),FOREIGN KEY(source_key) REFERENCES papers(source_key)')
    return {'zotero_matched_sources': projection['summary']['matched_source_dois'],
            'bibliography_cells_filled': len({(r['source_key'],r['field_name']) for r in updates}),
            'bibliography_fills_by_field': dict(Counter(r['field_name'] for r in updates)),
            'bibliography_content_differences_retained': sum(r['difference_type'] == 'content_difference_not_adjudicated' for r in differences),
            'bibliography_format_variants_retained': sum(r['difference_type'] == 'formatting_variant' for r in differences),
            'local_pdf_links': sum(r['availability'] == 'local_pdf_available' for r in documents),
            'unique_local_pdf_hashes': len(document_groups),
            'same_source_duplicate_file_groups': sum(r['classification'] == 'same_source_duplicate_attachment' for r in reuse),
            'cross_source_shared_file_groups': sum(r['classification'] == 'cross_source_reuse_pending_binding_review' for r in reuse),
            'parser_attempts': len(parser_reports),
            'parser_successes': sum(r['status'] == 'parsed' for r in parser_reports),
            'docling_candidate_tables': sum(int(r.get('table_count') or 0) for r in parser_reports if r['tool'] == 'docling'),
            'parser_attempts_with_runtime_observations': sum(bool(json.loads(r.get('runtime_observations', '[]'))) for r in parser_reports),
            'first_page_binding_checks': len(binding_checks),
            'first_page_expected_doi_literal_found': sum(r['expected_doi_literal_found'] == 'true' for r in binding_checks),
            'new_experiment_labels': 0, 'zotero_library_mutations': 0}
