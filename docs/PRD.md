# ControlCheck AI 2.0 — Product Requirements

Status: approved direction from the user's brief, 8 September 2026. Delivery: development scaffold, not a production release.

## Product promise
Upload project data. Ask questions. Get traceable project intelligence.

ControlCheck becomes an AI Project Control Assistant / Project Intelligence Assistant. The project workspace and uploaded evidence are the center of the product. Primary users are project controls engineers, planners, cost engineers, project managers and PMO leads. Indonesian copy is the default; field identifiers and API contracts use English.

## Jobs and journey
1. Create a project with currency and reporting date.
2. Inspect Excel (.xlsx) or UTF-8 CSV, then confirm worksheet, header row and numeric/date conventions before import.
3. Review suggested source-to-semantic column mapping. Never publish an AI suggestion automatically.
4. Inspect row-level quality findings; correct the source and re-upload if blocking errors exist.
5. Publish a validated snapshot, then inspect schedule, progress and cost measures.
6. Ask the assistant a question and receive supported facts with file, worksheet and row citations.
7. Read prioritized insights and export a dated executive report.

## MVP requirements and acceptance
| Capability | Acceptance target for full MVP | Scaffold coverage |
|---|---|---|
| Project workspace | Project-specific source data, configuration and conversation history | Create/select projects; persisted data and settings; conversation is session-only |
| Upload | CSV/XLSX, clear constraints, sheet/header choice, explicit locale conversion, immutable source identity | File inspection, XLSX sheet list, header suggestion/override, date/decimal/percent settings, 5 MB / 10,000 rows / 100 columns, SHA-256 source identity |
| AI schema mapping | Model suggestions, confidence, rationale, manual confirmation and review | Deterministic bilingual suggestions and editable confirmation; provider protocol for future LLM |
| Quality engine | Required fields, typing, duplicates, ranges and business consistency | Row/field errors block publication; warnings surface incomplete optional facts |
| Semantic model | Versioned schedule/progress/cost snapshots with provenance | Activity-grain snapshot, project scope, monetary currency at project level, row provenance |
| Assistant | Answers grounded in approved project tools, citations, abstention | Read-only local analytic assistant; provider integration remains a milestone |
| Analytics | Schedule variance, weighted progress, EVM with valid denominators | Overdue count, weighted progress, PV/EV/AC/BAC, SPI/CPI, SV/CV when all required facts exist |
| Insights | Severity, evidence, explanation and suggested response | Rules for overdue work, SPI and CPI; no automatic changes |
| Reports | Reviewable dated executive report, evidence and caveats | Markdown download from the same published snapshot |

## Scaffold data contract
One row is one leaf activity, one reporting snapshot, one currency. Required fields: activity_id, name. Optional: planned_start, planned_finish, planned_progress, actual_progress, budget, actual_cost and weight. Never mix WBS summary rows with leaf activity rows. Before import, the user chooses ISO, day-first or month-first dates; dot or comma decimals; and whether progress uses 0–100 points or 0–1 fractions. Conversions are explicit and stored with the source. Currency symbols and thousands separators are rejected. Excel formula cells must be replaced with values. Missing values stay unknown.

Each publication is a complete replacement snapshot, not an append or merge. This avoids double counting repeated activity IDs and costs. Separate schedule/cost/progress table reconciliation is full-MVP follow-up. Workbook sheets and the selected physical header row remain attached to source provenance. Forecast dates, critical path and root-cause claims cannot be inferred from this contract.

## Trust and control
Uploaded text is untrusted evidence, never instructions. All numerical answers come from deterministic analytics. A model may narrate tool results but cannot execute uploaded instructions or mutate a project. Unknown facts and missing dates yield an explicit insufficient-data answer. Uploaded files stay local in this scaffold; no external AI requests occur. Multiuser authentication, tenant authorization, malware scanning, retention/deletion controls, backups and audit export are production gates.

## Success measures for pilot
Measure time from upload to first validated insight, mapping corrections per file, percentage of answers with valid citations, quality failures resolved, report generation time and unsupported-claim rate. Targets: all numerical claims have evidence; no critical cross-project leakage; a 1,000-row template completes the journey without manual database edits. Latency targets are set after representative pilot benchmarks, not claimed by the scaffold.

## Not in this increment
MPP/XER parsing, dependency-network scheduling, critical path, forecasting, probabilistic completion dates, resource leveling, autonomous actions, notifications, portfolio rollups, OCR/PDF extraction, SaaS billing and production deployment.

