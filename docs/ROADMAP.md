# Delivery roadmap

| Stage | Deliverable | Exit gate |
|---|---|---|
| 0 — this scaffold | Repo, documents, local workspace, inspected CSV/XLSX journey with header and normalization controls, deterministic calculations, rule insights, local assistant, Markdown export | Backend tests and frontend production build; manual/browser journey checked |
| 1 — ingestion MVP | Multi-table schedule/progress/cost joins, mapping templates, unit conversion, source retention, dataset history, job retries | Representative customer workbooks imported without silent coercion or double counting |
| 2 — grounded AI MVP | Chosen provider adapter, tool-based assistant, model schema mapping with user review, persistent conversations | Evaluation suite for citations, abstention, injection, project isolation, timeouts and provider cost ceilings |
| 2.5 — snapshot history | Publication dates, immutable history, consecutive-period comparison and multi-period performance trends | Deltas preserve unknown values, source scope changes are explicit, and no causal/forecast claim is made |
| 3 — operational MVP | OIDC, tenant authorization, PostgreSQL migrations, object storage, queued ingestion, audit trail, backup and deletion | Security review, restore exercise, load checks, retention and authorization acceptance |
| 4 — reporting and pilot | Report templates, PDF/XLSX exports, stakeholder review flow, pilot feedback | Reports reconcile to approved source snapshots and meet pilot usability targets |
| 5 — schedule intelligence | MPP/XML and P6 XER adapters are enabled; relationship facts and P6 metadata are retained, while calendar/constraint/baseline calculation remains planned | Golden-file parity against scheduling tool outputs; explicit unsupported construct diagnostics |
| 6 — forecasting | Deterministic weekly S-Curve distribution, standard EVM forecasting (EAC, VAC, TCPI) and Forecast Readiness gate are enabled; probabilistic completion dates (Monte Carlo) and scenario models remain planned | Documented assumptions, calibrated backtesting and uncertainty; no guarantees from sparse data |
| 7 — agentic assistance | Read-only investigation agents, then approval-gated action proposals | Permission checks, dry run, idempotent execution, audit and rollback strategy per action |

## First implementation backlog after handoff
1. Collect anonymized schedule, progress and cost workbooks plus an expected executive report.
2. Add DatasetType and activity/WBS join contracts; reject unmatched and duplicate grain.
3. Add unit and currency conversion profiles on top of the existing date, decimal and percentage controls.
4. Add immutable original-file retention and source-cell evidence lookup.
5. Select an LLM provider and data-processing policy, then implement the protocols with a mocked evaluation suite before using real project data.

No calendar commitments are assumed. Finish each exit gate before enabling dependent capabilities.

### UI workspace & ingestion engine refresh
- Implemented: navy/light/green visual identity, responsive navigation, upload/assistant shortcuts, truthful assistant mode label, raw file object storage retention (local disk / S3-MinIO abstraction) with SHA-256 integrity check, and asynchronous background ingestion worker queue with granular stage progression.
- Pending: browser visual verification of the refreshed UI.

### Advanced analytics engine (Fitur Analitik Lanjutan)
- Implemented: time-phased deterministic S-Curve (Kurva-S) with weekly planned vs actual progress tracking and SVG visualization; deterministic standard EVM cost forecasting ($EAC_{CPI}$, $EAC_{composite}$, $VAC$, $TCPI$) with explicit assumptions and limitation guards; multi-period historical trend across all published snapshots.
- Planned: probabilistic completion modeling (Monte Carlo simulation) and resource-constrained scenario simulation.
