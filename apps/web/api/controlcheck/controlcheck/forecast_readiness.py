"""Determine whether approved schedule evidence can support a later forecast method."""


def assess_forecast_readiness(snapshot, history, analysis):
    """Return a deterministic readiness gate; this function never forecasts an outcome."""
    metrics = analysis['metrics']
    rows = snapshot['rows']
    reporting_dates = sorted({item['as_of'] for item in history})
    checks = [
        _history_check(reporting_dates),
        _coverage_check(rows),
        _dependency_coverage_check(metrics, len(rows)),
        _network_check('dependency_cycle', metrics.get('dependency_cycle_count'),
                       'Dependency cycle perlu diperbaiki sebelum schedule dipakai untuk forecast.'),
        _network_check('external_dependency', metrics.get('dependency_external_links'),
                       'Ada relasi dependency ke aktivitas di luar snapshot; lengkapi schedule sebelum forecast.'),
        _remaining_work_check(rows),
    ]
    blockers = [check['detail'] for check in checks if check['status'] in ('missing', 'blocked')]
    status = ('needs_attention' if any(check['status'] == 'blocked' for check in checks)
              else 'not_ready' if blockers else 'ready_for_method')
    warnings = []
    if metrics.get('isolated_activities'):
        warnings.append(f"{metrics['isolated_activities']} aktivitas terisolasi perlu dikonfirmasi sebelum memilih metode forecast.")
    return {
        'status': status,
        'snapshot_id': snapshot['id'],
        'snapshot_version': snapshot['version'],
        'reporting_dates': reporting_dates,
        'checks': checks,
        'blockers': blockers,
        'warnings': warnings,
        'limitations': ['Forecast belum dihitung. Hasil ini hanya menilai kelayakan data dan schedule untuk memilih metode forecast.'],
    }


def _history_check(reporting_dates):
    if len(reporting_dates) >= 2:
        return _check('history', 'pass', f'{len(reporting_dates)} periode laporan tersedia untuk membaca perubahan data.')
    return _check('history', 'missing', 'Publikasikan minimal dua snapshot dengan tanggal laporan berbeda.')


def _coverage_check(rows):
    required = ('planned_start', 'planned_finish', 'actual_progress')
    missing = [field for field in required if any(row.get(field) is None for row in rows)]
    if not missing:
        return _check('schedule_dates', 'pass', 'Tanggal mulai, tanggal selesai, dan progress tersedia untuk seluruh aktivitas.')
    return _check('schedule_dates', 'missing', 'Lengkapi ' + ', '.join(missing) + ' untuk seluruh aktivitas schedule.')


def _dependency_coverage_check(metrics, count):
    coverage = metrics.get('dependency_coverage')
    if coverage == f'{count}/{count}':
        return _check('dependency_coverage', 'pass', 'Relasi dependency tersedia untuk seluruh aktivitas.')
    return _check('dependency_coverage', 'missing', f'Relasi dependency belum lengkap ({coverage or "0/0"}); ekspor predecessor untuk seluruh aktivitas.')


def _network_check(check_id, count, blocked_detail):
    if count is None:
        return _check(check_id, 'missing', 'Integritas dependency belum dapat dinilai karena relasi belum lengkap.')
    if count:
        return _check(check_id, 'blocked', blocked_detail)
    return _check(check_id, 'pass', 'Tidak ada masalah integritas dependency yang terdeteksi pada snapshot.')


def _remaining_work_check(rows):
    if any(row.get('actual_progress') is not None and row['actual_progress'] < 100 for row in rows):
        return _check('remaining_work', 'pass', 'Masih ada aktivitas belum selesai untuk dinilai oleh metode forecast.')
    return _check('remaining_work', 'missing', 'Tidak ada aktivitas tersisa pada snapshot; forecast penyelesaian tidak diperlukan.')


def _check(check_id, status, detail):
    return {'id': check_id, 'status': status, 'detail': detail}
