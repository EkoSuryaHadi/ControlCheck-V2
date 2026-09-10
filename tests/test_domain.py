import pytest
from controlcheck.semantic import validate, suggest_mapping
from controlcheck.analytics import analyze
from controlcheck.importers import inspect_source, read_source


def rows():
    return [dict(activity_id='A1', name='Foundation', planned_finish='2026-09-01',
                 planned_progress='80', actual_progress='40', budget='1000', actual_cost='600')]


def test_mapping_and_validation():
    assert suggest_mapping(['Activity ID', 'Nama Aktivitas'])[0]['field'] == 'activity_id'
    result = validate(rows(), {k: k for k in rows()[0]}, 'source-1', 'Sheet1')
    assert not result['errors']
    assert result['rows'][0]['evidence']['row'] == 2


@pytest.mark.parametrize('field,value', [('actual_progress', '101'), ('budget', '-1'),
    ('planned_finish', 'not a date'), ('actual_cost', 'NaN'), ('weight', '0')])
def test_invalid_values_block(field, value):
    r = rows(); r[0][field] = value
    assert validate(r, {k: k for k in r[0]}, 's', 'CSV')['errors']


def test_duplicates_and_date_order_block():
    r = rows(); r[0]['planned_start'] = '2026-10-01'
    result = validate(r + r, {k: k for k in r[0]}, 's', 'CSV')
    assert {'duplicate_id', 'date_order'} <= {e['code'] for e in result['errors']}


def test_measures_and_zero_denominators():
    clean = validate(rows(), {k: k for k in rows()[0]}, 's', 'CSV')['rows']
    result = analyze(clean, '2026-09-08')
    assert result['metrics']['spi'] == .5
    assert result['metrics']['cpi'] == pytest.approx(2/3)
    assert result['metrics']['overdue'] == 1
    assert result['insights'][0]['evidence'][0]['source_id'] == 's'
    clean[0]['actual_cost'] = 0
    assert analyze(clean, '2026-09-08')['metrics']['cpi'] is None


def test_missing_does_not_become_zero_or_partial_total():
    clean = validate(rows(), {k: k for k in rows()[0]}, 's', 'CSV')['rows']
    clean.append(dict(activity_id='A2', name='Unknown', evidence={'source_id':'s','sheet':'CSV','row':3}))
    result = analyze(clean, '2026-09-08')
    assert result['metrics']['bac'] is None
    assert result['metrics']['progress'] is None
    assert result['metrics']['overdue_coverage'] == '1/2'


def test_csv_quoted_fields_and_duplicate_headers():
    assert read_source('a.csv', b'Activity ID,Name\nA1,"Road, north"')['rows'][0]['Name'] == 'Road, north'
    with pytest.raises(ValueError, match='header'):
        read_source('a.csv', b'Name,Name\na,b')


def test_csv_header_row_and_source_provenance():
    content = b'Report title,\nGenerated,2026-09-09\nActivity ID,Name\nA1,Foundation'
    result = read_source('a.csv', content, header_row=3)
    assert result['headers'] == ['Activity ID', 'Name']
    assert result['rows'][0]['__source_row__'] == 4


def test_inspect_xlsx_lists_sheets_and_suggests_header():
    from io import BytesIO
    from openpyxl import Workbook
    book = Workbook(); book.active.title = 'Cover'; ws = book.create_sheet('Schedule')
    ws.append(['Weekly report']); ws.append([]); ws.append(['Activity ID', 'Name']); ws.append(['A1', 'Work'])
    stream = BytesIO(); book.save(stream)
    result = inspect_source('schedule.xlsx', stream.getvalue())
    assert [s['name'] for s in result['sheets']] == ['Cover', 'Schedule']
    assert result['sheets'][1]['suggested_header_row'] == 3


def test_explicit_locale_and_percent_conversions():
    raw = [dict(activity_id='A1', name='Work', planned_finish='31/12/2026',
                planned_progress='0,80', actual_progress='0,40', budget='1000,50')]
    result = validate(raw, {k:k for k in raw[0]}, 's', 'CSV', {
        'date_format':'dmy', 'decimal_separator':'comma', 'percent_scale':'fraction'})
    row = result['rows'][0]
    assert not result['errors']
    assert row['planned_finish'] == '2026-12-31'
    assert row['actual_progress'] == 40
    assert row['budget'] == 1000.5


def test_progress_requires_activity_id_but_not_name():
    rows = [{'Activity ID': 'A-1', 'Actual Progress': '55', '__source_row__': 2}]
    result = validate(rows, {'Activity ID': 'activity_id', 'Actual Progress': 'actual_progress'},
                      'progress-1', 'Progress', dataset_type='progress')
    assert result['errors'] == []
    assert result['rows'][0]['name'] is None


def test_validation_keeps_schedule_intelligence_metadata():
    result = validate(
        [{'Activity ID': 'A1', 'Name': 'Foundation', 'Is Critical': 'true', 'Is Milestone': 'false', 'Total Slack': '-1'}],
        {'Activity ID': 'activity_id', 'Name': 'name', 'Is Critical': 'is_critical',
         'Is Milestone': 'is_milestone', 'Total Slack': 'total_slack'}, 'source', 'Schedule', dataset_type='schedule')
    assert result['errors'] == []
    assert result['rows'][0]['is_critical'] is True
    assert result['rows'][0]['total_slack'] == -1


def test_schedule_intelligence_flags_critical_and_milestone_risks():
    clean = validate(rows(), {k: k for k in rows()[0]}, 's', 'CSV')['rows']
    clean[0].update(is_critical=True, is_milestone=True, total_slack=0)
    result = analyze(clean, '2026-09-08')
    assert result['metrics']['critical_count'] == 1
    assert result['metrics']['critical_overdue'] == 1
    assert result['metrics']['milestone_overdue'] == 1
    assert {'critical_overdue', 'milestone_overdue', 'critical_exposure'} <= {item['id'] for item in result['insights']}


def test_schedule_intelligence_makes_no_claim_without_source_metadata():
    clean = validate(rows(), {k: k for k in rows()[0]}, 's', 'CSV')['rows']
    result = analyze(clean, '2026-09-08')
    assert result['metrics']['critical_count'] is None
    assert not {'critical_overdue', 'milestone_overdue', 'critical_exposure'} & {item['id'] for item in result['insights']}


def test_dependency_impact_follows_actual_predecessor_links_only():
    raw = [
        dict(activity_id='A', name='Late critical', planned_finish='2026-09-01', actual_progress='20', is_critical='true'),
        dict(activity_id='B', name='Downstream work', planned_finish='2026-09-30', actual_progress='0', predecessor_ids='A'),
        dict(activity_id='C', name='Milestone', planned_finish='2026-10-01', actual_progress='0', is_milestone='true', predecessor_ids='B'),
        dict(activity_id='D', name='Unrelated', planned_finish='2026-09-30', actual_progress='0'),
    ]
    mapping = {key: key for key in raw[0]}
    # Apply a complete mapping across the union of columns.
    mapping.update({'is_milestone': 'is_milestone', 'predecessor_ids': 'predecessor_ids'})
    for row in raw:
        for key in mapping:
            row.setdefault(key, '')
    clean = validate(raw, mapping, 's', 'Schedule', dataset_type='schedule')['rows']
    result = analyze(clean, '2026-09-08')
    assert result['metrics']['downstream_activities'] == 2
    assert result['metrics']['downstream_milestones'] == 1
    impact = next(item for item in result['insights'] if item['id'] == 'dependency_impact')
    assert len(impact['evidence']) == 3


def test_dependency_impact_is_absent_without_actual_links():
    clean = validate(rows(), {k: k for k in rows()[0]}, 's', 'CSV')['rows']
    clean[0]['is_critical'] = True
    result = analyze(clean, '2026-09-08')
    assert result['metrics']['downstream_activities'] is None
    assert 'dependency_impact' not in {item['id'] for item in result['insights']}
