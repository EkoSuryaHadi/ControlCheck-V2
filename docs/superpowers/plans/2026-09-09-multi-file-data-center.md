# Multi-File Data Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile separate Schedule, Progress and Cost sources into one publishable activity snapshot.

**Architecture:** Sources retain their current import, normalization and mapping flow, with a dataset type. A pure reconciliation module joins validated sources with Schedule as master. FastAPI previews and recomputes the merge during atomic publication; Data Center exposes typed uploads, coverage and blocking conflicts.

**Tech Stack:** Python 3.11, FastAPI, SQLite, React, TypeScript, Vite, pytest.

**Spec:** `docs/superpowers/specs/2026-09-09-multi-file-data-center-design.md`

## Global Constraints

- Support only CSV/XLSX with existing 5 MB, 10,000-row and 100-column limits.
- Schedule is required and is the sole master activity register.
- Each source has at most one row per `activity_id`; unmatched or duplicate IDs block publication.
- Missing Progress or Cost stays unknown and appears as a coverage gap.
- Retain source ID, sheet and physical row for every copied field.
- Do not add transaction aggregation, historical periods, MPP/XER or external AI.

---

### Task 1: Typed source validation

**Files:**
- Modify: `apps/api/controlcheck/semantic.py`
- Modify: `apps/api/controlcheck/main.py`
- Test: `tests/test_domain.py`
- Test: `tests/test_api.py`

**Interfaces:** `validate(raw_rows, mapping, source_id, sheet, options=None, dataset_type='combined')` returns canonical rows. Upload accepts and stores `dataset_type`.

- [ ] **Step 1: Write the failing test**

```python
def test_progress_requires_activity_id_but_not_name():
    rows = [{'Activity ID': 'A-1', 'Actual Progress': '55', '__source_row__': 2}]
    result = validate(rows, {'Activity ID': 'activity_id', 'Actual Progress': 'actual_progress'},
                      'progress-1', 'Progress', dataset_type='progress')
    assert result['errors'] == []
    assert result['rows'][0]['name'] is None
```

- [ ] **Step 2: Verify RED**

Run: `.venv/Scripts/python.exe -m pytest tests/test_domain.py::test_progress_requires_activity_id_but_not_name -v`

Expected: FAIL because `validate` does not accept `dataset_type`.

- [ ] **Step 3: Implement the minimum contract**

```python
REQUIRED_FIELDS = {
    'combined': {'activity_id', 'name'},
    'schedule': {'activity_id', 'name'},
    'progress': {'activity_id'},
    'cost': {'activity_id'},
}
```

Use `REQUIRED_FIELDS[dataset_type]` instead of always requiring name. Accept `dataset_type: Literal['combined', 'schedule', 'progress', 'cost'] = 'combined'` on upload and pass the stored value on validation.

- [ ] **Step 4: Verify GREEN and commit**

Run: `.venv/Scripts/python.exe -m pytest tests/test_domain.py tests/test_api.py -q`

```powershell
git add apps/api/controlcheck/semantic.py apps/api/controlcheck/main.py tests/test_domain.py tests/test_api.py
git commit -m "feat: add typed dataset validation"
```

### Task 2: Pure reconciliation module

**Files:**
- Create: `apps/api/controlcheck/reconciliation.py`
- Create: `tests/test_reconciliation.py`

**Interfaces:** `reconcile(schedule, progress=None, cost=None) -> {'rows': list[dict], 'errors': list[dict], 'coverage': dict, 'source_ids': list[str]}`.

- [ ] **Step 1: Write the failing happy-path test**

```python
def test_reconcile_merges_sources_and_preserves_field_evidence():
    result = reconcile(schedule_source(), progress_source(), cost_source())
    row = result['rows'][0]
    assert row['actual_progress'] == 55
    assert row['actual_cost'] == 500
    assert row['field_evidence']['actual_progress']['source_id'] == 'progress-1'
    assert result['coverage'] == {'schedule': 2, 'progress_matched': 1, 'cost_matched': 1}
    assert result['errors'] == []
```

- [ ] **Step 2: Verify RED**

Run: `.venv/Scripts/python.exe -m pytest tests/test_reconciliation.py::test_reconcile_merges_sources_and_preserves_field_evidence -v`

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `reconcile`**

```python
def reconcile(schedule, progress=None, cost=None):
    # Index each validated source by activity_id.
    # Emit duplicate_id and unmatched_activity errors.
    # Start with Schedule rows; overlay actual_progress, budget and actual_cost.
    # Keep schedule evidence and store source evidence in field_evidence.
    return {'rows': rows, 'errors': errors, 'coverage': coverage, 'source_ids': source_ids}
```

- [ ] **Step 4: Add conflict test, verify GREEN and commit**

```python
def test_reconcile_blocks_duplicate_and_unmatched_ids():
    result = reconcile(schedule_source(), progress_source(rows=['A-1', 'A-1', 'MISSING']))
    assert {issue['code'] for issue in result['errors']} == {'duplicate_id', 'unmatched_activity'}
```

Run: `.venv/Scripts/python.exe -m pytest tests/test_reconciliation.py -v`

```powershell
git add apps/api/controlcheck/reconciliation.py tests/test_reconciliation.py
git commit -m "feat: reconcile schedule progress and cost sources"
```

### Task 3: Reconciliation API and atomic publication

**Files:**
- Modify: `apps/api/controlcheck/main.py`
- Modify: `apps/api/controlcheck/repository.py`
- Modify: `tests/test_api.py`
- Modify: `packages/contracts/openapi.json`

**Interfaces:** `POST /api/projects/{pid}/reconciliations` previews a reconciliation. `POST /api/projects/{pid}/reconciliations/publish` repeats it inside the write transaction.

- [ ] **Step 1: Write the failing HTTP journey**

```python
def test_three_source_reconciliation_preview_and_publish(client):
    pid = project(client)
    schedule = upload(client, pid, schedule_csv, dataset_type='schedule')
    progress = upload(client, pid, progress_csv, dataset_type='progress')
    cost = upload(client, pid, cost_csv, dataset_type='cost')
    body = reconciliation_body(schedule, progress, cost)
    assert client.post(f'/api/projects/{pid}/reconciliations', json=body).json()['errors'] == []
    snapshot = client.post(f'/api/projects/{pid}/reconciliations/publish', json=body).json()
    assert snapshot['source_ids'] == [schedule['id'], progress['id'], cost['id']]
```

- [ ] **Step 2: Verify RED**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api.py::test_three_source_reconciliation_preview_and_publish -v`

Expected: FAIL with HTTP 404.

- [ ] **Step 3: Add endpoints and persistence**

```python
class ReconciliationInput(BaseModel):
    schedule_source_id: str
    schedule_mapping: dict[str, str | None]
    progress_source_id: str | None = None
    progress_mapping: dict[str, str | None] = {}
    cost_source_id: str | None = None
    cost_mapping: dict[str, str | None] = {}
```

Store `source_ids` in snapshot payload; retain the Schedule source ID as the existing `source_id` database foreign key. Reject foreign-project source IDs and do not update `active_snapshot` when reconciliation errors exist.

- [ ] **Step 4: Verify GREEN, export contract and commit**

Run: `.venv/Scripts/python.exe -m pytest tests/test_api.py -q`

Run: `.venv/Scripts/python.exe scripts/export_contracts.py`

```powershell
git add apps/api/controlcheck/main.py apps/api/controlcheck/repository.py tests/test_api.py packages/contracts/openapi.json
git commit -m "feat: add reconciliation preview and publication"
```

### Task 4: Data Center reconciliation UI

**Files:**
- Modify: `apps/web/src/types.ts`
- Modify: `apps/web/src/App.tsx`
- Modify: `apps/web/src/styles.css`

**Interfaces:** `DatasetType = 'combined' | 'schedule' | 'progress' | 'cost'`; reconciliation UI calls the Task 3 endpoints.

- [ ] **Step 1: Add types and UI state**

```ts
export type DatasetType = 'combined' | 'schedule' | 'progress' | 'cost';
export type Reconciliation = {
  rows: Record<string, unknown>[];
  errors: { code: string; dataset: string; activity_id?: string; message: string }[];
  coverage: { schedule: number; progress_matched: number; cost_matched: number };
  source_ids: string[];
};
```

- [ ] **Step 2: Implement Data Center controls**

Add a `Jenis data` upload selector, filter source pickers by dataset type, request a preview when three source choices change, and render coverage, issue messages and a merged-row preview. Disable combined publish only after preserving its existing path; enable multi-source publish only with a no-error reconciliation.

- [ ] **Step 3: Build and commit**

Run: `npm.cmd run build`

```powershell
git add apps/web/src/types.ts apps/web/src/App.tsx apps/web/src/styles.css
git commit -m "feat: add multi-source reconciliation workspace"
```

### Task 5: Samples, documentation and verification

**Files:**
- Create: `data/samples/schedule.csv`
- Create: `data/samples/progress.csv`
- Create: `data/samples/cost.csv`
- Modify: `README.md`, `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/SCREEN_INVENTORY.md`, `docs/ROADMAP.md`, `docs/VALIDATION.md`

- [ ] **Step 1: Add synthetic samples**

```csv
Activity ID,Name,Planned Start,Planned Finish,Planned Progress,Budget
ENG-001,Engineering deliverables,2026-06-01,2026-08-15,100,150000000
```

Add matching Progress and Cost samples plus one Schedule-only activity to demonstrate non-blocking coverage gaps.

- [ ] **Step 2: Document the three-file workflow**

Update the walkthrough with upload order, Schedule-master behavior, blocking duplicate/unmatched IDs, field precedence, coverage gaps and one-row-per-activity scope.

- [ ] **Step 3: Run complete verification and commit**

Run: `.venv/Scripts/python.exe -m pytest`

Run: `npm.cmd run build`

Run: `.venv/Scripts/python.exe scripts/export_contracts.py`

Perform a browser journey: create project, upload/validate Schedule, Progress and Cost, preview reconciliation, publish, inspect Overview and Insights.

```powershell
git add README.md docs data/samples packages/contracts/openapi.json
git commit -m "docs: document multi-file ingestion journey"
```
