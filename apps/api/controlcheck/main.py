import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, File, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator
from .repository import Repository
from .importers import inspect_source, max_upload_bytes, read_source
from .semantic import FIELDS, LocalMappingProvider, validate
from .analytics import analyze
from .comparison import compare_snapshots
from .forecast_readiness import assess_forecast_readiness
from .assistant import report
from .grounded import GroundedAssistant, MODELS, SumoPodGateway, SumoPodMappingProvider
from .reconciliation import reconcile
from .ingestion import run_ingestion


class NewProject(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    currency: str = Field(default='IDR', pattern=r'^[A-Z]{3}$')
    as_of: date

    @field_validator('name')
    @classmethod
    def trim_name(cls, value):
        if not value.strip():
            raise ValueError('Nama proyek wajib diisi.')
        return value.strip()


class MappingInput(BaseModel):
    mapping: dict[str, str | None]
    as_of: date | None = None


class ReconciliationInput(BaseModel):
    schedule_source_id: str
    schedule_mapping: dict[str, str | None]
    progress_source_id: str | None = None
    progress_mapping: dict[str, str | None] = {}
    cost_source_id: str | None = None
    cost_mapping: dict[str, str | None] = {}
    as_of: date | None = None


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    model: str | None = None

    @field_validator('question')
    @classmethod
    def trim_question(cls, value):
        if not value.strip():
            raise ValueError('Pertanyaan wajib diisi.')
        return value.strip()


def create_app(db_path=None):
    path = db_path or os.getenv('CONTROLCHECK_DB') or Path(__file__).resolve().parents[3] / 'data/local/controlcheck.db'

    @asynccontextmanager
    async def lifespan(app):
        app.state.repo = Repository(path)
        yield

    app = FastAPI(title='ControlCheck AI 2.0', version='0.1.0', lifespan=lifespan,
                  description='Local development API. No authentication; bind only to loopback.')
    app.add_middleware(CORSMiddleware, allow_origins=['http://127.0.0.1:5173','http://localhost:5173'],
                       allow_methods=['GET','POST'], allow_headers=['Content-Type'])
    gateway = SumoPodGateway()
    mapper = SumoPodMappingProvider(gateway) if gateway.enabled else LocalMappingProvider()
    assistant = GroundedAssistant(gateway) if gateway.enabled else None

    def project(pid):
        found = app.state.repo.project(pid)
        if not found:
            raise HTTPException(404, 'Proyek tidak ditemukan.')
        return found

    def source(pid, sid):
        project(pid)
        found = app.state.repo.source(pid,sid)
        if not found:
            raise HTTPException(404, 'Sumber tidak ditemukan pada proyek ini.')
        return found

    def snapshot(pid):
        project(pid)
        found = app.state.repo.active_snapshot(pid)
        if not found:
            raise HTTPException(409, 'Publikasikan data yang valid terlebih dahulu.')
        return found

    def readiness_for(pid, active):
        history = app.state.repo.snapshots(pid)
        analysis = analyze(active['rows'], active['as_of'])
        return assess_forecast_readiness(active, history, analysis)

    def public_source(s):
        preview = [{k: v for k, v in row.items() if k != '__source_row__'} for row in s['rows'][:5]]
        return {k:v for k,v in s.items() if k != 'rows'} | dict(row_count=len(s['rows']), preview=preview, suggestions=mapper.suggest(s['headers']))

    @app.get('/api/health')
    def health():
        return dict(status='ok', version='0.1.0', assistant_mode='sumopod_grounded' if gateway.enabled else 'local_analytics', mapping_mode='sumopod_suggestions' if gateway.enabled else 'local_aliases')

    @app.get('/api/ai/models')
    def ai_models():
        return dict(enabled=gateway.enabled, default_model=gateway.model, models=list(MODELS))

    @app.get('/api/fields')
    def fields():
        return list(FIELDS)

    @app.get('/api/projects')
    def list_projects():
        return app.state.repo.projects()

    @app.post('/api/projects', status_code=201)
    def create_project(body: NewProject):
        return app.state.repo.create_project(body.name, body.currency, body.as_of.isoformat())

    @app.get('/api/projects/{pid}/sources')
    def list_sources(pid: str):
        project(pid)
        return [public_source(s) for s in app.state.repo.sources(pid)]

    @app.post('/api/projects/{pid}/sources/inspect')
    def inspect_upload(pid: str, file: UploadFile = File(...)):
        project(pid)
        try:
            filename = file.filename or ''
            content = file.file.read(max_upload_bytes(filename) + 1)
            return inspect_source(filename, content)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            file.file.close()

    @app.post('/api/projects/{pid}/ingestions', status_code=201)
    async def ingest_sources(pid: str, response: Response, as_of: date | None = None, files: list[UploadFile] = File(...)):
        current_project = project(pid)
        if as_of:
            current_project = {**current_project, 'as_of': as_of.isoformat()}
        uploads = []
        try:
            for file in files:
                filename = file.filename or ''
                uploads.append((filename, await file.read(max_upload_bytes(filename) + 1)))
            result = run_ingestion(current_project, uploads, app.state.repo, mapper)
            if result['status'] == 'needs_attention':
                response.status_code = 200
            return result
        finally:
            for file in files:
                await file.close()

    @app.post('/api/projects/{pid}/sources', status_code=201)
    def upload_source(pid: str, file: UploadFile = File(...), sheet: str | None = None,
                      header_row: int = 1, date_format: Literal['iso','dmy','mdy'] = 'iso',
                      decimal_separator: Literal['dot','comma'] = 'dot',
                      percent_scale: Literal['points','fraction'] = 'points',
                      dataset_type: Literal['combined','schedule','progress','cost'] = 'combined'):
        project(pid)
        try:
            filename = file.filename or ''
            content = file.file.read(max_upload_bytes(filename) + 1)
            table = read_source(filename, content, sheet, header_row, date_format,
                                decimal_separator, percent_scale)
            table['dataset_type'] = dataset_type
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            file.file.close()
        return public_source(app.state.repo.add_source(pid,table))

    @app.post('/api/projects/{pid}/sources/{sid}/validate')
    def validate_source(pid: str, sid: str, body: MappingInput):
        s = source(pid,sid)
        checked = validate(s['rows'],body.mapping,sid,s['sheet'],s.get('normalization'),s.get('dataset_type', 'combined'))
        return dict(errors=checked['errors'], warnings=checked['warnings'], row_count=len(checked['rows']))

    @app.post('/api/projects/{pid}/sources/{sid}/publish')
    def publish_source(pid: str, sid: str, body: MappingInput):
        s = source(pid,sid)
        checked = validate(s['rows'],body.mapping,sid,s['sheet'],s.get('normalization'),s.get('dataset_type', 'combined'))
        if checked['errors']:
            raise HTTPException(422, dict(message='Data belum lolos validasi.', errors=checked['errors']))
        return app.state.repo.publish(project(pid),s,body.mapping,checked['rows'], body.as_of.isoformat() if body.as_of else None)

    def prepared_reconciliation(pid: str, body: ReconciliationInput):
        def checked(source_id, mapping, expected_type):
            if source_id is None:
                return None
            item = source(pid, source_id)
            if item.get('dataset_type', 'combined') not in (expected_type, 'combined'):
                raise HTTPException(422, f'Sumber harus bertipe {expected_type}.')
            result = validate(item['rows'], mapping, source_id, item['sheet'],
                              item.get('normalization'), item.get('dataset_type', 'combined'))
            if result['errors']:
                raise HTTPException(422, dict(message='Sumber belum lolos validasi.', errors=result['errors']))
            return {**item, 'rows': result['rows']}
        schedule = checked(body.schedule_source_id, body.schedule_mapping, 'schedule')
        progress = checked(body.progress_source_id, body.progress_mapping, 'progress')
        cost = checked(body.cost_source_id, body.cost_mapping, 'cost')
        return schedule, progress, cost, reconcile(schedule, progress, cost)

    @app.post('/api/projects/{pid}/reconciliations')
    def preview_reconciliation(pid: str, body: ReconciliationInput):
        _, _, _, result = prepared_reconciliation(pid, body)
        return result

    @app.post('/api/projects/{pid}/reconciliations/publish')
    def publish_reconciliation(pid: str, body: ReconciliationInput):
        schedule, progress, cost, result = prepared_reconciliation(pid, body)
        if result['errors']:
            raise HTTPException(422, dict(message='Data antar-sumber belum selaras.', errors=result['errors']))
        mappings = dict(schedule=body.schedule_mapping, progress=body.progress_mapping if progress else None,
                        cost=body.cost_mapping if cost else None)
        return app.state.repo.publish_reconciliation(project(pid), schedule,
                                                     [item for item in (schedule, progress, cost) if item],
                                                     mappings, result['rows'], body.as_of.isoformat() if body.as_of else None)

    @app.get('/api/projects/{pid}/overview')
    def overview(pid: str):
        p = project(pid)
        s = app.state.repo.active_snapshot(pid)
        history = [dict(id=item['id'], version=item['version'], as_of=item['as_of'], filename=item['filename'], sheet=item['sheet']) for item in app.state.repo.snapshots(pid)]
        previous = app.state.repo.previous_snapshot(pid, s['id']) if s else None
        return dict(project=p, snapshot=s, analysis=analyze(s['rows'],s['as_of']) if s else None,
                    history=history, comparison=compare_snapshots(previous, s) if s else None,
                    forecast_readiness=readiness_for(pid, s) if s else None)

    @app.post('/api/projects/{pid}/assistant')
    def ask(pid: str, body: Question):
        active = snapshot(pid)
        if body.model and body.model not in MODELS:
            raise HTTPException(422, 'Model tidak didukung.')
        previous = app.state.repo.previous_snapshot(pid, active['id'])
        comparison = compare_snapshots(previous, active)
        forecast_readiness = readiness_for(pid, active)
        response = (assistant.answer(body.question, active, body.model, comparison, forecast_readiness) if assistant
                    else __import__('controlcheck.assistant', fromlist=['LocalAssistant']).LocalAssistant().answer(body.question, active, comparison, forecast_readiness))
        app.state.repo.save_conversation(pid, active['id'], body.question, response)
        return response

    @app.get('/api/projects/{pid}/comparison')
    def comparison(pid: str):
        active = snapshot(pid)
        return compare_snapshots(app.state.repo.previous_snapshot(pid, active['id']), active)

    @app.get('/api/projects/{pid}/forecast-readiness')
    def forecast_readiness(pid: str):
        return readiness_for(pid, snapshot(pid))

    @app.get('/api/projects/{pid}/conversations')
    def conversations(pid: str):
        project(pid)
        return app.state.repo.conversations(pid)

    @app.get('/api/projects/{pid}/report', response_class=PlainTextResponse)
    def export_report(pid: str):
        text = report(project(pid),snapshot(pid))
        return PlainTextResponse(text, headers={'Content-Disposition':'attachment; filename="controlcheck-report.md"'})

    return app


app = create_app()
