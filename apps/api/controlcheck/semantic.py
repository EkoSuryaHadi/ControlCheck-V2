"""Canonical activity model v1 and explicit quality gates."""
import math
import re
from datetime import datetime
from typing import Protocol

FIELDS = {
    'activity_id': ['activity id', 'id aktivitas', 'kode aktivitas', 'task id'],
    'name': ['activity name', 'nama aktivitas', 'task name', 'nama pekerjaan', 'name'],
    'planned_start': ['planned start', 'baseline start', 'rencana mulai'],
    'planned_finish': ['planned finish', 'baseline finish', 'rencana selesai'],
    'planned_progress': ['planned progress', 'rencana progress', 'plan progress'],
    'actual_progress': ['actual progress', 'progress aktual', 'actual percent complete'],
    'budget': ['budget', 'bac', 'anggaran'],
    'actual_cost': ['actual cost', 'ac', 'biaya aktual'],
    'weight': ['weight', 'bobot'],
}

REQUIRED_FIELDS = {
    'combined': {'activity_id', 'name'},
    'schedule': {'activity_id', 'name'},
    'progress': {'activity_id'},
    'cost': {'activity_id'},
}


class MappingProvider(Protocol):
    def suggest(self, headers: list[str]) -> list[dict]: ...


def normalized(text):
    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()


def suggest_mapping(headers):
    suggestions = []
    used = set()
    for header in headers:
        field = next((f for f, aliases in FIELDS.items()
                      if normalized(header) in [normalized(f), *aliases] and f not in used), None)
        if field:
            used.add(field)
        suggestions.append(dict(column=header, field=field, confidence=1.0 if field else 0.0,
                                reason='Alias dikenal; konfirmasi diperlukan.' if field else 'Pilih manual atau abaikan.'))
    return suggestions


def validate(raw_rows, mapping, source_id, sheet, options=None, dataset_type='combined'):
    options = options or {'date_format':'iso', 'decimal_separator':'dot', 'percent_scale':'points'}
    errors, warnings, rows = [], [], []
    required = REQUIRED_FIELDS.get(dataset_type)

    def parse_date(value):
        formats = {'iso':'%Y-%m-%d', 'dmy':'%d/%m/%Y', 'mdy':'%m/%d/%Y'}
        return datetime.strptime(value, formats[options.get('date_format', 'iso')]).date().isoformat()

    def parse_number(value, field):
        if options.get('decimal_separator', 'dot') == 'comma':
            if '.' in value:
                raise ValueError()
            value = value.replace(',', '.')
        elif ',' in value:
            raise ValueError()
        result = float(value)
        if field.endswith('progress') and options.get('percent_scale', 'points') == 'fraction':
            result *= 100
        return result

    def issue(collection, row, field, code, message):
        collection.append(dict(row=row, field=field, code=code, message=message))

    if required is None:
        issue(errors, 1, 'dataset_type', 'invalid_dataset_type', 'Jenis data tidak dikenal.')
        return dict(rows=[], errors=errors, warnings=warnings)
    targets = [v for v in mapping.values() if v]
    if any(v not in FIELDS for v in targets) or len(targets) != len(set(targets)):
        issue(errors, 1, 'mapping', 'invalid_mapping', 'Field tujuan harus dikenal dan tidak berulang.')
    if raw_rows and any(k not in raw_rows[0] for k in mapping):
        issue(errors, 1, 'mapping', 'unknown_column', 'Kolom sumber tidak ditemukan.')
    if not required <= set(targets):
        issue(errors, 1, 'mapping', 'required_mapping',
              'Petakan ' + ' dan '.join(sorted(required)) + ' terlebih dahulu.')
    if errors:
        return dict(rows=[], errors=errors, warnings=warnings)
    seen = set()
    for fallback_number, raw in enumerate(raw_rows, 2):
        number = int(raw.get('__source_row__', fallback_number))
        item = {f: None for f in FIELDS}
        for column, field in mapping.items():
            if not field:
                continue
            value = str(raw.get(column, '')).strip()
            if not value:
                continue
            if field in ('activity_id', 'name'):
                item[field] = value
            elif field in ('planned_start', 'planned_finish'):
                try:
                    item[field] = parse_date(value)
                except ValueError:
                    issue(errors, number, field, 'invalid_date', 'Gunakan tanggal YYYY-MM-DD yang valid.')
            else:
                try:
                    val = parse_number(value, field)
                    if not math.isfinite(val) or val < 0 or (field == 'weight' and val <= 0):
                        raise ValueError()
                    if field.endswith('progress') and val > 100:
                        raise ValueError()
                    item[field] = val
                except ValueError:
                    issue(errors, number, field, 'invalid_number', 'Angka tidak valid; progress 0–100, biaya ≥ 0, bobot > 0.')
        for field in required:
            if not item[field]:
                issue(errors, number, field, 'required', 'Nilai wajib belum diisi.')
        if item['activity_id'] in seen:
            issue(errors, number, 'activity_id', 'duplicate_id', 'ID aktivitas berulang dalam snapshot.')
        seen.add(item['activity_id'])
        if item['planned_start'] and item['planned_finish'] and item['planned_start'] > item['planned_finish']:
            issue(errors, number, 'planned_finish', 'date_order', 'Tanggal selesai mendahului tanggal mulai.')
        missing = [f for f in ('planned_finish', 'planned_progress', 'actual_progress', 'budget', 'actual_cost') if item[f] is None]
        if missing:
            issue(warnings, number, ', '.join(missing), 'missing_optional', 'Data belum lengkap; sebagian analitik tidak tersedia.')
        item['evidence'] = dict(source_id=source_id, sheet=sheet, row=number)
        rows.append(item)
    if any(r['weight'] is not None for r in rows) and not all(r['weight'] is not None for r in rows):
        issue(warnings, 1, 'weight', 'partial_weights', 'Bobot hanya terisi sebagian; progress agregat tidak tersedia.')
    return dict(rows=rows, errors=errors, warnings=warnings)


class LocalMappingProvider:
    def suggest(self, headers):
        return suggest_mapping(headers)
