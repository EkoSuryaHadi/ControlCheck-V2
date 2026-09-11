from controlcheck.project_files import _xml_tasks, normalize_tasks


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


def test_normalize_tasks_preserves_actual_predecessor_task_uids():
    result = normalize_tasks([{'uid': 2, 'name': 'Foundation', 'summary': False,
                               'predecessor_ids': ['1', 3]}])
    assert 'Predecessor IDs' in result['headers']
    assert result['rows'][0]['Predecessor IDs'] == '1;3'


def test_project_xml_reads_task_predecessor_uids():
    tasks = _xml_tasks(b'''<Project xmlns="http://schemas.microsoft.com/project">
      <Tasks><Task><UID>2</UID><Name>Successor</Name><PredecessorLink><PredecessorUID>1</PredecessorUID></PredecessorLink></Task></Tasks>
    </Project>''')
    assert tasks[0]['predecessor_ids'] == ['1']


def test_normalize_tasks_prefers_primavera_activity_id_and_metadata():
    result = normalize_tasks([{
        'uid': 9001, 'activity_id': 'ENG-010', 'name': 'Engineering',
        'calendar': '6D Calendar', 'constraint_type': 'Start On',
        'constraint_date': '2026-10-01', 'baseline_start': '2026-09-01',
        'baseline_finish': '2026-09-10',
    }])
    row = result['rows'][0]
    assert row['Activity ID'] == 'ENG-010'
    assert row['Calendar'] == '6D Calendar'
    assert row['Baseline Finish'] == '2026-09-10'


def test_normalize_tasks_resolves_predecessors_to_activity_ids():
    result = normalize_tasks([
        {'uid': 1, 'activity_id': 'A-100', 'name': 'First'},
        {'uid': 2, 'activity_id': 'B-200', 'name': 'Second', 'predecessor_uids': [1]},
    ])
    assert result['rows'][1]['Predecessor IDs'] == 'A-100'
import pytest
from controlcheck import project_files
from controlcheck.project_files import read_project_file


def test_read_project_file_routes_xer_to_adapter(monkeypatch):
    monkeypatch.setattr(project_files, '_xer_tasks', lambda content: [
        {'uid': 1, 'activity_id': 'P6-1', 'name': 'P6 task'},
    ])
    result = read_project_file('schedule.xer', b'%T\tPROJECT')
    assert result['sheet'] == 'Primavera P6'
    assert result['rows'][0]['Activity ID'] == 'P6-1'


def test_xer_parser_unavailable_has_clear_diagnostic(monkeypatch):
    def unavailable(content):
        raise ValueError('Parser XER belum tersedia di server.')
    monkeypatch.setattr(project_files, '_xer_tasks', unavailable)
    with pytest.raises(ValueError, match='Parser XER belum tersedia'):
        read_project_file('schedule.xer', b'%T\tPROJECT')


def test_project_file_upload_limit_is_larger_than_tabular_limit():
    from controlcheck.importers import MAX_BYTES, MAX_PROJECT_BYTES, max_upload_bytes
    assert max_upload_bytes('schedule.xer') == MAX_PROJECT_BYTES
    assert max_upload_bytes('schedule.mpp') == MAX_PROJECT_BYTES
    assert max_upload_bytes('schedule.xlsx') == MAX_BYTES
    assert MAX_PROJECT_BYTES == 50 * 1024 * 1024


def test_xer_size_check_uses_project_limit(monkeypatch):
    from controlcheck import importers
    monkeypatch.setattr(importers, 'MAX_PROJECT_BYTES', 10 * 1024 * 1024)
    with pytest.raises(ValueError, match='10 MB'):
        importers.inspect_source('schedule.xer', b'x' * (10 * 1024 * 1024 + 1))


def test_temp_project_file_cleanup_does_not_mask_parser_result(monkeypatch):
    def locked(path):
        raise PermissionError('file is still held by MPXJ')
    monkeypatch.setattr(project_files.os.path, 'exists', lambda path: True)
    monkeypatch.setattr(project_files.os, 'unlink', locked)
    project_files._remove_temp_file('temporary.xer')


def test_xer_tabular_fallback_reads_task_and_predecessor_records():
    content = b'''%T\tTASK\n%F\ttask_id\ttask_code\ttask_name\ttarget_start_date\ttarget_end_date\tphys_complete_pct\tcritical_flag\n%R\t1\tA-100\tFoundation\t2026-01-01 08:00\t2026-01-10 17:00\t40\tY\n%R\t2\tB-200\tStructure\t2026-01-11\t2026-01-20\t0\tN\n%T\tTASKPRED\n%F\ttask_id\tpred_task_id\n%R\t2\t1\n%E\n'''
    result = project_files._xer_tasks_tabular(content)
    assert result[0]['activity_id'] == 'A-100'
    assert result[0]['planned_start'] == '2026-01-01'
    assert result[1]['predecessor_uids'] == ['1']


def test_xer_tabular_fallback_accepts_windows_1252_export():
    content = ('%T\tTASK\n%F\ttask_id\ttask_code\ttask_name\n%R\t1\tA-100\tPérkerjaan\n%E\n').encode('cp1252')
    result = project_files._xer_tasks_tabular(content)
    assert result[0]['name'] == 'Pérkerjaan'
