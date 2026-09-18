import pytest
from controlcheck.analytics import analyze, calculate_s_curve, calculate_evm_forecasts


def test_calculate_s_curve_normal():
    rows = [
        {
            'activity_id': 'A1', 'name': 'Task 1',
            'planned_start': '2026-09-01', 'planned_finish': '2026-09-10',
            'actual_progress': 100, 'weight': 50,
            'evidence': {'source_id': 's1', 'sheet': 'Sheet1', 'row': 1}
        },
        {
            'activity_id': 'A2', 'name': 'Task 2',
            'planned_start': '2026-09-05', 'planned_finish': '2026-09-20',
            'actual_progress': 20, 'weight': 50,
            'evidence': {'source_id': 's1', 'sheet': 'Sheet1', 'row': 2}
        },
    ]
    as_of = '2026-09-08'
    res = calculate_s_curve(rows, as_of)
    assert res['is_complete'] is True
    assert res['coverage'] == '2/2'
    points = res['points']
    assert isinstance(points, list)
    assert len(points) > 0

    first_point = points[0]
    last_point = points[-1]
    assert isinstance(first_point, dict) and isinstance(last_point, dict)
    assert first_point['planned_cumulative'] >= 0.0
    assert last_point['planned_cumulative'] == 100.0

    # For dates before or equal to as_of, actual_cumulative is numeric
    # For dates after as_of, actual_cumulative is None
    for pt in points:
        assert isinstance(pt, dict)
        if pt['date'] <= as_of:
            assert pt['actual_cumulative'] is not None
        else:
            assert pt['actual_cumulative'] is None


def test_calculate_s_curve_missing_dates():
    rows = [
        {
            'activity_id': 'A1', 'name': 'Task 1',
            'planned_start': None, 'planned_finish': '2026-09-10',
            'actual_progress': 50,
            'evidence': {'source_id': 's1', 'sheet': 'Sheet1', 'row': 1}
        }
    ]
    res = calculate_s_curve(rows, '2026-09-08')
    assert res['is_complete'] is False
    assert res['coverage'] == '0/1'
    points = res['points']
    assert isinstance(points, list)
    assert len(points) == 0


def test_calculate_evm_forecasts():
    metrics = {
        'bac': 10000000.0,
        'ac': 4000000.0,
        'ev': 5000000.0,
        'pv': 6000000.0,
        'cpi': 1.25,      # 5M / 4M
        'spi': 0.8333,    # 5M / 6M
    }
    f = calculate_evm_forecasts(metrics)
    assert f['eac_cpi'] == 8000000.0  # 10M / 1.25
    assert f['vac'] == 2000000.0      # 10M - 8M
    assert f['eac_composite'] is not None
    assert f['tcpi'] is not None
    # TCPI = (10M - 5M) / (10M - 4M) = 5M / 6M = 0.83
    assert f['tcpi'] == 0.83
    assert len(f['assumptions']) >= 2


def test_calculate_evm_forecasts_zero_or_missing():
    f_empty = calculate_evm_forecasts({})
    assert f_empty['eac_cpi'] is None
    assert f_empty['vac'] is None
    assert f_empty['tcpi'] is None
    assert len(f_empty['limitations']) > 0


def test_analyze_includes_advanced_analytics():
    rows = [
        {
            'activity_id': 'A1', 'name': 'Task 1',
            'planned_start': '2026-09-01', 'planned_finish': '2026-09-10',
            'planned_progress': 100, 'actual_progress': 100,
            'budget': 1000, 'actual_cost': 900,
            'evidence': {'source_id': 's1', 'sheet': 'Sheet1', 'row': 1}
        }
    ]
    result = analyze(rows, '2026-09-08')
    assert 's_curve' in result
    assert 'forecasts' in result
    assert result['s_curve']['is_complete'] is True
    assert result['forecasts']['eac_cpi'] is not None
