"""Pure merge rules for one Schedule master and optional Progress/Cost sources."""


def _evidence(source, row):
    current = row.get('evidence', {})
    return {'source_id': source['id'], 'sheet': source['sheet'], 'row': current.get('row')}


def _index(source, dataset, errors):
    indexed = {}
    for row in source.get('rows', []):
        activity_id = row.get('activity_id')
        if activity_id in indexed:
            errors.append({'code': 'duplicate_id', 'dataset': dataset, 'activity_id': activity_id,
                           'message': f'Activity ID {activity_id} berulang pada {dataset}.'})
        else:
            indexed[activity_id] = row
    return indexed


def reconcile(schedule, progress=None, cost=None):
    errors = []
    schedule_index = _index(schedule, 'schedule', errors)
    progress_index = _index(progress, 'progress', errors) if progress else {}
    cost_index = _index(cost, 'cost', errors) if cost else {}
    for dataset, indexed in (('progress', progress_index), ('cost', cost_index)):
        for activity_id in indexed:
            if activity_id not in schedule_index:
                errors.append({'code': 'unmatched_activity', 'dataset': dataset, 'activity_id': activity_id,
                               'message': f'Activity ID {activity_id} pada {dataset} tidak ada di Schedule.'})
    rows = []
    for activity_id, schedule_row in schedule_index.items():
        merged = {**schedule_row, 'evidence': _evidence(schedule, schedule_row),
                  'field_evidence': {}}
        for field in ('activity_id', 'name', 'planned_start', 'planned_finish', 'planned_progress', 'weight', 'budget'):
            if merged.get(field) is not None:
                merged['field_evidence'][field] = _evidence(schedule, schedule_row)
        if progress and activity_id in progress_index:
            source_row = progress_index[activity_id]
            if source_row.get('actual_progress') is not None:
                merged['actual_progress'] = source_row['actual_progress']
                merged['field_evidence']['actual_progress'] = _evidence(progress, source_row)
        if cost and activity_id in cost_index:
            source_row = cost_index[activity_id]
            for field in ('budget', 'actual_cost'):
                if source_row.get(field) is not None:
                    merged[field] = source_row[field]
                    merged['field_evidence'][field] = _evidence(cost, source_row)
        rows.append(merged)
    return {
        'rows': rows,
        'errors': errors,
        'coverage': {'schedule': len(schedule_index), 'progress_matched': len(set(schedule_index) & set(progress_index)),
                     'cost_matched': len(set(schedule_index) & set(cost_index))},
        'source_ids': [item['id'] for item in (schedule, progress, cost) if item],
    }
