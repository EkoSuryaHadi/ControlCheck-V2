"""Local SQLite repository. IDs are opaque; all child lookups include project ID."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


class Repository:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, currency TEXT NOT NULL,
                    as_of TEXT NOT NULL, active_snapshot TEXT);
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    source_id TEXT NOT NULL REFERENCES sources(id), version INTEGER NOT NULL,
                    mapping TEXT NOT NULL, payload TEXT NOT NULL,
                    UNIQUE(project_id, version));
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    snapshot_id TEXT NOT NULL REFERENCES snapshots(id), payload TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id),
                    job_type TEXT NOT NULL, status TEXT NOT NULL, stage TEXT NOT NULL,
                    progress_percent INTEGER NOT NULL, error_message TEXT,
                    result_payload TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL);
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def projects(self):
        with self.connection() as db:
            return [dict(r) for r in db.execute('SELECT * FROM projects ORDER BY rowid DESC')]

    def project(self, project_id):
        with self.connection() as db:
            row = db.execute('SELECT * FROM projects WHERE id=?', (project_id,)).fetchone()
            return dict(row) if row else None

    def create_project(self, name, currency, as_of):
        project_id = str(uuid4())
        with self.connection() as db:
            db.execute('INSERT INTO projects(id,name,currency,as_of) VALUES (?,?,?,?)', (project_id,name,currency,as_of))
        return self.project(project_id)

    def add_source(self, project_id, table):
        source = {**table, 'id':str(uuid4()), 'project_id':project_id}
        with self.connection() as db:
            db.execute('INSERT INTO sources VALUES (?,?,?)', (source['id'],project_id,json.dumps(source)))
        return source

    def source(self, project_id, source_id):
        with self.connection() as db:
            row = db.execute('SELECT payload FROM sources WHERE id=? AND project_id=?',(source_id,project_id)).fetchone()
            return json.loads(row['payload']) if row else None

    def sources(self, project_id):
        with self.connection() as db:
            return [json.loads(r['payload']) for r in db.execute('SELECT payload FROM sources WHERE project_id=? ORDER BY rowid DESC',(project_id,))]

    def active_snapshot(self, project_id):
        with self.connection() as db:
            row = db.execute('''SELECT s.payload FROM snapshots s JOIN projects p
                ON p.id=s.project_id AND p.active_snapshot=s.id WHERE p.id=?''',(project_id,)).fetchone()
            return json.loads(row['payload']) if row else None

    def save_conversation(self, project_id, snapshot_id, question, response):
        entry = dict(id=str(uuid4()), project_id=project_id, snapshot_id=snapshot_id, question=question, response=response)
        with self.connection() as db:
            db.execute('INSERT INTO conversations VALUES (?,?,?,?)', (entry['id'], project_id, snapshot_id, json.dumps(entry)))
        return entry

    def conversations(self, project_id):
        with self.connection() as db:
            return [json.loads(row['payload']) for row in db.execute('SELECT payload FROM conversations WHERE project_id=? ORDER BY rowid ASC', (project_id,))]

    def snapshots(self, project_id):
        with self.connection() as db:
            rows = db.execute('SELECT payload FROM snapshots WHERE project_id=? ORDER BY version DESC', (project_id,))
            return [json.loads(row['payload']) for row in rows]

    def previous_snapshot(self, project_id, snapshot_id):
        snapshots = self.snapshots(project_id)
        for index, item in enumerate(snapshots):
            if item['id'] == snapshot_id:
                return snapshots[index + 1] if index + 1 < len(snapshots) else None
        return None

    def publish(self, project, source, mapping, rows, as_of=None):
        canonical_mapping = json.dumps(mapping, sort_keys=True)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT id,payload FROM snapshots WHERE project_id=? AND source_id=? AND mapping=?',
                                  (project['id'],source['id'],canonical_mapping)).fetchall()
            previous = next((row for row in existing if json.loads(row['payload'])['as_of'] == (as_of or project['as_of'])), None)
            if previous:
                # Re-select only the same source, mapping, and reporting date.
                db.execute('UPDATE projects SET active_snapshot=? WHERE id=?',(previous['id'],project['id']))
                return json.loads(previous['payload'])
            version = db.execute('SELECT COALESCE(MAX(version),0)+1 FROM snapshots WHERE project_id=?',(project['id'],)).fetchone()[0]
            snapshot = dict(id=str(uuid4()), project_id=project['id'], source_id=source['id'],
                            version=version, semantic_version='activity-snapshot/v1',
                            as_of=as_of or project['as_of'], currency=project['currency'], filename=source['filename'],
                            sheet=source['sheet'], sha256=source['sha256'], rows=rows)
            db.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?)',
                       (snapshot['id'],project['id'],source['id'],version,canonical_mapping,json.dumps(snapshot)))
            db.execute('UPDATE projects SET active_snapshot=? WHERE id=?',(snapshot['id'],project['id']))
            return snapshot

    def publish_reconciliation(self, project, schedule_source, sources, mappings, rows, as_of=None):
        """Persist an activity snapshot produced from Schedule plus optional inputs."""
        canonical_mapping = json.dumps(mappings, sort_keys=True)
        source_ids = [source['id'] for source in sources]
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            existing = db.execute('SELECT id,payload FROM snapshots WHERE project_id=? AND source_id=? AND mapping=?',
                                  (project['id'], schedule_source['id'], canonical_mapping)).fetchall()
            previous = next((row for row in existing if json.loads(row['payload'])['as_of'] == (as_of or project['as_of'])), None)
            if previous:
                db.execute('UPDATE projects SET active_snapshot=? WHERE id=?', (previous['id'], project['id']))
                return json.loads(previous['payload'])
            version = db.execute('SELECT COALESCE(MAX(version),0)+1 FROM snapshots WHERE project_id=?',
                                 (project['id'],)).fetchone()[0]
            snapshot = dict(
                id=str(uuid4()), project_id=project['id'], source_id=schedule_source['id'],
                source_ids=source_ids, version=version, semantic_version='activity-snapshot/v2',
                as_of=as_of or project['as_of'], currency=project['currency'], filename=schedule_source['filename'],
                sheet=schedule_source['sheet'], sha256=schedule_source['sha256'], rows=rows,
            )
            db.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?)',
                       (snapshot['id'], project['id'], schedule_source['id'], version,
                        canonical_mapping, json.dumps(snapshot)))
            db.execute('UPDATE projects SET active_snapshot=? WHERE id=?', (snapshot['id'], project['id']))
            return snapshot

    def create_job(self, project_id: str, job_type: str = 'ingest_sources') -> dict:
        now = datetime.now(timezone.utc).isoformat()
        job_id = str(uuid4())
        record = dict(
            id=job_id,
            project_id=project_id,
            job_type=job_type,
            status='queued',
            stage='queued',
            progress_percent=0,
            error_message=None,
            result_payload=None,
            created_at=now,
            updated_at=now,
        )
        with self.connection() as db:
            db.execute(
                '''INSERT INTO jobs (id, project_id, job_type, status, stage, progress_percent,
                   error_message, result_payload, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)''',
                (job_id, project_id, job_type, 'queued', 'queued', 0, None, None, now, now)
            )
        return record

    def update_job(self, job_id: str, status: str, stage: str, progress_percent: int,
                   error_message: str | None = None, result_payload: dict | None = None) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        res_json = json.dumps(result_payload) if result_payload is not None else None
        with self.connection() as db:
            db.execute(
                '''UPDATE jobs SET status=?, stage=?, progress_percent=?,
                   error_message=COALESCE(?, error_message),
                   result_payload=COALESCE(?, result_payload),
                   updated_at=? WHERE id=?''',
                (status, stage, progress_percent, error_message, res_json, now, job_id)
            )
            row = db.execute('SELECT * FROM jobs WHERE id=?', (job_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            if data.get('result_payload'):
                data['result_payload'] = json.loads(data['result_payload'])
            return data

    def job(self, project_id: str, job_id: str) -> dict | None:
        with self.connection() as db:
            row = db.execute('SELECT * FROM jobs WHERE id=? AND project_id=?', (job_id, project_id)).fetchone()
            if not row:
                return None
            data = dict(row)
            if data.get('result_payload'):
                data['result_payload'] = json.loads(data['result_payload'])
            return data

    def jobs(self, project_id: str) -> list[dict]:
        with self.connection() as db:
            rows = db.execute('SELECT * FROM jobs WHERE project_id=? ORDER BY created_at DESC', (project_id,)).fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if item.get('result_payload'):
                    item['result_payload'] = json.loads(item['result_payload'])
                results.append(item)
            return results

