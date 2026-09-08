"""Bounded source parsing; never evaluate formulas or coerce ambiguous units."""
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
    def read(self, content: bytes, sheet: str | None = None) -> dict: ...


def text_value(value):
    if value is None:
        return ''
    if isinstance(value, (datetime, date)):
        return value.strftime('%Y-%m-%d')
    return str(value).strip()


def read_source(filename: str, content: bytes, sheet: str | None = None) -> dict:
    if not content or len(content) > MAX_BYTES:
        raise ValueError('File kosong atau melebihi batas 5 MB.')
    extension = Path(filename).suffix.lower()
    sheet_name = 'CSV'
    if extension == '.csv':
        try:
            text = content.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            raise ValueError('CSV harus menggunakan UTF-8.') from exc
        try:
            delimiter = csv.Sniffer().sniff(text[:8192], delimiters=',;\t').delimiter
        except csv.Error:
            delimiter = ','
        try:
            matrix = []
            for row in csv.reader(io.StringIO(text), delimiter=delimiter, strict=True):
                matrix.append(row)
                if len(matrix) > MAX_ROWS + 1:
                    raise ValueError('Maksimal 10.000 baris data.')
        except csv.Error as exc:
            raise ValueError('Struktur CSV tidak valid.') from exc
    elif extension == '.xlsx':
        from openpyxl import load_workbook
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if sum(i.file_size for i in archive.infolist()) > 50 * 1024 * 1024:
                    raise ValueError('Workbook terlalu besar setelah diekstrak (maks. 50 MB).')
            book = load_workbook(io.BytesIO(content), read_only=True, data_only=False)
            try:
                if sheet and sheet not in book.sheetnames:
                    raise ValueError('Sheet tidak ditemukan. Pilihan: ' + ', '.join(book.sheetnames))
                ws = book[sheet] if sheet else book.worksheets[0]
                sheet_name = ws.title
                if (ws.max_row or 0) > MAX_ROWS + 1 or (ws.max_column or 0) > MAX_COLUMNS:
                    raise ValueError('Maksimal 10.000 baris data dan 100 kolom.')
                matrix = []
                for row in ws.iter_rows():
                    if any(cell.data_type == 'f' for cell in row):
                        raise ValueError('Ubah formula Excel menjadi values sebelum upload.')
                    matrix.append([text_value(cell.value) for cell in row])
                    if len(matrix) > MAX_ROWS + 1:
                        raise ValueError('Maksimal 10.000 baris data.')
            finally:
                book.close()
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError('Workbook XLSX tidak valid atau tidak dapat dibaca.') from exc
    else:
        raise ValueError('Format belum didukung. Gunakan .csv atau .xlsx; MPP/XER ada di roadmap.')
    if not matrix:
        raise ValueError('Tidak ada header atau data.')
    headers = [text_value(h) for h in matrix[0]]
    if not headers or any(not h for h in headers) or len(set(headers)) != len(headers):
        raise ValueError('Setiap header harus terisi dan unik.')
    if len(headers) > MAX_COLUMNS:
        raise ValueError('Maksimal 100 kolom.')
    rows = []
    for number, row in enumerate(matrix[1:], start=2):
        if len(row) != len(headers):
            raise ValueError(f'Baris {number}: jumlah kolom berbeda dari header.')
        # Keep blank physical rows so provenance row numbers stay exact.
        rows.append(dict(zip(headers, map(text_value, row))))
    if not rows:
        raise ValueError('Tidak ada baris data.')
    return dict(filename=Path(filename.replace('\\', '/')).name, sheet=sheet_name,
                headers=headers, rows=rows, sha256=hashlib.sha256(content).hexdigest())
