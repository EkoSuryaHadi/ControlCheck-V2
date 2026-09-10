# Forecast Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Assess whether approved snapshot evidence is sufficient to begin a later schedule forecast, without calculating a forecast.

**Architecture:** A pure forecast readiness module evaluates the active snapshot, immutable snapshot history, and deterministic schedule analysis. FastAPI exposes the result as an endpoint and inside Overview. The web client renders a read-only readiness card; assistants receive the same bounded object.

**Tech Stack:** Python 3.11, FastAPI, SQLite, React 19, TypeScript, Vite, pytest.

**Spec:** docs/superpowers/specs/2026-09-10-forecast-readiness-design.md

## Global Constraints

- Never return a finish date, delay probability, recovery duration, root cause, critical path, or numeric forecast.
- Evaluate only the active project snapshot and that project's retained publication history.
- Treat unknown facts as missing; do not coerce them to zero.
- Preserve snapshot provenance and project scope.
- Uploaded text remains untrusted evidence and is never executable instructions.
- Run pytest, production frontend build, and scripts/export_contracts.py before completion.

---

### Task 1: Pure forecast readiness assessment

**Files:**

- Create: apps/api/controlcheck/forecast_readiness.py
- Create: tests/test_forecast_readiness.py

**Interfaces:**

- Consumes: snapshot dict, history list of dict, and analysis dict returned by analytics.analyze.
- Produces: assess_forecast_readiness(snapshot: dict, history: list[dict], analysis: dict) -> dict.

- [ ] **Step 1: Write the failing tests**

~~~python
from controlcheck.analytics import analyze
from controlcheck.forecast_readiness import assess_forecast_readiness

def test_ready_when_history_schedule_and_network_are_complete(ready_snapshot, ready_history):
    result = assess_forecast_readiness(ready_snapshot, ready_history,
                                      analyze(ready_snapshot['rows'], ready_snapshot['as_of']))
    assert result['status'] == 'ready_for_method'
    assert result['blockers'] == []
    assert result['reporting_dates'] == ['2026-09-08', '2026-09-15']

def test_missing_history_blocks_readiness(snapshot):
    result = assess_forecast_readiness(snapshot, [snapshot], analyze(snapshot['rows'], snapshot['as_of']))
    assert result['status'] == 'not_ready'
    assert any(check['id'] == 'history' and check['status'] == 'missing' for check in result['checks'])

def test_cycle_and_external_dependency_block_readiness(snapshot_with_bad_network, history):
    result = assess_forecast_readiness(snapshot_with_bad_network, history,
                                      analyze(snapshot_with_bad_network['rows'], snapshot_with_bad_network['as_of']))
    assert {'dependency_cycle', 'external_dependency'} <= {
        check['id'] for check in result['checks'] if check['status'] == 'blocked'
    }
~~~

- [ ] **Step 2: Run test to verify it fails**

Run: .venv\Scripts\python.exe -m pytest tests\test_forecast_readiness.py -q

Expected: FAIL because module controlcheck.forecast_readiness does not exist.

- [ ] **Step 3: Write minimal implementation**

~~~python
def assess_forecast_readiness(snapshot, history, analysis):
    metrics = analysis['metrics']
    rows = snapshot['rows']
    dates = sorted({item['as_of'] for item in history})
    checks = [
        _history_check(dates),
        _coverage_check('schedule_dates', rows, ('planned_start', 'planned_finish', 'actual_progress')),
        _dependency_coverage_check(metrics, len(rows)),
        _network_checks(metrics),
        _remaining_work_check(rows),
    ]
    blockers = [item['detail'] for item in checks if item['status'] in ('missing', 'blocked')]
    return {
        'status': 'needs_attention' if any(item['status'] == 'blocked' for item in checks)
                  else 'not_ready' if blockers else 'ready_for_method',
        'snapshot_id': snapshot['id'], 'snapshot_version': snapshot['version'],
        'reporting_dates': dates, 'checks': checks, 'blockers': blockers,
        'warnings': _isolated_warning(metrics),
        'limitations': ['Forecast belum dihitung. Hasil ini hanya menilai kelayakan data dan schedule untuk memilih metode forecast.'],
    }
~~~

Implement helpers with exact check IDs: history, schedule_dates, dependency_coverage, dependency_cycle, external_dependency, remaining_work. Use analytics metrics for cycles and external links; use raw rows for required fields and incomplete work.

- [ ] **Step 4: Run focused test to verify it passes**

Run: .venv\Scripts\python.exe -m pytest tests\test_forecast_readiness.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~powershell
git add apps/api/controlcheck/forecast_readiness.py tests/test_forecast_readiness.py
git commit -m "feat: assess forecast readiness"
~~~

### Task 2: Project-scoped API and assistant context

**Files:**

- Modify: apps/api/controlcheck/main.py
- Modify: apps/api/controlcheck/grounded.py
- Modify: apps/api/controlcheck/assistant.py
- Modify: tests/test_api.py
- Modify: tests/test_grounded_ai.py

**Interfaces:**

- Consumes: assess_forecast_readiness from Task 1.
- Produces: GET /api/projects/{pid}/forecast-readiness, overview.forecast_readiness, and assistant context field forecast_readiness.

- [ ] **Step 1: Write failing HTTP and assistant tests**

~~~python
def test_forecast_readiness_requires_published_snapshot(client):
    pid = project(client)
    assert client.get(f'/api/projects/{pid}/forecast-readiness').status_code == 409

def test_overview_embeds_readiness_after_publication(client):
    pid = publish_two_complete_schedule_snapshots(client)
    overview = client.get(f'/api/projects/{pid}/overview').json()
    assert overview['forecast_readiness']['snapshot_id'] == overview['snapshot']['id']

def test_local_assistant_answers_readiness_without_forecast(client):
    pid = publish_two_complete_schedule_snapshots(client)
    answer = client.post(f'/api/projects/{pid}/assistant',
                         json={'question': 'Apakah data siap untuk forecast?'}).json()
    assert 'forecast' in answer['answer'].lower()
    assert 'tanggal selesai' not in answer['answer'].lower()
~~~

In tests/test_grounded_ai.py assert provider context includes forecast_readiness.

- [ ] **Step 2: Run test to verify it fails**

Run: .venv\Scripts\python.exe -m pytest tests\test_api.py tests\test_grounded_ai.py -q

Expected: FAIL because readiness is absent from endpoint, Overview, local answer, and provider context.

- [ ] **Step 3: Implement endpoint and bounded assistant context**

~~~python
def readiness_for(pid, active):
    history = app.state.repo.snapshots(pid)
    analysis = analyze(active['rows'], active['as_of'])
    return assess_forecast_readiness(active, history, analysis)

@app.get('/api/projects/{pid}/forecast-readiness')
def forecast_readiness(pid: str):
    return readiness_for(pid, snapshot(pid))
~~~

Use readiness_for in Overview and ask. Add optional forecast_readiness parameters to GroundedAssistant.answer and LocalAssistant.answer. Include the object in grounded context. A local readiness answer reports status, blockers, and next action only.

- [ ] **Step 4: Run focused tests to verify they pass**

Run: .venv\Scripts\python.exe -m pytest tests\test_api.py tests\test_grounded_ai.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~powershell
git add apps/api/controlcheck/main.py apps/api/controlcheck/grounded.py apps/api/controlcheck/assistant.py tests/test_api.py tests/test_grounded_ai.py
git commit -m "feat: expose forecast readiness"
~~~

### Task 3: Overview presentation and typed contract

**Files:**

- Modify: apps/web/src/types.ts
- Modify: apps/web/src/App.tsx
- Modify: apps/web/src/styles.css
- Modify: packages/contracts/openapi.json

**Interfaces:**

- Consumes: Overview.forecast_readiness and the endpoint from Task 2.
- Produces: ForecastReadiness TypeScript type and read-only ForecastReadinessCard.

- [ ] **Step 1: Write TypeScript contract first**

~~~ts
export type ForecastReadiness = {
  status: 'not_ready' | 'needs_attention' | 'ready_for_method';
  snapshot_id: string;
  snapshot_version: number;
  reporting_dates: string[];
  checks: { id: string; status: 'pass' | 'missing' | 'blocked'; detail: string }[];
  blockers: string[];
  warnings: string[];
  limitations: string[];
};
~~~

Extend Overview with forecast_readiness: ForecastReadiness | null before editing App.tsx.

- [ ] **Step 2: Verify the build fails before UI implementation**

Run: npm.cmd run build

Expected: PASS; the type contract compiles before the UI is added.

- [ ] **Step 3: Implement the card and prompt**

~~~tsx
function ForecastReadinessCard({ readiness }: { readiness: ForecastReadiness }) {
  const label = {
    not_ready: 'Belum siap untuk forecast',
    needs_attention: 'Perlu perbaikan sebelum forecast',
    ready_for_method: 'Siap memilih metode forecast',
  }[readiness.status];
  return <section className="forecast-readiness">{label}</section>;
}
~~~

Render it after ComparisonCard. List all check details, blockers, warnings, and “Forecast belum dihitung”. Add the suggested prompt “Apakah data saya siap untuk forecast?” and responsive styles for each status.

- [ ] **Step 4: Verify production build passes**

Run: npm.cmd run build

Expected: PASS.

- [ ] **Step 5: Export contract and commit**

~~~powershell
.venv\Scripts\python.exe scripts\export_contracts.py
git add apps/web/src/types.ts apps/web/src/App.tsx apps/web/src/styles.css packages/contracts/openapi.json
git commit -m "feat: show forecast readiness"
~~~

### Task 4: Documentation and full verification

**Files:**

- Modify: docs/PRD.md
- Modify: docs/ARCHITECTURE.md
- Modify: docs/SCREEN_INVENTORY.md
- Modify: docs/ROADMAP.md
- Modify: README.md
- Modify: docs/VALIDATION.md

**Interfaces:**

- Consumes: finished readiness gate, endpoint, assistant behavior, and UI from Tasks 1–3.
- Produces: accurate enabled-versus-planned product boundaries and validation record.

- [ ] **Step 1: Update documentation**

State that Forecast Readiness is enabled. Keep forecast ranges, probability, and completion projections in the future forecasting stage. State it is a deterministic gate that does not transmit data or execute actions.

- [ ] **Step 2: Run complete backend verification**

Run: .venv\Scripts\python.exe -m pytest tests -q

Expected: PASS.

- [ ] **Step 3: Run frontend and contract verification**

~~~powershell
npm.cmd run build
.venv\Scripts\python.exe scripts\export_contracts.py
git diff --check
~~~

Expected: all commands exit successfully with no whitespace errors.

- [ ] **Step 4: Commit**

~~~powershell
git add README.md docs/PRD.md docs/ARCHITECTURE.md docs/SCREEN_INVENTORY.md docs/ROADMAP.md docs/VALIDATION.md packages/contracts/openapi.json
git commit -m "docs: record forecast readiness gate"
~~~

## Plan self-review

- Spec coverage: Tasks 1–3 cover status, required inputs, API, Overview, and assistant context. Task 4 preserves roadmap and trust boundaries.
- No placeholder terms remain. Check IDs, interfaces, commands, and expected results are explicit.
- Type consistency: API uses forecast_readiness; Python uses assess_forecast_readiness; TypeScript uses ForecastReadiness; status values match across all tasks.


