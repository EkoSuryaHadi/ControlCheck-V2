from controlcheck.comparison import compare_snapshots


def snapshot(version, as_of, rows):
    return {
        'id': f's{version}', 'version': version, 'as_of': as_of, 'filename': f'v{version}.csv',
        'sheet': 'Schedule', 'currency': 'IDR', 'rows': rows,
    }


def row(activity_id, finish, progress, row_number):
    return {'activity_id': activity_id, 'name': activity_id, 'planned_finish': finish,
            'actual_progress': progress, 'planned_progress': progress, 'budget': 100,
            'actual_cost': 100, 'weight': 1,
            'evidence': {'source_id': 'source', 'sheet': 'Schedule', 'row': row_number}}


def test_comparison_reports_measured_metric_and_activity_changes_only():
    previous = snapshot(1, '2026-09-08', [row('A', '2026-09-07', 50, 2), row('B', '2026-09-20', 0, 3)])
    current = snapshot(2, '2026-09-15', [row('A', '2026-09-07', 100, 2), row('C', '2026-09-10', 10, 4)])
    result = compare_snapshots(previous, current)

    assert result['previous_snapshot']['version'] == 1
    assert result['current_snapshot']['version'] == 2
    assert result['activities']['added_ids'] == ['C']
    assert result['activities']['removed_ids'] == ['B']
    assert result['activities']['progress_changed_ids'] == ['A']
    assert result['activities']['newly_overdue_ids'] == ['C']
    assert result['activities']['resolved_overdue_ids'] == ['A']
    assert result['metrics']['progress_delta'] is not None
    assert 'penyebab' in result['limitations'][2]


def test_comparison_requires_a_previous_snapshot():
    assert compare_snapshots(None, snapshot(1, '2026-09-08', [])) is None
