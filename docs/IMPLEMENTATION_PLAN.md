# Foundation implementation plan

Goal: a runnable local scaffold implementing the user's approved AI Project Control Assistant direction.
Architecture: React client, modular FastAPI service, SQLite repository and deterministic domain core. Scope: docs/PRD.md. Execution: inline within this task.

## Delivery units
1. Define docs/PRD.md, docs/ARCHITECTURE.md, docs/SCREEN_INVENTORY.md and docs/ROADMAP.md. Specify actual vs planned capability explicitly.
2. Write tests/test_domain.py before the domain implementation. Cover duplicate IDs, impossible dates, progress bounds, zero denominators, missing facts and source evidence.
3. Implement apps/api/controlcheck/{importers,semantic,analytics,assistant,extensions}.py. Importers return SourceTable; mapping returns suggestions; validation returns rows/issues; analytics returns metrics/insights/limitations.
4. Write tests/test_api.py for create→upload→preview→publish→ask→report and cross-project rejection. Implement repository.py and main.py with project-scoped transactional publication.
5. Implement apps/web/src/{App,api,types}.tsx/ts and styles.css. Connect every enabled control to the API; disable publication until validation of the current mapping succeeds. Reset project-specific UI state on project switch.
6. Generate packages/contracts/openapi.json from the app; add synthetic CSV/XLSX samples and local setup instructions.
7. Run backend tests, strict TypeScript compilation, production build and a browser/HTTP smoke check. Record evidence in docs/VALIDATION.md.
8. Copy only the verified new repository into E:/project/ControlCheck-V2, verify file hashes and initialize an independent Git repository. Do not read or modify old application contents.

## Constraints
- Local mode only, no automatic external AI calls or source transmissions.
- Missing data never becomes zero; all numeric claims trace to approved snapshots.
- Full replacement snapshot publication; no implicit merging of multiple uploads.
- Future capabilities use interfaces and documented gates, not simulated forecasts or agent actions.

