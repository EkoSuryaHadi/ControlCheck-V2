from controlcheck.project_files import normalize_tasks


def test_normalize_tasks_excludes_summary_rows_and_keeps_task_uid():
    result = normalize_tasks([
        {'uid': 1, 'name': 'Phase', 'summary': True},
        {'uid': 2, 'name': 'Foundation', 'summary': False, 'percent_complete': 50},
    ])
    assert [row['Task UID'] for row in result['rows']] == ['2']
    assert result['headers'][:2] == ['Activity ID', 'Name']


def test_normalize_tasks_converts_project_datetimes_to_reporting_dates():
    result = normalize_tasks([{'uid': 2, 'name': 'Foundation', 'summary': False,
                               'planned_start': '2026-09-09T08:00',
                               'planned_finish': '2026-09-10T17:00'}])
    assert result['rows'][0]['Planned Start'] == '2026-09-09'
    assert result['rows'][0]['Planned Finish'] == '2026-09-10'


def test_normalize_tasks_preserves_schedule_intelligence_metadata():
    result = normalize_tasks([{'uid': 2, 'name': 'Foundation', 'summary': False,
                               'critical': True, 'milestone': True, 'total_slack': 0}])
    row = result['rows'][0]
    assert row['Is Critical'] == 'true'
    assert row['Is Milestone'] == 'true'
    assert row['Total Slack'] == '0'
