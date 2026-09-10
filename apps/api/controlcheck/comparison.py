"""Evidence-preserving comparison between two immutable project snapshots."""
from .analytics import analyze


def _activity_map(snapshot):
    return {row['activity_id']: row for row in snapshot['rows']}


def _overdue_ids(snapshot):
    as_of = snapshot['as_of']
    return {
        row['activity_id'] for row in snapshot['rows']
        if row.get('planned_finish') and row.get('actual_progress') is not None
        and row['planned_finish'] < as_of and row['actual_progress'] < 100
    }


def _delta(current, previous, key):
    current_value = current['metrics'].get(key)
    previous_value = previous['metrics'].get(key)
    return current_value - previous_value if current_value is not None and previous_value is not None else None


def compare_snapshots(previous_snapshot, current_snapshot):
    """Return observable changes only. Snapshot scope changes are never treated as performance changes."""
    if not previous_snapshot:
        return None
    previous = analyze(previous_snapshot['rows'], previous_snapshot['as_of'])
    current = analyze(current_snapshot['rows'], current_snapshot['as_of'])
    before, after = _activity_map(previous_snapshot), _activity_map(current_snapshot)
    previous_overdue, current_overdue = _overdue_ids(previous_snapshot), _overdue_ids(current_snapshot)
    changed_progress = [
        activity_id for activity_id in sorted(before.keys() & after.keys())
        if before[activity_id].get('actual_progress') is not None
        and after[activity_id].get('actual_progress') is not None
        and before[activity_id]['actual_progress'] != after[activity_id]['actual_progress']
    ]
    return {
        'previous_snapshot': _summary(previous_snapshot),
        'current_snapshot': _summary(current_snapshot),
        'metrics': {
            'progress_delta': _delta(current, previous, 'progress'),
            'spi_delta': _delta(current, previous, 'spi'),
            'cpi_delta': _delta(current, previous, 'cpi'),
            'overdue_delta': _delta(current, previous, 'overdue'),
        },
        'activities': {
            'added_ids': sorted(after.keys() - before.keys()),
            'removed_ids': sorted(before.keys() - after.keys()),
            'progress_changed_ids': changed_progress,
            'newly_overdue_ids': sorted(current_overdue - previous_overdue),
            'resolved_overdue_ids': sorted(previous_overdue - current_overdue),
        },
        'limitations': [
            'Perbandingan hanya memakai dua snapshot yang dipublikasikan dan ID aktivitas yang sama.',
            'Aktivitas ditambah atau dihapus dapat mencerminkan perubahan cakupan sumber; bukan otomatis perubahan kinerja.',
            'Perbandingan tidak menjelaskan penyebab perubahan atau membuat forecast.',
        ],
    }


def _summary(snapshot):
    return {key: snapshot[key] for key in ('id', 'version', 'as_of', 'filename', 'sheet')}
