"""Deterministic project-data intake decisions."""


def classify(headers, mapping):
    targets = {field for field in mapping.values() if field}
    if not {'activity_id', 'name'} <= targets:
        if 'activity_id' not in targets:
            return None
        if targets & {'actual_progress'} and not targets & {'budget', 'actual_cost'}:
            return 'progress'
        if targets & {'budget', 'actual_cost'}:
            return 'cost'
        return None
    if targets & {'actual_progress', 'actual_cost', 'budget'}:
        return 'combined'
    return 'schedule'


def decide_source(table, mapper):
    mapping = {item['column']: item['field'] for item in mapper.suggest(table['headers']) if item['field']}
    dataset_type = classify(table['headers'], mapping)
    decisions = [
        {'step': 'schema_mapping', 'message': 'Agent memetakan kolom dengan alias yang dikenal.'},
        {'step': 'source_type', 'message': ('Jenis data terdeteksi: ' + dataset_type) if dataset_type
         else 'Jenis data belum dapat dipastikan.'},
    ]
    return {'dataset_type': dataset_type, 'mapping': mapping, 'decisions': decisions}
