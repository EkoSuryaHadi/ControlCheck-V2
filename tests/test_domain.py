import pytest
from controlcheck.semantic import validate, suggest_mapping
from controlcheck.analytics import analyze
from controlcheck.importers import read_source


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

