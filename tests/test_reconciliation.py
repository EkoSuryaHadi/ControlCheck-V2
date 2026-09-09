from controlcheck.reconciliation import reconcile


def source(source_id, rows):
    return {'id': source_id, 'sheet': source_id, 'rows': rows}


def row(activity_id, **fields):
    return {'activity_id': activity_id, 'name': fields.pop('name', activity_id),
            'evidence': {'source_id': 'schedule-1', 'sheet': 'Schedule', 'row': 2}, **fields}


def test_reconcile_merges_sources_and_preserves_field_evidence():
    schedule = source('schedule-1', [row('A-1', budget=1000), row('A-2')])
    progress = source('progress-1', [row('A-1', actual_progress=55)])
    cost = source('cost-1', [row('A-1', actual_cost=500)])
    result = reconcile(schedule, progress, cost)
    merged = result['rows'][0]
    assert merged['actual_progress'] == 55
    assert merged['actual_cost'] == 500
    assert merged['field_evidence']['actual_progress']['source_id'] == 'progress-1'
    assert result['coverage'] == {'schedule': 2, 'progress_matched': 1, 'cost_matched': 1}
    assert result['errors'] == []


def test_reconcile_blocks_duplicate_and_unmatched_ids():
    schedule = source('schedule-1', [row('A-1')])
    progress = source('progress-1', [row('A-1'), row('A-1'), row('MISSING')])
    result = reconcile(schedule, progress)
    assert {issue['code'] for issue in result['errors']} == {'duplicate_id', 'unmatched_activity'}
