# Primavera P6 XER Import Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Import bounded Primavera P6 XER schedules through the approved ControlCheck ingestion pipeline while preserving P6 activity and source metadata.

**Architecture:** Extend the existing MPXJ-backed project-file adapter so UniversalProjectReader reads XER into a normalized source table. Preserve P6-only metadata as source columns; semantic validation and publication remain unchanged. The client accepts XER in the main agent upload flow.

**Tech Stack:** Python 3.11, FastAPI, MPXJ 16.7.0, JPype1, Java 17, React 19, TypeScript, Vite, pytest.

**Spec:** docs/superpowers/specs/2026-09-10-primavera-xer-import-design.md

## Global Constraints

- Use the existing 5 MB, 10,000-row, and 100-column bounds.
- No critical-path calculation, calendar interpretation, schedule repair, finish-date forecast, or source mutation.
- Preserve Calendar, Constraint Type, Constraint Date, Baseline Start, and Baseline Finish as source metadata only.
- Parser failures must not publish or activate a snapshot.
- Retain source provenance and project isolation.
- Run pytest, frontend production build, and scripts/export_contracts.py before completion.

---

### Task 1: XER normalization contract

**Files:**

- Modify: apps/api/controlcheck/project_files.py
- Modify: tests/test_project_files.py

**Interfaces:**

- Consumes: P6-shaped task dicts.
- Produces: normalize_tasks(tasks) rows whose Activity ID prefers activity_id and whose Predecessor IDs use visible Activity IDs.

- [ ] **Step 1: Write failing unit tests**

~~~python
def test_normalize_tasks_prefers_primavera_activity_id_and_metadata():
    result = normalize_tasks([{
        'uid': 9001, 'activity_id': 'ENG-010', 'name': 'Engineering',
        'calendar': '6D Calendar', 'constraint_type': 'Start On',
        'constraint_date': '2026-10-01', 'baseline_start': '2026-09-01',
        'baseline_finish': '2026-09-10',
    }])
    row = result['rows'][0]
    assert row['Activity ID'] == 'ENG-010'
    assert row['Calendar'] == '6D Calendar'
    assert row['Baseline Finish'] == '2026-09-10'

def test_normalize_tasks_resolves_predecessors_to_activity_ids():
    result = normalize_tasks([
        {'uid': 1, 'activity_id': 'A-100', 'name': 'First'},
        {'uid': 2, 'activity_id': 'B-200', 'name': 'Second', 'predecessor_uids': [1]},
    ])
    assert result['rows'][1]['Predecessor IDs'] == 'A-100'
~~~

- [ ] **Step 2: Run test to verify it fails**

Run: .venv\Scripts\python.exe -m pytest tests\test_project_files.py -q

Expected: FAIL because Activity ID uses UID and P6 metadata columns do not exist.

- [ ] **Step 3: Implement the normalizer**

Add P6 audit headers to HEADERS. Build a UID-to-Activity-ID map before emitting rows. Use activity_id when present, otherwise UID. Convert predecessor_uids through the map; preserve unknown predecessor UID as its opaque string for downstream integrity diagnostics. Retain calendar, constraint, and baseline fields in source rows.

- [ ] **Step 4: Run focused tests**

Run: .venv\Scripts\python.exe -m pytest tests\test_project_files.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~powershell
git add apps/api/controlcheck/project_files.py tests/test_project_files.py
git commit -m "feat: normalize Primavera schedule metadata"
~~~

### Task 2: MPXJ XER adapter and bounded importer routing

**Files:**

- Modify: apps/api/controlcheck/project_files.py
- Modify: apps/api/controlcheck/importers.py
- Modify: tests/test_project_files.py
- Modify: tests/test_api.py

**Interfaces:**

- Consumes: read_project_file(filename: str, content: bytes).
- Produces: a source table with sheet "Primavera P6" for .xer and bounded importer acceptance in inspect_source and read_source.

- [ ] **Step 1: Write failing adapter and route tests**

~~~python
def test_read_project_file_routes_xer_to_mpxj(monkeypatch):
    monkeypatch.setattr('controlcheck.project_files._xer_tasks',
                        lambda content: [{'uid': 1, 'activity_id': 'P6-1', 'name': 'P6 task'}])
    result = read_project_file('schedule.xer', b'%T\\tPROJECT')
    assert result['sheet'] == 'Primavera P6'
    assert result['rows'][0]['Activity ID'] == 'P6-1'

def test_xer_parser_unavailable_has_clear_diagnostic(monkeypatch):
    monkeypatch.setattr('controlcheck.project_files._xer_tasks',
                        lambda content: (_ for _ in ()).throw(ValueError('Parser XER belum tersedia di server.')))
    with pytest.raises(ValueError, match='Parser XER belum tersedia'):
        read_project_file('schedule.xer', b'%T\\tPROJECT')
~~~

Add an API test that posts a .xer file with read_project_file monkeypatched to a valid table and verifies normal source inspection and project-scoped upload.

- [ ] **Step 2: Run tests to verify they fail**

Run: .venv\Scripts\python.exe -m pytest tests\test_project_files.py tests\test_api.py -q

Expected: FAIL because .xer is not routed and _xer_tasks does not exist.

- [ ] **Step 3: Implement MPXJ read and importer routing**

Implement _xer_tasks using the existing temporary-file and UniversalProjectReader pattern. Extract task unique ID, activity ID, baseline/start/finish, percent complete, cost, critical, milestone, slack, calendar, constraint type/date, and predecessor task IDs. Change read_project_file, inspect_source, and read_source extension checks to include .xer. Give XER its explicit sheet label. Translate Java, MPXJ, and parse failures to a ValueError that names XER.

- [ ] **Step 4: Run focused tests**

Run: .venv\Scripts\python.exe -m pytest tests\test_project_files.py tests\test_api.py -q

Expected: PASS.

- [ ] **Step 5: Commit**

~~~powershell
git add apps/api/controlcheck/project_files.py apps/api/controlcheck/importers.py tests/test_project_files.py tests/test_api.py
git commit -m "feat: import Primavera XER schedules"
~~~

### Task 3: Data Center and documentation

**Files:**

- Modify: apps/web/src/App.tsx
- Modify: README.md
- Modify: docs/PRD.md
- Modify: docs/ARCHITECTURE.md
- Modify: docs/SCREEN_INVENTORY.md
- Modify: docs/ROADMAP.md
- Modify: docs/VALIDATION.md
- Modify: packages/contracts/openapi.json

**Interfaces:**

- Consumes: .xer importer support from Task 2.
- Produces: XER file acceptance and accurate supported-format documentation.

- [ ] **Step 1: Update UI file accept and helper copy**

Change the primary agent input accept string to include .xer. State “Primavera P6 XER” beside MPP and Project XML and indicate Java 17 is required for MPP/XER. Do not add an XER-specific publishing path.

- [ ] **Step 2: Update documentation**

Move XER from planned to working. State that source metadata is retained for review but no calendar calculation, constraint analysis, baseline selection, or forecast result is enabled.

- [ ] **Step 3: Export contract and verify**

~~~powershell
.venv\Scripts\python.exe -m pytest tests -q
npm.cmd run build
.venv\Scripts\python.exe scripts\export_contracts.py
git diff --check
~~~

Expected: all commands pass.

- [ ] **Step 4: Commit**

~~~powershell
git add apps/web/src/App.tsx README.md docs/PRD.md docs/ARCHITECTURE.md docs/SCREEN_INVENTORY.md docs/ROADMAP.md docs/VALIDATION.md packages/contracts/openapi.json
git commit -m "docs: record Primavera XER support"
~~~

## Plan self-review

- Task 1 implements Activity ID and metadata preservation.
- Task 2 adds MPXJ reading, diagnostics, bounded routes, and API coverage.
- Task 3 exposes XER to users and updates enabled-versus-planned documentation.
- No task calculates schedule outcomes or makes a forecast claim.


