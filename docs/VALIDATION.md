# Validation record

Verified 10 September 2026 on Windows, Python 3.11 and Node.js 24.3.0.

## Automated checks

- `.venv/Scripts/python.exe -m pytest tests -q` → **67 passed**, 2 dependency deprecation warnings.
- `npm.cmd run build` → **Vite production build succeeded**; TypeScript emitted no errors.
- `scripts/export_contracts.py` → generated `packages/contracts/openapi.json` successfully.
- `scripts/make_samples.py` → generated the synthetic `data/samples/project-snapshot.xlsx` companion.

## Browser smoke check

The feature API started on `127.0.0.1:8001` and Vite on `127.0.0.1:5174` because the default development ports were already occupied. The empty-project screen rendered with the six workspace sections, local analytics notice and accessible project form. A project named `Uji Import Lokal` was created in a headed Chromium session. Data Center accepted the synthetic XLSX, listed its worksheet, suggested header row 1, displayed the eight-row matrix preview and exposed explicit date, decimal and progress-scale settings. The file then imported with all eight mappings selected, passed quality validation with **0 errors / 0 warnings**, and published into Overview.

The request journey is also covered in `tests/test_api.py`: create, inspect, explicit header/normalization upload, mapping review, quality validation, publish, overview metrics, assistant answer, report text, idempotent republish, project isolation, restart persistence, invalid XLSX formula rejection unsupported MPP/XER response, immutable snapshot history, reporting-date publication, consecutive-period comparison, local comparison answers, Forecast Readiness domain/API/assistant coverage, and controlled Primavera P6 XER adapter/upload coverage.

## Known limitations

The optional SumoPod provider needs an explicit `SUMOPOD_API_KEY`; unavailable or uncited responses fall back to labelled local analytics. Original file bytes are not retained, and locale handling intentionally requires an explicit user choice. Use loopback-only development until the production gates in `docs/ARCHITECTURE.md` are implemented.
