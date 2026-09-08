import { useEffect, useState, type FormEvent } from 'react';
import { api, json } from './api';
import type { Project, Overview, Source, Quality, Answer, Evidence, Insight } from './types';

const tabs = ['Overview', 'Data Center', 'AI Assistant', 'Insights', 'Reports', 'Settings'] as const;
type Tab = typeof tabs[number];
const fieldNames = ['activity_id','name','planned_start','planned_finish','planned_progress','actual_progress','budget','actual_cost','weight'];
const number = (v: number | null | undefined, digits=2) => v == null ? '—' : v.toLocaleString('id-ID', {maximumFractionDigits:digits});
const message = (e: unknown) => e instanceof Error ? e.message : 'Terjadi kesalahan. Coba kembali.';

function EvidenceList({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) return <p className="muted">Tidak ada klaim data yang dirujuk.</p>;
  return <details className="evidence"><summary>{evidence.length} referensi baris sumber</summary><ul>{evidence.map((e,i) => <li key={i}>Source {e.source_id} · {e.sheet} · baris {e.row}</li>)}</ul></details>;
}

function InsightItem({ insight }: { insight: Insight }) {
  return <article className="insight"><div><span className={'tag '+insight.severity}>{insight.severity === 'high' ? 'Prioritas tinggi' : 'Perlu ditinjau'}</span><h3>{insight.title}</h3><p>{insight.detail}</p><p className="action-note">{insight.action}</p><EvidenceList evidence={insight.evidence}/></div></article>;
}

export default function App() {
  const [projects,setProjects] = useState<Project[]>([]);
  const [selected,setSelected] = useState('');
  const [creating,setCreating] = useState(false);
  const [loading,setLoading] = useState(true);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const [name,setName] = useState('');
  const [currency,setCurrency] = useState('IDR');
  const [asOf,setAsOf] = useState(new Date().toLocaleDateString('en-CA'));
  async function loadProjects() {
    setLoading(true); setError('');
    try { const list = await api<Project[]>('/projects'); setProjects(list); setSelected(list[0]?.id || ''); }
    catch(e) { setError(message(e)); }
    finally { setLoading(false); }
  }
  useEffect(() => { void loadProjects(); }, []);
  async function create(e: FormEvent) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const p = await api<Project>('/projects', json({name,currency,as_of:asOf}));
      setProjects(list => [p,...list]); setSelected(p.id); setCreating(false); setName('');
    } catch(e) { setError(message(e)); } finally { setBusy(false); }
  }
  const project = projects.find(p => p.id === selected);
  return <div className="app-shell">
    <header className="brandbar"><a className="wordmark" href="#">ControlCheck<span>AI</span></a><span className="edition">PROJECT INTELLIGENCE / 2.0</span><span className="local-status"><i/> Local workspace</span></header>
    {error && <div role="alert" className="error global-error">{error} <button onClick={() => void loadProjects()}>Coba hubungkan kembali</button></div>}
    <div className="projectbar"><label>WORKSPACE<select aria-label="Pilih proyek" value={selected} onChange={e => {setSelected(e.target.value);setCreating(false);}} disabled={!projects.length || busy}>{!projects.length && <option value="">Belum ada proyek</option>}{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label><button className="secondary" onClick={() => setCreating(!creating)} disabled={busy}>{creating ? 'Tutup form' : '+ Proyek baru'}</button></div>
    {(creating || (!loading && !projects.length && !error)) && <section className="create-project"><div><p className="eyebrow">MULAI DARI PROYEK ANDA</p><h1>Satu workspace.<br/>Konteks proyek yang utuh.</h1><p>Satukan data, pahami kondisi, dan tentukan langkah berikutnya.</p></div><form onSubmit={create}><label>Nama proyek<input required maxLength={120} value={name} onChange={e => setName(e.target.value)} placeholder="Contoh: Revitalisasi Plant Balikpapan"/></label><div className="form-row"><label>Mata uang<select value={currency} onChange={e=>setCurrency(e.target.value)}><option>IDR</option><option>USD</option><option>EUR</option><option>SGD</option></select></label><label>Tanggal pelaporan<input type="date" required value={asOf} onChange={e=>setAsOf(e.target.value)}/></label></div><p className="hint">Tanggal ini dipakai untuk menilai aktivitas yang melewati rencana selesai.</p><button disabled={busy || !name.trim()}>{busy ? 'Membuat…' : 'Buat workspace →'}</button></form></section>}
    {loading ? <main className="empty" role="status">Menghubungkan workspace…</main> : project && <Workspace key={project.id} project={project}/>}
    <footer>ControlCheck AI 2.0 <span>Data → Context → Intelligence</span><span>Development scaffold · v0.1</span></footer>
  </div>;
}

function Workspace({project}: {project: Project}) {
  const [tab,setTab] = useState<Tab>('Overview');
  const [overview,setOverview] = useState<Overview|null>(null);
  const [sources,setSources] = useState<Source[]>([]);
  const [source,setSource] = useState<Source|null>(null);
  const [mapping,setMapping] = useState<Record<string,string|null>>({});
  const [quality,setQuality] = useState<Quality|null>(null);
  const [file,setFile] = useState<File|null>(null);
  const [sheet,setSheet] = useState('');
  const [busy,setBusy] = useState('');
  const [loading,setLoading] = useState(true);
  const [error,setError] = useState('');
  const [notice,setNotice] = useState('');
  const [question,setQuestion] = useState('');
  const [answers,setAnswers] = useState<{question:string;response:Answer}[]>([]);
  const [report,setReport] = useState('');
  const base = '/projects/'+project.id;
  async function refresh() {
    const [o,s] = await Promise.all([api<Overview>(base+'/overview'),api<Source[]>(base+'/sources')]);
    setOverview(o); setSources(s);
  }
  useEffect(() => { let alive=true; Promise.all([api<Overview>(base+'/overview'),api<Source[]>(base+'/sources')]).then(([o,s])=>{if(alive){setOverview(o);setSources(s);}}).catch(e=>{if(alive)setError(message(e));}).finally(()=>{if(alive)setLoading(false);}); return()=>{alive=false;}; }, [base]);
  async function run(label: string, action: ()=>Promise<void>) {
    setBusy(label); setError(''); setNotice('');
    try { await action(); } catch(e) { setError(message(e)); } finally { setBusy(''); }
  }
  function selectSource(s: Source) { setSource(s); setMapping(Object.fromEntries(s.suggestions.map(m=>[m.column,m.field]))); setQuality(null); }
  async function upload(e: FormEvent) {
    e.preventDefault(); if (!file) return;
    await run('Mengunggah dan membaca data…',async()=>{
      const form=new FormData(); form.append('file',file);
      const s=await api<Source>(base+'/sources'+(sheet ? '?sheet='+encodeURIComponent(sheet) : ''),{method:'POST',body:form});
      selectSource(s); await refresh(); setNotice('Sumber berhasil dibaca. Tinjau mapping sebelum publikasi.');
    });
  }
  async function check() { if(source) await run('Memeriksa kualitas…',async()=>setQuality(await api<Quality>(base+'/sources/'+source.id+'/validate',json({mapping})))); }
  async function publish() { if(source) await run('Menerbitkan snapshot…',async()=>{
    await api(base+'/sources/'+source.id+'/publish',json({mapping})); await refresh(); setAnswers([]);setReport('');
    setNotice('Snapshot dipublikasikan. Analitik menggunakan data yang baru disetujui.'); setTab('Overview');
  }); }
  async function ask(q=question) { if (!q.trim()) return; await run('Menganalisis snapshot…',async()=>{
    const response=await api<Answer>(base+'/assistant',json({question:q})); setAnswers(old=>[...old,{question:q,response}]); setQuestion('');
  }); }
  async function previewReport() { await run('Menyiapkan laporan…',async()=>{
    const response=await fetch('/api'+base+'/report'); if(!response.ok) throw new Error('Laporan belum tersedia. Publikasikan data terlebih dahulu.'); setReport(await response.text());
  }); }
  function downloadReport() { const url=URL.createObjectURL(new Blob([report],{type:'text/markdown;charset=utf-8'})); const link=document.createElement('a');link.href=url;link.download='controlcheck-report.md';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000); }
  const snapshot=overview?.snapshot, analysis=overview?.analysis, metrics=analysis?.metrics;
  const empty=<section className="empty-state"><span className="step-number">01 / DATA FIRST</span><h2>Intelligence dimulai<br/>dari data proyek Anda.</h2><p>Upload schedule, progress, dan biaya dalam satu snapshot Excel atau CSV. Setiap jawaban akan memiliki sumber yang bisa ditelusuri.</p><button onClick={()=>setTab('Data Center')}>Upload data pertama →</button><div className="journey"><span>Upload</span><b>→</b><span>Tinjau mapping</span><b>→</b><span>Validasi</span><b>→</b><span>Insight</span></div></section>;
  return <div className="workspace"><aside><p className="eyebrow">PROJECT WORKSPACE</p><nav aria-label="Navigasi proyek">{tabs.map((name,i)=><button key={name} className={tab===name?'active':''} aria-current={tab===name?'page':undefined} onClick={()=>{setTab(name);setError('');}}><span className="nav-number">0{i+1}</span>{name}{name==='Insights' && !!analysis?.insights.length && <em>{analysis.insights.length}</em>}</button>)}</nav><div className="sidebar-note"><span className="tag">ANALITIK LOKAL</span><p>Jawaban bersumber dari snapshot yang Anda setujui.</p><small>Integrasi model AI disiapkan untuk tahap berikutnya.</small></div></aside>
    <main><div className="page-heading"><div><p className="eyebrow">{project.name} / {project.currency}</p><h1>{tab === 'Overview' ? 'Your project, in focus.' : tab}</h1></div><div className="snapshot-label">Tanggal data <strong>{snapshot?.as_of || project.as_of}</strong>{snapshot ? <span>Snapshot v{snapshot.version}</span> : <span>Belum dipublikasikan</span>}</div></div>
      <div aria-live="polite">{busy && <p role="status" className="notice">{busy}</p>}{notice && <p className="notice">{notice}</p>}</div>{error && <p role="alert" className="error">{error}</p>}
      {loading ? <p role="status">Memuat data proyek…</p> : <>
      {tab==='Overview' && (!snapshot || !metrics ? empty : <>
        <div className="section-line"><span className="tag">PUBLISHED SNAPSHOT</span><span>{snapshot.filename} · {snapshot.sheet}</span><button className="text-button" onClick={()=>setTab('Data Center')}>Kelola data ↗</button></div>
        <section className="metrics" aria-label="Metrik proyek"><div><span>Progress aktual</span><strong>{number(metrics.progress)}{metrics.progress != null && <small>%</small>}</strong><small>Basis: {metrics.progress_basis}</small></div><div><span>Schedule performance</span><strong>{number(metrics.spi)}</strong><small>SPI · EV / PV</small></div><div><span>Cost performance</span><strong>{number(metrics.cpi)}</strong><small>CPI · EV / AC</small></div><div><span>Aktivitas terlambat</span><strong>{number(metrics.overdue,0)}</strong><small>Cakupan {metrics.overdue_coverage}</small></div></section>
        <div className="overview-grid"><section><div className="section-title"><h2>Perlu perhatian</h2><span>{analysis?.insights.length} sinyal</span></div>{analysis?.insights.length ? analysis.insights.slice(0,2).map(i=><InsightItem key={i.id} insight={i}/>) : <p className="muted">Tidak ada aturan yang terpicu. Tinjau kualitas dan cakupan data sebelum menyimpulkan kondisi proyek.</p>}<button className="text-button" onClick={()=>setTab('Insights')}>Lihat seluruh insight →</button></section><section className="assistant-invite"><span className="eyebrow">PROJECT INTELLIGENCE ASSISTANT</span><h2>Ubah angka<br/>menjadi pemahaman.</h2><p>Tanyakan kondisi proyek, progress, biaya, atau pekerjaan yang melewati rencana selesai.</p><button onClick={()=>setTab('AI Assistant')}>Tanya assistant ↗</button><small>Mode analitik lokal · berbasis sumber</small></section></div>
        <section className="budget-strip"><h2>Cost snapshot <small>{project.currency}</small></h2><dl><div><dt>Budget at completion</dt><dd>{number(metrics.bac)}</dd></div><div><dt>Planned value</dt><dd>{number(metrics.pv)}</dd></div><div><dt>Earned value</dt><dd>{number(metrics.ev)}</dd></div><div><dt>Actual cost</dt><dd>{number(metrics.ac)}</dd></div></dl></section>
        <section><div className="section-title"><h2>Activity register</h2><span>{snapshot.rows.length} aktivitas</span></div><div className="table-wrap"><table><thead><tr><th>ID</th><th>Aktivitas</th><th>Rencana selesai</th><th>Aktual</th><th>Sumber</th></tr></thead><tbody>{snapshot.rows.slice(0,100).map(r=><tr key={r.activity_id}><td>{r.activity_id}</td><td>{r.name}</td><td>{r.planned_finish || '—'}</td><td>{number(r.actual_progress)}{r.actual_progress != null ? '%' : ''}</td><td>{r.evidence.sheet}:{r.evidence.row}</td></tr>)}</tbody></table></div>{snapshot.rows.length>100 && <p className="hint">Menampilkan 100 dari {snapshot.rows.length} aktivitas. Perhitungan menggunakan seluruh snapshot.</p>}</section><details className="limitations"><summary>Cakupan dan keterbatasan analisis</summary>{analysis?.limitations.map(l=><p key={l}>{l}</p>)}<EvidenceList evidence={analysis?.evidence || []}/></details>
      </>)}
      {tab==='Data Center' && <>
        <p className="lead">Bangun konteks proyek dari sumber yang Anda percaya.</p><form className="upload-area" onSubmit={upload}><div><span className="step-number">01 / UPLOAD SOURCE</span><h2>Excel atau CSV,<br/>siap untuk dipahami.</h2><p>Data tetap menjadi draft sampai mapping dan kualitas disetujui.</p></div><div className="upload-controls"><label>File data<input type="file" accept=".csv,.xlsx" required onChange={e=>setFile(e.target.files?.[0] || null)} disabled={!!busy}/></label><label>Nama sheet Excel <span className="muted">(opsional)</span><input placeholder="Kosongkan untuk sheet pertama" value={sheet} onChange={e=>setSheet(e.target.value)} disabled={!!busy}/></label><button disabled={!file || !!busy}>Baca data →</button><small>5 MB · 10.000 baris · CSV UTF-8 / XLSX</small></div></form>
        <p className="hint">Satu baris = satu aktivitas. Tanggal YYYY-MM-DD, progress 0–100, biaya tanpa pemisah ribuan. Ubah formula Excel menjadi values. Publikasi mengganti snapshot aktif; file tidak digabung otomatis.</p>
        {sources.length>0 && <label className="source-picker">Sumber yang diunggah<select value={source?.id || ''} onChange={e=>{const s=sources.find(s=>s.id===e.target.value);if(s)selectSource(s);}} disabled={!!busy}><option value="" disabled>Pilih sumber untuk ditinjau</option>{sources.map(s=><option key={s.id} value={s.id}>{s.filename} · {s.sheet} · {s.row_count} baris · {s.id.slice(0,8)}</option>)}</select></label>}
        {source && <section><div className="section-title"><h2>02 / Tinjau schema mapping</h2><span className="tag">SARAN ALIAS LOKAL</span></div><p className="muted">{source.filename} · {source.sheet} · {source.row_count} baris</p><div className="table-wrap"><table><thead><tr><th>Kolom sumber</th><th>Field proyek</th><th>Saran awal</th></tr></thead><tbody>{source.suggestions.map(s=><tr key={s.column}><td>{s.column}</td><td><select aria-label={'Mapping '+s.column} disabled={!!busy} value={mapping[s.column] || ''} onChange={e=>{setMapping(old=>({...old,[s.column]:e.target.value || null}));setQuality(null);}}><option value="">Abaikan</option>{fieldNames.map(f=><option key={f} value={f}>{f}</option>)}</select></td><td><span>{Math.round(s.confidence*100)}% alias match</span><small className="block">{s.reason}</small></td></tr>)}</tbody></table></div>
        <details className="source-preview"><summary>Preview sumber · {Math.min(5,source.row_count)} baris pertama</summary><div className="table-wrap"><table><thead><tr>{source.headers.map(h=><th key={h}>{h}</th>)}</tr></thead><tbody>{source.preview.map((r,i)=><tr key={i}>{source.headers.map(h=><td key={h}>{r[h] || '—'}</td>)}</tr>)}</tbody></table></div><p className="hint">Source {source.id} · SHA-256 {source.sha256}</p></details>
        <div className="button-row"><button className="secondary" onClick={()=>void check()} disabled={!!busy}>Periksa kualitas</button><button onClick={()=>void publish()} disabled={!!busy || !quality || quality.errors.length>0}>Publikasikan snapshot →</button></div>
        {quality && <section className="quality"><h3>03 / Data quality · {quality.errors.length} error · {quality.warnings.length} peringatan</h3>{quality.errors.length===0 && <p>Validasi wajib lolos. Tinjau peringatan sebelum publikasi.</p>}{[...quality.errors,...quality.warnings].slice(0,100).map((q,i)=><p key={i} className={i<quality.errors.length?'quality-error':'muted'}>Baris {q.row} · {q.field}: {q.message}</p>)}{quality.errors.length+quality.warnings.length>100 && <p>Menampilkan 100 temuan pertama.</p>}</section>}</section>}
      </>}
      {tab==='AI Assistant' && (!snapshot ? empty : <section className="chat"><div className="chat-intro"><span className="tag">ANALITIK LOKAL · SNAPSHOT v{snapshot.version}</span><h2>Apa yang ingin Anda<br/>pahami tentang proyek ini?</h2><p>Jawaban memakai perhitungan dan sumber yang telah dipublikasikan. Model AI eksternal belum terhubung.</p></div><div className="prompts">{['Bagaimana kondisi proyek saya?','Aktivitas apa yang terlambat?','Ringkas progress dan biaya proyek.'].map(q=><button key={q} className="secondary" disabled={!!busy} onClick={()=>void ask(q)}>{q} ↗</button>)}</div><div className="conversation" aria-live="polite">{answers.map((a,i)=><article key={i}><p className="user-question">{a.question}</p><div className="answer"><span className="eyebrow">CONTROLCHECK / ANALITIK LOKAL</span><p>{a.response.answer}</p><EvidenceList evidence={a.response.evidence}/><details><summary>Keterbatasan jawaban</summary>{a.response.limitations.map(l=><p key={l}>{l}</p>)}</details></div></article>)}</div><form className="composer" onSubmit={e=>{e.preventDefault();void ask();}}><label htmlFor="question">Pertanyaan proyek</label><textarea id="question" value={question} onChange={e=>setQuestion(e.target.value)} placeholder="Tanyakan progress, biaya, atau keterlambatan…" maxLength={2000} required/><button disabled={!!busy || !question.trim()}>Analisis pertanyaan →</button></form><p className="hint">Percakapan hanya tersimpan selama sesi workspace ini. Forecast, critical path, dan alasan perubahan membutuhkan data tambahan.</p></section>)}
      {tab==='Insights' && (!snapshot ? empty : <><p className="lead">Sinyal yang dapat ditelusuri. Langkah berikutnya yang bisa ditinjau.</p>{analysis?.insights.length ? analysis.insights.map(i=><InsightItem key={i.id} insight={i}/>) : <p className="empty">Tidak ada aturan insight yang terpicu. Ini bukan jaminan proyek bebas risiko.</p>}<div className="limitations">{analysis?.limitations.map(l=><p key={l}>{l}</p>)}</div></>)}
      {tab==='Reports' && (!snapshot ? empty : <section><p className="lead">Satu laporan, satu versi data yang disepakati.</p><div className="report-cover"><span className="eyebrow">EXECUTIVE PROJECT REPORT</span><h2>{project.name}</h2><p>{snapshot.as_of} · Snapshot v{snapshot.version} · {project.currency}</p><p>Ringkasan metrik, insight, keterbatasan, dan referensi sumber.</p><div className="button-row"><button onClick={()=>void previewReport()} disabled={!!busy}>Siapkan preview</button><button className="secondary" onClick={downloadReport} disabled={!report || !!busy}>Unduh Markdown ↓</button></div></div>{report && <pre className="report-preview">{report}</pre>}<p className="hint">Format PDF dan template laporan lanjutan ada di roadmap. Narasi saat ini dihasilkan dari aturan analitik lokal.</p></section>)}
      {tab==='Settings' && <section><p className="lead">Fondasi yang transparan untuk pengembangan berikutnya.</p><dl className="settings"><div><dt>Nama proyek</dt><dd>{project.name}</dd></div><div><dt>Project ID</dt><dd>{project.id}</dd></div><div><dt>Mata uang / tanggal data</dt><dd>{project.currency} / {project.as_of}</dd></div><div><dt>Assistant</dt><dd>Analitik lokal — provider AI belum terhubung</dd></div><div><dt>Schema mapping</dt><dd>Alias kolom + konfirmasi manual</dd></div><div><dt>Format aktif</dt><dd>CSV, XLSX</dd></div><div><dt>Fondasi lanjutan</dt><dd>MPP/XER · Forecasting · Agent action proposals</dd></div><div><dt>Penyimpanan</dt><dd>SQLite lokal · snapshot terpisah per proyek</dd></div></dl><p className="hint">Metadata read-only pada scaffold ini. Untuk tanggal pelaporan lain, buat workspace baru sampai versioned reporting periods tersedia. Autentikasi multiuser dan pengaturan provider belum diaktifkan.</p></section>}
      </>}
    </main>
  </div>;
}
