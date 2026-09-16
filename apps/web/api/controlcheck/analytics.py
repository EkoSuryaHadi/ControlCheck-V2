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
    critical_known = [r for r in rows if r.get('is_critical') is not None]
    milestone_known = [r for r in rows if r.get('is_milestone') is not None]
    slack_known = [r for r in rows if r.get('total_slack') is not None]
    dependency_known = [r for r in rows if r.get('predecessor_ids') is not None]
    critical = [r for r in critical_known if r['is_critical']]
    critical_overdue = [r for r in overdue if r.get('is_critical')]
    milestone_overdue = [r for r in overdue if r.get('is_milestone')]
    critical_exposure = [r for r in critical if r.get('total_slack') is not None and r['total_slack'] <= 0]
    by_id = {r['activity_id']: r for r in rows if r.get('activity_id')}
    successors = {}
    external_links = 0
    for row in dependency_known:
        for predecessor_id in row['predecessor_ids']:
            if predecessor_id in by_id:
                successors.setdefault(predecessor_id, []).append(row)
            else:
                external_links += 1
    cycle_components, indexes, lowlinks, stack, on_stack = [], {}, {}, [], set()
    next_index = 0

    def visit(activity_id):
        nonlocal next_index
        indexes[activity_id] = lowlinks[activity_id] = next_index
        next_index += 1
        stack.append(activity_id)
        on_stack.add(activity_id)
        for successor in successors.get(activity_id, []):
            successor_id = successor['activity_id']
            if successor_id not in indexes:
                visit(successor_id)
                lowlinks[activity_id] = min(lowlinks[activity_id], lowlinks[successor_id])
            elif successor_id in on_stack:
                lowlinks[activity_id] = min(lowlinks[activity_id], indexes[successor_id])
        if lowlinks[activity_id] == indexes[activity_id]:
            component = []
            while True:
                member = stack.pop()
                on_stack.remove(member)
                component.append(member)
                if member == activity_id:
                    break
            if len(component) > 1 or any(item['activity_id'] == activity_id for item in successors.get(activity_id, [])):
                cycle_components.append(component)

    for activity_id in by_id:
        if activity_id not in indexes:
            visit(activity_id)
    isolated = ([row for row in rows if not row.get('predecessor_ids') and not successors.get(row['activity_id'])]
                if len(dependency_known) == n and n > 1 else [])
    recovery_priorities = []
    for row in overdue:
        direct_successors = successors.get(row['activity_id'], [])
        successor_milestones = [item for item in direct_successors if item.get('is_milestone')]
        slack = row.get('total_slack')
        days_overdue = (date.fromisoformat(as_of) - date.fromisoformat(row['planned_finish'])).days
        recovery_priorities.append({
            'activity_id': row['activity_id'], 'name': row['name'],
            'planned_finish': row['planned_finish'], 'actual_progress': row.get('actual_progress'),
            'days_overdue': days_overdue, 'is_critical': bool(row.get('is_critical')),
            'total_slack': slack, 'predecessor_ids': list(row.get('predecessor_ids') or []),
            'successor_count': len(direct_successors),
            'successor_milestone_count': len(successor_milestones),
            'successor_ids': [item['activity_id'] for item in direct_successors[:5]],
            'citation': row['evidence'],
            '_score': (bool(row.get('is_critical')), slack is not None and slack <= 0,
                       -slack if slack is not None else float('-inf'),
                       len(successor_milestones), len(direct_successors), days_overdue,
                       100 - (row.get('actual_progress') or 0)),
        })
    recovery_priorities.sort(key=lambda item: item['_score'], reverse=True)
    recovery_priorities = [{key: value for key, value in item.items() if key != '_score'}
                           for item in recovery_priorities[:5]]
    impacted_ids, frontier = set(), [r['activity_id'] for r in critical_overdue]
    while frontier:
        predecessor_id = frontier.pop()
        for successor in successors.get(predecessor_id, []):
            successor_id = successor['activity_id']
            if successor_id not in impacted_ids:
                impacted_ids.add(successor_id)
                frontier.append(successor_id)
    impacted = [by_id[item] for item in impacted_ids]
    downstream_milestones = [r for r in impacted if r.get('is_milestone')]
    metrics = dict(activity_count=n, progress=progress, progress_basis=basis, bac=bac, ac=ac, pv=pv, ev=ev,
                   spi=spi, cpi=cpi, sv=ev-pv if ev is not None and pv is not None else None,
                   cv=ev-ac if ev is not None and ac is not None else None,
                   overdue=len(overdue) if covered else None, overdue_coverage=f'{len(covered)}/{n}',
                   critical_count=len(critical) if critical_known else None,
                   critical_overdue=len(critical_overdue) if critical_known else None,
                   milestone_overdue=len(milestone_overdue) if milestone_known else None,
                   critical_coverage=f'{len(critical_known)}/{n}', milestone_coverage=f'{len(milestone_known)}/{n}',
                   slack_coverage=f'{len(slack_known)}/{n}',
                   dependency_coverage=f'{len(dependency_known)}/{n}',
                   downstream_activities=len(impacted) if dependency_known else None,
                   downstream_milestones=len(downstream_milestones) if dependency_known else None,
                   dependency_external_links=external_links if dependency_known else None,
                   dependency_cycle_count=len(cycle_components) if dependency_known else None,
                   isolated_activities=len(isolated) if len(dependency_known) == n and n > 1 else None)
    if any(metrics[k] is None for k in ('bac','ac','pv','ev','progress','spi','cpi')):
        limitations.append('Sebagian metrik tidak tersedia karena data tidak lengkap atau penyebut nol.')
    if len(covered) != n:
        limitations.append('Cakupan keterlambatan belum lengkap; tidak semua aktivitas dapat dinilai.')
    if not critical_known:
        limitations.append('Status critical tidak tersedia dari sumber schedule; critical path tidak dapat dinilai.')
    if not dependency_known:
        limitations.append('Relasi dependency tidak tersedia dari sumber schedule; dampak penerus tidak dapat dinilai.')
    elif external_links:
        limitations.append(f'{external_links} relasi dependency merujuk aktivitas di luar snapshot dan tidak dianalisis.')
    limitations.append('Satu snapshot tidak menunjukkan tren, penyebab perubahan, atau forecast selesai.')
    evidence = [r['evidence'] for r in rows]
    insights = []
    if overdue:
        insights.append(dict(id='overdue', severity='high', title=f'{len(overdue)} aktivitas melewati rencana selesai',
                             detail=f'Belum mencapai 100% pada {as_of}. Cakupan penilaian: {len(covered)}/{n}.',
                             action='Tinjau status aktual dan rencana pemulihan bersama planner.', evidence=[r['evidence'] for r in overdue]))
    if critical_overdue:
        insights.append(dict(id='critical_overdue', severity='high',
                             title=f'{len(critical_overdue)} aktivitas critical melewati rencana selesai',
                             detail='Status critical berasal dari file schedule; aktivitas belum mencapai 100%.',
                             action='Prioritaskan pemulihan bersama planner dan tinjau predecessor aktivitas.',
                             evidence=[r['evidence'] for r in critical_overdue]))
    if milestone_overdue:
        insights.append(dict(id='milestone_overdue', severity='high',
                             title=f'{len(milestone_overdue)} milestone melewati rencana selesai',
                             detail='Milestone belum mencapai 100% pada status date snapshot.',
                             action='Konfirmasi dampak milestone dan tindakan pemulihan dengan tim proyek.',
                             evidence=[r['evidence'] for r in milestone_overdue]))
    if critical_exposure:
        insights.append(dict(id='critical_exposure', severity='medium',
                             title=f'{len(critical_exposure)} aktivitas critical tanpa float positif',
                             detail='Total slack nol atau negatif berdasarkan file schedule.',
                             action='Pantau aktivitas ini pada pembaruan schedule berikutnya.',
                             evidence=[r['evidence'] for r in critical_exposure]))
    if impacted:
        impact_evidence = [r['evidence'] for r in critical_overdue + impacted]
        insights.append(dict(id='dependency_impact', severity='high',
                             title=f'{len(impacted)} aktivitas berada pada jalur dampak critical delay',
                             detail=f'{len(downstream_milestones)} di antaranya adalah milestone penerus. Relasi berasal dari dependency schedule.',
                             action='Tinjau urutan kerja dan rencana pemulihan bersama planner sebelum menetapkan dampak tanggal.',
                             evidence=impact_evidence))
    if cycle_components:
        cycle_rows = [by_id[activity_id] for component in cycle_components for activity_id in component]
        insights.append(dict(id='dependency_cycle', severity='high',
                             title=f'{len(cycle_components)} dependency cycle perlu ditinjau',
                             detail='Aktivitas dalam cycle saling bergantung berdasarkan file schedule.',
                             action='Periksa relationship di schedule sumber sebelum memakai hasil analisis network.',
                             evidence=[row['evidence'] for row in cycle_rows]))
    if isolated:
        insights.append(dict(id='isolated_activity', severity='medium',
                             title=f'{len(isolated)} aktivitas terisolasi dalam dependency schedule',
                             detail='Aktivitas ini tidak memiliki predecessor atau successor pada snapshot yang diunggah.',
                             action='Konfirmasi apakah aktivitas ini memang berdiri sendiri atau ada relasi yang belum diekspor.',
                             evidence=[row['evidence'] for row in isolated]))
    if spi is not None and spi < 1:
        insights.append(dict(id='spi', severity='medium', title=f'SPI {spi:.2f}: earned value di bawah rencana',
                             detail='EV / PV < 1. Ini bukan estimasi jumlah hari keterlambatan.',
                             action='Validasi bobot biaya dan kemajuan aktivitas terhadap baseline.', evidence=evidence))
    if cpi is not None and cpi < 1:
        insights.append(dict(id='cpi', severity='high', title=f'CPI {cpi:.2f}: biaya aktual melebihi earned value',
                             detail='EV / AC < 1 pada snapshot ini; tidak membuktikan penyebab biaya.',
                             action='Tinjau actual cost dan kuantitas pekerjaan yang diakui.', evidence=evidence))
    return dict(metrics=metrics, insights=insights, recovery_priorities=recovery_priorities,
                limitations=limitations, evidence=evidence)
