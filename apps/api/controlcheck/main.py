import os
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, field_validator
from .repository import Repository
from .importers import MAX_BYTES, inspect_source, read_source
from .semantic import FIELDS, LocalMappingProvider, validate
from .analytics import analyze
from .assistant import LocalAssistant, report


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


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=2000)

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
    mapper, assistant = LocalMappingProvider(), LocalAssistant()

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

    def public_source(s):
        preview = [{k: v for k, v in row.items() if k != '__source_row__'} for row in s['rows'][:5]]
        return {k:v for k,v in s.items() if k != 'rows'} | dict(row_count=len(s['rows']), preview=preview, suggestions=mapper.suggest(s['headers']))

    @app.get('/api/health')
    def health():
        return dict(status='ok', version='0.1.0', assistant_mode='local_analytics', mapping_mode='local_aliases')

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
            content = file.file.read(MAX_BYTES + 1)
            return inspect_source(file.filename or '', content)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        finally:
            file.file.close()

    @app.post('/api/projects/{pid}/sources', status_code=201)
    def upload_source(pid: str, file: UploadFile = File(...), sheet: str | None = None,
                      header_row: int = 1, date_format: Literal['iso','dmy','mdy'] = 'iso',
                      decimal_separator: Literal['dot','comma'] = 'dot',
                      percent_scale: Literal['points','fraction'] = 'points',
                      dataset_type: Literal['combined','schedule','progress','cost'] = 'combined'):
        project(pid)
        try:
            content = file.file.read(MAX_BYTES + 1)
            table = read_source(file.filename or '', content, sheet, header_row, date_format,
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
        return app.state.repo.publish(project(pid),s,body.mapping,checked['rows'])

    @app.get('/api/projects/{pid}/overview')
    def overview(pid: str):
        p = project(pid)
        s = app.state.repo.active_snapshot(pid)
        return dict(project=p, snapshot=s, analysis=analyze(s['rows'],s['as_of']) if s else None)

    @app.post('/api/projects/{pid}/assistant')
    def ask(pid: str, body: Question):
        return assistant.answer(body.question,snapshot(pid))

    @app.get('/api/projects/{pid}/report', response_class=PlainTextResponse)
    def export_report(pid: str):
        text = report(project(pid),snapshot(pid))
        return PlainTextResponse(text, headers={'Content-Disposition':'attachment; filename="controlcheck-report.md"'})

    return app


app = create_app()
