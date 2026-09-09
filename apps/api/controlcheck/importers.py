"""Bounded source parsing; never evaluate formulas or guess ambiguous units."""
import csv
import hashlib
import io
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Protocol

MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 10_000
MAX_COLUMNS = 100


class Importer(Protocol):
    def read(self, content: bytes, sheet: str | None = None, header_row: int = 1) -> dict: ...


def text_value(value):
    if value is None:
        return ''
    if isinstance(value, (datetime, date)):
        return value.strftime('%Y-%m-%d')
    return str(value).strip()


def _csv_matrix(content: bytes):
    try:
        text = content.decode('utf-8-sig')
    except UnicodeDecodeError as exc:
        raise ValueError('CSV harus menggunakan UTF-8.') from exc
    sample = text[:8192]
    candidates = []
    for delimiter in (',', ';', '\t'):
        counts = [len(row) for row in csv.reader(io.StringIO(sample), delimiter=delimiter) if any(row)]
        if not counts:
            continue
        mode = max(set(counts), key=counts.count)
        candidates.append(((counts.count(mode) if mode > 1 else 0, mode), delimiter))
    delimiter = max(candidates, default=((0, 1), ','))[1]
    try:
        matrix = []
        for row in csv.reader(io.StringIO(text), delimiter=delimiter, strict=True):
            matrix.append(row)
            if len(matrix) > MAX_ROWS + 50:
                raise ValueError('Maksimal 10.000 baris data.')
        return matrix
    except csv.Error as exc:
        raise ValueError('Struktur CSV tidak valid.') from exc


def _xlsx_matrix(content: bytes, sheet: str | None, reject_formulas=False):
    from openpyxl import load_workbook
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            if sum(i.file_size for i in archive.infolist()) > 50 * 1024 * 1024:
                raise ValueError('Workbook terlalu besar setelah diekstrak (maks. 50 MB).')
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
        try:
            if sheet and sheet not in book.sheetnames:
                raise ValueError('Sheet tidak ditemukan. Pilihan: ' + ', '.join(book.sheetnames))
            names = [sheet] if sheet else list(book.sheetnames)
            matrices = {}
            for name in names:
                ws = book[name]
                if (ws.max_row or 0) > MAX_ROWS + 50 or (ws.max_column or 0) > MAX_COLUMNS:
                    raise ValueError('Maksimal 10.000 baris data dan 100 kolom.')
                matrix = []
                for row in ws.iter_rows():
                    if reject_formulas and any(cell.data_type == 'f' for cell in row):
                        raise ValueError('Ubah formula Excel menjadi values sebelum upload.')
                    matrix.append([text_value(cell.value) for cell in row])
                matrices[name] = matrix
            return list(book.sheetnames), matrices
        finally:
            book.close()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Workbook XLSX tidak valid atau tidak dapat dibaca.') from exc


def _suggest_header(matrix):
    for index, row in enumerate(matrix[:25], start=1):
        values = [text_value(value) for value in row if text_value(value)]
        if len(values) >= 2 and len(values) == len(set(values)):
            return index
    return 1


def inspect_source(filename: str, content: bytes) -> dict:
    if not content or len(content) > MAX_BYTES:
        raise ValueError('File kosong atau melebihi batas 5 MB.')
    extension = Path(filename).suffix.lower()
    if extension == '.csv':
        names, matrices = ['CSV'], {'CSV': _csv_matrix(content)}
    elif extension == '.xlsx':
        names, matrices = _xlsx_matrix(content, None)
    elif extension in ('.mpp', '.xml'):
        from .project_files import read_project_file
        table = read_project_file(filename, content)
        names, matrices = [table['sheet']], {table['sheet']: [table['headers'], *[list(row.values()) for row in table['rows']]]}
    else:
        raise ValueError('Format belum didukung. Gunakan .csv atau .xlsx; MPP/XER ada di roadmap.')
    sheets = []
    for name in names:
        matrix = matrices.get(name, [])
        width = min(max((len(row) for row in matrix[:8]), default=0), MAX_COLUMNS)
        preview = [[text_value(row[i]) if i < len(row) else '' for i in range(width)] for row in matrix[:8]]
        sheets.append(dict(name=name, suggested_header_row=_suggest_header(matrix), preview=preview))
    return dict(filename=Path(filename.replace('\\', '/')).name, kind=extension.lstrip('.'), sheets=sheets,
                sha256=hashlib.sha256(content).hexdigest())


def read_source(filename: str, content: bytes, sheet: str | None = None, header_row: int = 1,
                date_format: str = 'iso', decimal_separator: str = 'dot', percent_scale: str = 'points') -> dict:
    if not content or len(content) > MAX_BYTES:
        raise ValueError('File kosong atau melebihi batas 5 MB.')
    extension = Path(filename).suffix.lower()
    sheet_name = 'CSV'
    if extension == '.csv':
        matrix = _csv_matrix(content)
    elif extension == '.xlsx':
        all_names, matrices = _xlsx_matrix(content, sheet, reject_formulas=True)
        sheet_name = sheet or all_names[0]
        matrix = matrices[sheet_name]
    elif extension in ('.mpp', '.xml'):
        from .project_files import read_project_file
        table = read_project_file(filename, content)
        sheet_name, matrix = table['sheet'], [table['headers'], *[[row.get(header, '') for header in table['headers']] for row in table['rows']]]
    else:
        raise ValueError('Format belum didukung. Gunakan .csv atau .xlsx; MPP/XER ada di roadmap.')
    if not matrix or header_row < 1 or header_row > min(len(matrix), 50):
        raise ValueError('Baris header harus berada di antara 1 dan 50 serta tersedia pada sheet.')
    if len(matrix) - header_row > MAX_ROWS:
        raise ValueError('Maksimal 10.000 baris data.')
    headers = [text_value(value) for value in matrix[header_row - 1]]
    if not headers or any(not header for header in headers) or len(set(headers)) != len(headers):
        raise ValueError('Setiap header harus terisi dan unik.')
    if len(headers) > MAX_COLUMNS:
        raise ValueError('Maksimal 100 kolom.')
    rows = []
    for number, row in enumerate(matrix[header_row:], start=header_row + 1):
        if len(row) != len(headers):
            raise ValueError(f'Baris {number}: jumlah kolom berbeda dari header.')
        rows.append(dict(zip(headers, map(text_value, row))) | {'__source_row__': number})
    if not rows:
        raise ValueError('Tidak ada baris data.')
    return dict(filename=Path(filename.replace('\\', '/')).name, sheet=sheet_name, header_row=header_row,
                normalization=dict(date_format=date_format, decimal_separator=decimal_separator,
                                   percent_scale=percent_scale),
                headers=headers, rows=rows, sha256=hashlib.sha256(content).hexdigest())
