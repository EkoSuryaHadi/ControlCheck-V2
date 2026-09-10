from controlcheck.analytics import analyze
from controlcheck.forecast_readiness import assess_forecast_readiness


def row(activity_id, start, finish, progress, predecessors=()):
    return {
        'activity_id': activity_id, 'name': activity_id, 'planned_start': start,
        'planned_finish': finish, 'actual_progress': progress, 'planned_progress': progress,
        'budget': None, 'actual_cost': None, 'weight': None, 'is_critical': None,
        'is_milestone': None, 'total_slack': None, 'predecessor_ids': predecessors,
        'evidence': {'source_id': 'source', 'sheet': 'Schedule', 'row': 2},
    }


def snapshot(version, as_of, rows):
    return {'id': f's{version}', 'version': version, 'as_of': as_of, 'rows': rows,
            'filename': 'schedule.csv', 'sheet': 'Schedule', 'currency': 'IDR'}


def test_ready_when_history_schedule_and_network_are_complete():
    current = snapshot(2, '2026-09-15', [
        row('A', '2026-09-01', '2026-09-10', 100),
        row('B', '2026-09-11', '2026-09-20', 20, ('A',)),
    ])
    history = [current, snapshot(1, '2026-09-08', current['rows'])]

    result = assess_forecast_readiness(current, history, analyze(current['rows'], current['as_of']))

    assert result['status'] == 'ready_for_method'
    assert result['blockers'] == []
    assert result['reporting_dates'] == ['2026-09-08', '2026-09-15']


def test_missing_history_blocks_readiness():
    current = snapshot(1, '2026-09-15', [row('A', '2026-09-01', '2026-09-20', 20)])

    result = assess_forecast_readiness(current, [current], analyze(current['rows'], current['as_of']))

    assert result['status'] == 'not_ready'
    assert any(check['id'] == 'history' and check['status'] == 'missing' for check in result['checks'])


def test_cycle_and_external_dependency_block_readiness():
    current = snapshot(2, '2026-09-15', [
        row('A', '2026-09-01', '2026-09-20', 20, ('B', 'OUTSIDE')),
        row('B', '2026-09-01', '2026-09-20', 20, ('A',)),
    ])
    history = [current, snapshot(1, '2026-09-08', current['rows'])]

    result = assess_forecast_readiness(current, history, analyze(current['rows'], current['as_of']))

    assert result['status'] == 'needs_attention'
    assert {'dependency_cycle', 'external_dependency'} <= {
        check['id'] for check in result['checks'] if check['status'] == 'blocked'
    }
