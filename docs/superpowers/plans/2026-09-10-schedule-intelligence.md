# Schedule Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface critical schedule exposure, overdue milestones, and source-provided slack from MPP/XML schedules.

**Architecture:** The project-file adapter adds optional schedule metadata to normalized task rows. Semantic validation copies safe metadata into the immutable activity snapshot, while analytics emits only rules supported by those facts. React renders the returned metrics and insight cards.

**Tech Stack:** Python, FastAPI, MPXJ, React, TypeScript.

**Spec:** `docs/superpowers/specs/2026-09-10-schedule-intelligence-design.md`

### Task 1: Preserve MPP schedule metadata

**Files:** Modify `apps/api/controlcheck/project_files.py`, `apps/api/controlcheck/semantic.py`; test `tests/test_project_files.py`, `tests/test_domain.py`.

- [ ] Write a failing test proving a non-summary task with `critical=True`, `milestone=True`, and `total_slack=0` retains those fields after normalization and validation.
- [ ] Run `.venv\\Scripts\\python.exe -m pytest tests/test_project_files.py tests/test_domain.py -q` and observe failure.
- [ ] Add optional canonical fields `is_critical`, `is_milestone`, and `total_slack`; map MPP/XML task attributes to them; copy them through validation without relaxing required fields.
- [ ] Run the same tests and observe pass.
- [ ] Commit `feat: preserve MPP schedule intelligence metadata`.

### Task 2: Deterministic schedule intelligence rules

**Files:** Modify `apps/api/controlcheck/analytics.py`; test `tests/test_domain.py`.

- [ ] Write failing tests for a critical overdue activity, an overdue milestone, and a schedule with no metadata that produces no critical claim.
- [ ] Run `.venv\\Scripts\\python.exe -m pytest tests/test_domain.py -q` and observe failure.
- [ ] Add schedule coverage metrics and evidence-backed insight rules; retain the current no-forecast limitation.
- [ ] Run `.venv\\Scripts\\python.exe -m pytest tests/test_domain.py -q` and observe pass.
- [ ] Commit `feat: add deterministic schedule intelligence insights`.

### Task 3: Overview and insight rendering

**Files:** Modify `apps/web/src/types.ts`, `apps/web/src/App.tsx`; test with build.

- [ ] Extend metric types with schedule intelligence coverage/counts.
- [ ] Render a Schedule Intelligence strip and Critical/Milestone badges only when metadata exists.
- [ ] Run `npm.cmd run build` and correct TypeScript errors.
- [ ] Commit `feat: show schedule intelligence in project overview`.

### Task 4: Contracts, docs, and verification

**Files:** Modify `README.md`, `docs/ARCHITECTURE.md`, `packages/contracts/openapi.json`.

- [ ] Update user-facing description and architecture boundaries: source facts are reported; critical path and forecast are not newly calculated.
- [ ] Run `scripts/export_contracts.py`, `.venv\\Scripts\\python.exe -m pytest -q`, and `npm.cmd run build`.
- [ ] Commit `docs: document schedule intelligence boundaries` and push the completed branch to GitHub.
