"""Pure deterministic measures: absence is not zero; one snapshot is not a trend."""
from datetime import date


def analyze(rows, as_of):
    date.fromisoformat(as_of)
    n = len(rows)
    limitations = []

    def total(*fields):
        if not rows or any(any(r.get(f) is None for f in fields) for r in rows):
            return None
        if len(fields) == 1:
            return sum(r[fields[0]] for r in rows)
        return sum(r[fields[0]] * r[fields[1]] / 100 for r in rows)

    bac, ac = total('budget'), total('actual_cost')
    pv, ev = total('budget', 'planned_progress'), total('budget', 'actual_progress')
    spi = ev / pv if ev is not None and pv is not None and pv > 0 else None
    cpi = ev / ac if ev is not None and ac is not None and ac > 0 else None
    if rows and all(r.get('weight') is not None for r in rows):
        weights, basis = [r['weight'] for r in rows], 'explicit_weight'
    elif any(r.get('weight') is not None for r in rows):
        weights, basis = [], 'incomplete_weights'
    elif bac is not None and bac > 0:
        weights, basis = [r['budget'] for r in rows], 'budget'
    else:
        weights, basis = [1 for _ in rows], 'equal_activity'
    progress = (sum(r['actual_progress'] * w for r, w in zip(rows, weights)) / sum(weights)
                if weights and sum(weights) > 0 and all(r.get('actual_progress') is not None for r in rows) else None)
    covered = [r for r in rows if r.get('planned_finish') and r.get('actual_progress') is not None]
    overdue = [r for r in covered if r['planned_finish'] < as_of and r['actual_progress'] < 100]
    metrics = dict(activity_count=n, progress=progress, progress_basis=basis, bac=bac, ac=ac, pv=pv, ev=ev,
                   spi=spi, cpi=cpi, sv=ev-pv if ev is not None and pv is not None else None,
                   cv=ev-ac if ev is not None and ac is not None else None,
                   overdue=len(overdue) if covered else None, overdue_coverage=f'{len(covered)}/{n}')
    if any(metrics[k] is None for k in ('bac','ac','pv','ev','progress','spi','cpi')):
        limitations.append('Sebagian metrik tidak tersedia karena data tidak lengkap atau penyebut nol.')
    if len(covered) != n:
        limitations.append('Cakupan keterlambatan belum lengkap; tidak semua aktivitas dapat dinilai.')
    limitations.append('Satu snapshot tidak menunjukkan tren, critical path, penyebab perubahan, atau forecast selesai.')
    evidence = [r['evidence'] for r in rows]
    insights = []
    if overdue:
        insights.append(dict(id='overdue', severity='high', title=f'{len(overdue)} aktivitas melewati rencana selesai',
                             detail=f'Belum mencapai 100% pada {as_of}. Cakupan penilaian: {len(covered)}/{n}.',
                             action='Tinjau status aktual dan rencana pemulihan bersama planner.', evidence=[r['evidence'] for r in overdue]))
    if spi is not None and spi < 1:
        insights.append(dict(id='spi', severity='medium', title=f'SPI {spi:.2f}: earned value di bawah rencana',
                             detail='EV / PV < 1. Ini bukan estimasi jumlah hari keterlambatan.',
                             action='Validasi bobot biaya dan kemajuan aktivitas terhadap baseline.', evidence=evidence))
    if cpi is not None and cpi < 1:
        insights.append(dict(id='cpi', severity='high', title=f'CPI {cpi:.2f}: biaya aktual melebihi earned value',
                             detail='EV / AC < 1 pada snapshot ini; tidak membuktikan penyebab biaya.',
                             action='Tinjau actual cost dan kuantitas pekerjaan yang diakui.', evidence=evidence))
    return dict(metrics=metrics, insights=insights, limitations=limitations, evidence=evidence)

