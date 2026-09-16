"""Deterministic project-data intake decisions."""
from .importers import inspect_source, read_source
from .reconciliation import reconcile
from .semantic import validate


def classify(headers, mapping):
    targets = {field for field in mapping.values() if field}
    if not {'activity_id', 'name'} <= targets:
        if 'activity_id' not in targets:
            return None
        if targets & {'actual_progress'} and not targets & {'budget', 'actual_cost'}:
            return 'progress'
        if targets & {'budget', 'actual_cost'}:
            return 'cost'
        return None
    if targets & {'actual_progress', 'actual_cost', 'budget'}:
        return 'combined'
    return 'schedule'


def decide_source(table, mapper):
    mapping = {item['column']: item['field'] for item in mapper.suggest(table['headers']) if item['field']}
    dataset_type = classify(table['headers'], mapping)
    decisions = [
        {'step': 'schema_mapping', 'message': 'Agent memetakan kolom dengan alias yang dikenal.'},
        {'step': 'source_type', 'message': ('Jenis data terdeteksi: ' + dataset_type) if dataset_type
         else 'Jenis data belum dapat dipastikan.'},
    ]
    return {'dataset_type': dataset_type, 'mapping': mapping, 'decisions': decisions}


def run_ingestion(project, uploads, repository, mapper):
    """Read uploaded files, publish a valid semantic snapshot, or return a receipt."""
    sources, decisions, issues = [], [], []
    for filename, content in uploads:
        try:
            inspection = inspect_source(filename, content)
            selected = inspection['sheets'][0]
            table = read_source(filename, content, selected['name'] if inspection['kind'] == 'xlsx' else None,
                                selected['suggested_header_row'])
            decision = decide_source(table, mapper)
            decisions.extend([{'filename': table['filename'], **item} for item in decision['decisions']])
            if not decision['dataset_type']:
                issues.append({'filename': table['filename'], 'code': 'ambiguous_source',
                               'message': 'Agent tidak dapat menentukan jenis data dari kolom file.'})
                continue
            table['dataset_type'] = decision['dataset_type']
            source = repository.add_source(project['id'], table)
            checked = validate(source['rows'], decision['mapping'], source['id'], source['sheet'],
                               source['normalization'], source['dataset_type'])
            sources.append({**source, 'rows': checked['rows'], 'mapping': decision['mapping']})
            issues.extend([{**item, 'filename': source['filename']} for item in checked['errors']])
        except ValueError as exc:
            issues.append({'filename': filename, 'code': 'read_error', 'message': str(exc)})
    schedule_sources = [item for item in sources if item['dataset_type'] in ('schedule', 'combined')]
    if len(schedule_sources) != 1:
        issues.append({'code': 'schedule_required', 'message': 'Unggah tepat satu sumber Schedule atau Combined.'})
    if issues:
        return {'status': 'needs_attention', 'summary': 'Agent memerlukan tinjauan data.',
                'sources': _source_receipts(sources), 'issues': issues, 'decisions': decisions,
                'coverage': {'schedule': 0, 'progress_matched': 0, 'cost_matched': 0}}
    schedule = schedule_sources[0]
    progress = next((item for item in sources if item['dataset_type'] == 'progress'), None)
    cost = next((item for item in sources if item['dataset_type'] == 'cost'), None)
    merged = reconcile(schedule, progress, cost)
    if merged['errors']:
        return {'status': 'needs_attention', 'summary': 'Agent menemukan data antar-sumber yang belum selaras.',
                'sources': _source_receipts(sources), 'issues': merged['errors'], 'decisions': decisions,
                'coverage': merged['coverage']}
    snapshot = repository.publish_reconciliation(project, schedule, [item for item in (schedule, progress, cost) if item],
                                                 {'schedule': schedule['mapping'],
                                                  'progress': progress['mapping'] if progress else None,
                                                  'cost': cost['mapping'] if cost else None}, merged['rows'])
    return {'status': 'published', 'summary': 'Agent selesai membaca dan menerbitkan snapshot proyek.',
            'snapshot': snapshot, 'sources': _source_receipts(sources), 'issues': [],
            'decisions': decisions, 'coverage': merged['coverage']}


def _source_receipts(sources):
    return [dict(id=item['id'], filename=item['filename'], dataset_type=item['dataset_type'],
                 sheet=item['sheet'], row_count=len(item['rows']), mapping=item['mapping']) for item in sources]
