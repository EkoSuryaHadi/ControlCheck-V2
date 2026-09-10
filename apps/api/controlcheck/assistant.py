"""Provider seam; the default answers only supported analytic intents."""
from typing import Protocol
from .analytics import analyze


class AssistantProvider(Protocol):
    def answer(self, question: str, snapshot: dict) -> dict: ...


class LocalAssistant:
    def answer(self, question, snapshot):
        result = analyze(snapshot['rows'], snapshot['as_of'])
        m = result['metrics']
        q = question.lower()
        unsupported = ('kenapa', 'mengapa', 'why', 'forecast', 'kemungkinan', 'prediksi', 'penyebab', 'tren')
        references = result['evidence']
        if any(word in q for word in unsupported):
            answer = 'Data belum cukup untuk menjawab pertanyaan ini. Snapshot ini tidak memuat riwayat, dependency network, atau model forecasting yang diperlukan.'
            references = []
        elif any(word in q for word in ('integritas', 'integrity', 'cycle', 'siklus')):
            answer = (f"Dependency cycle: {m['dependency_cycle_count'] if m['dependency_cycle_count'] is not None else 'belum tersedia'}; "
                      f"aktivitas terisolasi: {m['isolated_activities'] if m['isolated_activities'] is not None else 'belum tersedia'}; "
                      f"link di luar snapshot: {m['dependency_external_links'] if m['dependency_external_links'] is not None else 'belum tersedia'}.")
            integrity = [item for item in result['insights'] if item['id'] in ('dependency_cycle', 'isolated_activity')]
            references = [evidence for item in integrity for evidence in item['evidence']]
        elif any(word in q for word in ('critical', 'kritis', 'dependency', 'dependensi', 'dampak')):
            if m['critical_count'] is None:
                answer = 'Status critical belum tersedia dari file schedule, sehingga jalur critical dan dependency tidak dapat dinilai.'
                references = []
            else:
                answer = (f"Aktivitas critical: {m['critical_count']}; critical terlambat: {m['critical_overdue']}. "
                          f"Aktivitas pada jalur dampak: {m['downstream_activities'] if m['downstream_activities'] is not None else 'belum tersedia'}; "
                          f"milestone penerus: {m['downstream_milestones'] if m['downstream_milestones'] is not None else 'belum tersedia'}.")
                issue = next((i for i in result['insights'] if i['id'] == 'dependency_impact'), None)
                references = issue['evidence'] if issue else []
        elif any(word in q for word in ('delay', 'terlambat', 'overdue')):
            issue = next((i for i in result['insights'] if i['id'] == 'overdue'), None)
            answer = f"Aktivitas terlambat: {m['overdue'] if m['overdue'] is not None else 'belum tersedia'}. Cakupan: {m['overdue_coverage']}."
            if issue:
                refs = {e['row'] for e in issue['evidence']}
                names = [r['name'] for r in snapshot['rows'] if r['evidence']['row'] in refs]
                answer += ' Aktivitas: ' + ', '.join(names[:20]) + (f' (dan {len(names)-20} lainnya)' if len(names)>20 else '') + '.'
                references = issue['evidence']
        elif any(word in q for word in ('kondisi', 'summary', 'ringkas', 'progress', 'progres', 'spi', 'cpi', 'cost', 'biaya', 'budget', 'masalah')):
            def fmt(v):
                return f'{v:,.2f}' if v is not None else 'belum tersedia'
            answer = (f"Snapshot {snapshot['as_of']}: {m['activity_count']} aktivitas. "
                      f"Progress {fmt(m['progress'])}{'%' if m['progress'] is not None else ''} (basis: {m['progress_basis']}). "
                      f"SPI {fmt(m['spi'])}; CPI {fmt(m['cpi'])}. "
                      f"BAC {fmt(m['bac'])}; actual cost {fmt(m['ac'])} {snapshot['currency']}. "
                      f"Ada {len(result['insights'])} sinyal yang perlu ditinjau.")
        else:
            answer = 'Mode analitik lokal mendukung ringkasan kondisi, progress, SPI/CPI, biaya, dan aktivitas terlambat. Pertanyaan ini belum didukung; integrasi model AI ada di roadmap.'
            references = []
        return dict(answer=answer, mode='local_analytics', snapshot_id=snapshot['id'], version=snapshot['version'],
                    evidence=references, limitations=result['limitations'])


def report(project, snapshot):
    result = analyze(snapshot['rows'], snapshot['as_of'])
    lines = [f"# {project['name']} — Executive report", '', f"Tanggal data: {snapshot['as_of']}",
             f"Snapshot: {snapshot['id']} · versi {snapshot['version']}", f"Mata uang: {project['currency']}",
             '', 'Mode: analitik lokal; bukan narasi model AI.', '', '## Metrik', '']
    for key, value in result['metrics'].items():
        value = 'Belum tersedia' if value is None else (f'{value:,.2f}' if isinstance(value,float) else str(value))
        lines.append(f'- {key}: {value}')
    lines += ['', '## Insight', '']
    for i in result['insights']:
        lines.extend([f"- {i['title']}. {i['detail']} {i['action']}"])
    if not result['insights']:
        lines.append('Tidak ada aturan insight yang terpicu. Ini bukan jaminan proyek bebas risiko.')
    lines += ['', '## Keterbatasan', *['- '+v for v in result['limitations']], '', '## Sumber',
              f"File: {snapshot['filename']} · sheet: {snapshot['sheet']} · source: {snapshot['source_id']}",
              f"SHA-256: {snapshot['sha256']}",
              'Baris: ' + ', '.join(str(r['evidence']['row']) for r in snapshot['rows'])]
    return '\n'.join(lines)
