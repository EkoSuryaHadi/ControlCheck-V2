"""Local SQLite repository. IDs are opaque; all child lookups include project ID."""
import json
import sqlite3
from contextlib import contextmanager
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

    def publish(self, project, source, mapping, rows):
        canonical_mapping = json.dumps(mapping, sort_keys=True)
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT id,payload FROM snapshots WHERE project_id=? AND source_id=? AND mapping=?',
                                  (project['id'],source['id'],canonical_mapping)).fetchone()
            if previous:
                # Re-select the existing snapshot when the user deliberately republishes it.
                db.execute('UPDATE projects SET active_snapshot=? WHERE id=?',(previous['id'],project['id']))
                return json.loads(previous['payload'])
            version = db.execute('SELECT COALESCE(MAX(version),0)+1 FROM snapshots WHERE project_id=?',(project['id'],)).fetchone()[0]
            snapshot = dict(id=str(uuid4()), project_id=project['id'], source_id=source['id'],
                            version=version, semantic_version='activity-snapshot/v1',
                            as_of=project['as_of'], currency=project['currency'], filename=source['filename'],
                            sheet=source['sheet'], sha256=source['sha256'], rows=rows)
            db.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?)',
                       (snapshot['id'],project['id'],source['id'],version,canonical_mapping,json.dumps(snapshot)))
            db.execute('UPDATE projects SET active_snapshot=? WHERE id=?',(snapshot['id'],project['id']))
            return snapshot

