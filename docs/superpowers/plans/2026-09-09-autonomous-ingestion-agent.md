# Autonomous Ingestion Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users upload project files once and receive an automatically published, traceable project snapshot when the data is valid.

**Architecture:** A new `ingestion.py` application service orchestrates inspection, deterministic source classification, mapping, validation, reconciliation, persistence, and an immutable receipt. The existing detailed source endpoints remain available for advanced correction. MPP/XML are read through a project-file adapter and normalized into the same Schedule source shape as spreadsheet files.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, SQLite, openpyxl, MPXJ Java adapter, React/TypeScript/Vite.

**Spec:** `docs/superpowers/specs/2026-09-09-autonomous-ingestion-agent-design.md`

## Global Constraints

- Publish automatically only after deterministic mapping, validation, and reconciliation pass.
- Keep CSV/XLSX source and reconciliation endpoints working for advanced review.
- Never replace the active snapshot for a failed ingestion.
- Limit uploads to the existing 5 MB, 10,000-row, and 100-column protections.
- Treat MPP as Schedule; preserve task UID and source evidence; exclude summary tasks from activity calculations.
- The MVP does not use an external AI provider or require an API key.

---

### Task 1: Deterministic source classification and decision receipts

**Files:**
- Create: `apps/api/controlcheck/ingestion.py`
- Test: `tests/test_ingestion.py`

**Interfaces:**
- Produces `classify(headers: list[str]) -> str | None`.
- Produces `decide_source(table: dict, mapper: MappingProvider) -> dict` with `dataset_type`, `mapping`, and `decisions`.

- [ ] **Step 1: Write the failing test**

```python
from controlcheck.ingestion import decide_source
from controlcheck.semantic import LocalMappingProvider

def test_agent_classifies_schedule_and_records_mapping_decision():
    result = decide_source({'headers': ['Activity ID', 'Name', 'Planned Finish']}, LocalMappingProvider())
    assert result['dataset_type'] == 'schedule'
    assert result['mapping']['Activity ID'] == 'activity_id'
    assert result['decisions'][0]['step'] == 'schema_mapping'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_ingestion.py::test_agent_classifies_schedule_and_records_mapping_decision -v`

Expected: FAIL because `controlcheck.ingestion` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def decide_source(table, mapper):
    mapping = {item['column']: item['field'] for item in mapper.suggest(table['headers']) if item['field']}
    targets = set(mapping.values())
    dataset_type = 'schedule' if {'activity_id', 'name'} <= targets else None
    return {'dataset_type': dataset_type, 'mapping': mapping,
            'decisions': [{'step': 'schema_mapping', 'message': 'Mapping kolom dibuat otomatis.'}]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_ingestion.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/controlcheck/ingestion.py tests/test_ingestion.py
git commit -m "feat: add deterministic ingestion decisions"
```

### Task 2: Automatic CSV/XLSX ingestion and publication

**Files:**
- Modify: `apps/api/controlcheck/ingestion.py`
- Modify: `apps/api/controlcheck/main.py`
- Test: `tests/test_api.py`

**Interfaces:**
- Produces `run_ingestion(project, files, repository, mapper) -> dict`.
- Adds `POST /api/projects/{pid}/ingestions` with multipart field `files`.

- [ ] **Step 1: Write the failing test**

```python
def test_agent_upload_publishes_valid_schedule_without_mapping(client):
    pid = project(client)
    response = client.post(f'/api/projects/{pid}/ingestions', files=[
        ('files', ('schedule.csv', b'Activity ID,Name\\nA1,Foundation', 'text/csv')),
    ])
    assert response.status_code == 201
    assert response.json()['status'] == 'published'
    assert response.json()['snapshot']['rows'][0]['activity_id'] == 'A1'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_api.py::test_agent_upload_publishes_valid_schedule_without_mapping -v`

Expected: FAIL with HTTP 404.

- [ ] **Step 3: Write minimal implementation**

```python
@app.post('/api/projects/{pid}/ingestions', status_code=201)
async def ingest(pid: str, files: list[UploadFile] = File(...)):
    result = await ingest_files(project(pid), files, app.state.repo, mapper)
    return result
```

`ingest_files` reads sources, derives mappings, validates, persists each accepted source, reconciles them, and calls `publish_reconciliation` only when its error list is empty. Its `needs_attention` result includes `issues`, `sources`, and ordered `decisions`.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_api.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/controlcheck/ingestion.py apps/api/controlcheck/main.py tests/test_api.py
git commit -m "feat: publish valid uploads through ingestion agent"
```

### Task 3: Batch reconciliation and safe failure receipts

**Files:**
- Modify: `apps/api/controlcheck/ingestion.py`
- Test: `tests/test_ingestion.py`
- Test: `tests/test_api.py`

**Interfaces:**
- `run_ingestion` returns `status: 'needs_attention'` with no `snapshot` when validation or cross-source matching fails.

- [ ] **Step 1: Write the failing test**

```python
def test_agent_does_not_publish_unmatched_progress_activity(client):
    pid = project(client)
    response = client.post(f'/api/projects/{pid}/ingestions', files=[
        ('files', ('schedule.csv', b'Activity ID,Name\\nA1,Foundation', 'text/csv')),
        ('files', ('progress.csv', b'Activity ID,Actual Progress\\nB9,55', 'text/csv')),
    ])
    assert response.status_code == 200
    assert response.json()['status'] == 'needs_attention'
    assert client.get(f'/api/projects/{pid}/overview').json()['snapshot'] is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_api.py::test_agent_does_not_publish_unmatched_progress_activity -v`

Expected: FAIL because the current endpoint does not return a receipt.

- [ ] **Step 3: Write minimal implementation**

```python
if checked_errors or reconciliation['errors']:
    return {'status': 'needs_attention', 'summary': 'Agent memerlukan tinjauan data.',
            'sources': receipts, 'issues': checked_errors + reconciliation['errors'],
            'decisions': decisions, 'coverage': reconciliation['coverage']}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_ingestion.py tests/test_api.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/controlcheck/ingestion.py tests/test_ingestion.py tests/test_api.py
git commit -m "feat: return safe ingestion attention receipts"
```

### Task 4: MPP/XML schedule adapter

**Files:**
- Create: `apps/api/controlcheck/project_files.py`
- Modify: `apps/api/controlcheck/importers.py`
- Modify: `requirements.txt`
- Test: `tests/test_project_files.py`

**Interfaces:**
- Produces `read_project_file(filename: str, content: bytes) -> dict` with Schedule headers and rows.
- `read_source` accepts `.mpp` and `.xml` and returns a Schedule table carrying `task_uid` source metadata.

- [ ] **Step 1: Write the failing test**

```python
from controlcheck.project_files import normalize_tasks

def test_normalize_tasks_excludes_summary_rows_and_keeps_task_uid():
    result = normalize_tasks([{'uid': 1, 'name': 'Phase', 'summary': True},
                              {'uid': 2, 'name': 'Foundation', 'summary': False, 'percent_complete': 50}])
    assert [row['Task UID'] for row in result['rows']] == ['2']
    assert result['headers'][:2] == ['Activity ID', 'Name']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_project_files.py::test_normalize_tasks_excludes_summary_rows_and_keeps_task_uid -v`

Expected: FAIL because `project_files` does not exist.

- [ ] **Step 3: Write minimal implementation**

```python
def normalize_tasks(tasks):
    rows = [{'Activity ID': str(task['uid']), 'Task UID': str(task['uid']), 'Name': task['name'],
             'Actual Progress': str(task.get('percent_complete', ''))}
            for task in tasks if not task.get('summary')]
    return {'headers': list(rows[0]), 'rows': rows, 'sheet': 'Microsoft Project'}
```

Add an MPXJ adapter command with a pinned, documented JAR dependency. The adapter writes content to a temporary file, invokes Java with no shell interpolation, parses its JSON output, enforces existing row limits, and translates parser errors into a `ValueError`. XML uses the same adapter. Do not execute formulas or macros.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_project_files.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/controlcheck/project_files.py apps/api/controlcheck/importers.py requirements.txt tests/test_project_files.py
git commit -m "feat: add MPP and project XML schedule adapter"
```

### Task 5: One-step Data Center interface and receipt

**Files:**
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/types.ts`
- Modify: `apps/web/src/styles.css`
- Test: `apps/web/src/App.test.tsx` if the project test harness is introduced

**Interfaces:**
- Adds `IngestionReceipt` type with `status`, `summary`, `sources`, `coverage`, `issues`, `decisions`, and optional `snapshot`.
- The primary Data Center action posts selected files to `/ingestions`.

- [ ] **Step 1: Write the failing test**

```tsx
it('shows an overview action after the agent publishes data', async () => {
  render(<DataCenter receipt={{status: 'published', summary: 'Snapshot siap', sources: [], decisions: [], coverage: {schedule: 1, progress_matched: 0, cost_matched: 0}}} />)
  expect(screen.getByRole('button', {name: 'Buka project overview'})).toBeVisible()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm.cmd test -- App.test.tsx`

Expected: FAIL because the receipt UI does not exist.

- [ ] **Step 3: Write minimal implementation**

Make the primary panel accept multiple `.csv,.xlsx,.mpp,.xml` files and use one action named **Analisis project data**. Render five visible progress steps while posting. Render the receipt after completion; published results offer **Buka project overview**, while attention-needed results offer **Review data** and list concise issues. Keep the manual upload and mapping section inside a collapsed **Advanced data review** panel.

- [ ] **Step 4: Run test and production build**

Run: `npm.cmd run build`

Expected: TypeScript check and Vite production build pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/App.tsx apps/web/src/types.ts apps/web/src/styles.css
git commit -m "feat: add one-step ingestion agent workspace"
```

### Task 6: Contracts, documentation, and verification

**Files:**
- Modify: `README.md`
- Modify: `docs/PRD.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/SCREEN_INVENTORY.md`
- Modify: `packages/contracts/openapi.json`

- [ ] **Step 1: Add the failing HTTP contract assertion**

```python
def test_ingestion_contract_exposes_upload_route(client):
    schema = client.get('/openapi.json').json()
    assert '/api/projects/{pid}/ingestions' in schema['paths']
```

- [ ] **Step 2: Run it to verify it fails before endpoint registration**

Run: `.venv\\Scripts\\python.exe -m pytest tests/test_api.py::test_ingestion_contract_exposes_upload_route -v`

Expected: FAIL until Task 2 endpoint is registered.

- [ ] **Step 3: Generate final contract and update docs**

Run `scripts/export_contracts.py` after endpoint completion. Document direct MPP/XML support, automatic publication conditions, receipt behavior, and advanced review fallback.

- [ ] **Step 4: Run final verification**

Run: `.venv\\Scripts\\python.exe -m pytest -q`

Run: `npm.cmd run build`

Run a browser journey: create project, upload schedule CSV without mapping, verify receipt, open Overview; repeat with a valid MPP fixture when MPXJ is available.

- [ ] **Step 5: Commit**

```bash
git add README.md docs packages/contracts/openapi.json tests/test_api.py
git commit -m "docs: document autonomous project ingestion"
```
