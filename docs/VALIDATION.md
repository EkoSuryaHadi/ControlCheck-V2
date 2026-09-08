# Validation record

Verified 8 September 2026 on Windows, Python 3.11 and Node.js 24.3.0.

## Automated checks

- `.venv/Scripts/python.exe -m pytest tests -q` → **17 passed**, 2 dependency deprecation warnings.
- `npm.cmd run build` → **Vite production build succeeded**; TypeScript emitted no errors.
- `scripts/export_contracts.py` → generated `packages/contracts/openapi.json` successfully.
- `scripts/make_samples.py` → generated the synthetic `data/samples/project-snapshot.xlsx` companion.

## Browser smoke check

The local API started on `127.0.0.1:8000` and Vite on `127.0.0.1:5173`. The empty-project screen rendered with the six workspace sections, local analytics notice, and accessible project form. A project named `Demo — Plant Balikpapan` was created in the browser; Data Center opened and accepted the synthetic XLSX through the browser file chooser. Upload state changed to “Mengunggah dan membaca data…”.

The full request journey is covered in `tests/test_api.py`: create, upload, mapping review, quality validation, publish, overview metrics, assistant answer, report text, idempotent republish, project isolation, restart persistence, invalid XLSX formula rejection and unsupported MPP/XER response.

## Known limitations

Browser testing stopped at the upload request because the temporary browser session expired while the server was still processing. The same upload and publication path is covered by the HTTP journey tests, including XLSX sheet selection and formula rejection. There is no external AI provider in this increment; answers are explicitly labelled local analytics. Use loopback-only development until the production gates in `docs/ARCHITECTURE.md` are implemented.
