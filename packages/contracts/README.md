# Contracts

openapi.json is generated from apps/api/controlcheck/main.py using scripts/export_contracts.py. Run that script after API changes and review the diff. The client keeps a small typed response model in apps/web/src/types.ts; code generation may replace it once the API stabilizes.

Canonical semantic version: activity-snapshot/v1. Each activity belongs to a project-scoped snapshot and carries source_id, sheet and original row number. Dates use YYYY-MM-DD. Progress uses 0–100 points. Currency belongs to the project, and mixing currencies in one snapshot is unsupported. Null means unknown, never zero. A breaking grain or unit change requires a new semantic version and migration strategy.
