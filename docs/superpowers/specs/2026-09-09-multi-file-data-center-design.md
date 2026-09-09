# Multi-File Data Center — Design

Status: approved design direction, 9 September 2026.

## Purpose

ControlCheck accepts three independently prepared project-control datasets for one reporting date:

- **Schedule** is the master activity register.
- **Progress** provides actual progress for matching activities.
- **Cost** provides budget and actual cost for matching activities.

The system creates one semantic activity snapshot only after a user reviews the reconciliation and explicitly publishes it. Existing one-file uploads remain valid and publishable as a complete `combined` source.

## User flow

1. In Data Center, the user chooses a dataset type before inspecting a CSV or XLSX file.
2. Each file keeps the current sheet, header-row and normalization workflow, then receives a mapping appropriate to its dataset type.
3. After quality validation, the user selects one validated Schedule source and optional validated Progress and Cost sources.
4. The reconciliation screen reports matching coverage and blocking issues.
5. Publication remains disabled until Schedule has no duplicate IDs and every ID in Progress or Cost exists exactly once in Schedule.
6. A successful publication creates an immutable `activity-snapshot/v2` with source provenance for each copied field.

## Dataset contracts

| Dataset | Required mapping | Optional mapping | Grain |
|---|---|---|---|
| Schedule | `activity_id`, `name` | `planned_start`, `planned_finish`, `planned_progress`, `weight`, `budget` | One row per activity |
| Progress | `activity_id` | `actual_progress` | At most one row per activity |
| Cost | `activity_id` | `budget`, `actual_cost` | At most one row per activity |

All three sources use the existing explicit date, decimal and percentage normalization settings. A source may omit optional data, but an incomplete field remains unknown; it never becomes zero.

## Reconciliation rules

- Schedule is required and is the only source allowed to introduce activities.
- Duplicate `activity_id` values in any selected source are blocking errors.
- Every `activity_id` in Progress and Cost must appear in the selected Schedule source; unmatched IDs are blocking errors.
- Missing Progress or Cost for a Schedule activity is non-blocking and shown as a coverage gap.
- Field precedence is explicit: schedule owns identity/name/planned fields/weight, progress owns `actual_progress`, and cost owns `actual_cost`. Cost `budget`, when present, replaces Schedule `budget`; otherwise Schedule `budget` remains.
- A field copied into the merged row retains evidence with its original source ID, sheet and physical row. The activity record keeps the Schedule evidence as its primary source.
- Selecting an unvalidated source or sources from different projects is rejected before reconciliation.

## Persistence and API

Sources store `dataset_type` (`combined`, `schedule`, `progress`, `cost`) and their independent mapping/quality state stays a preview concern. Snapshot persistence changes from a single `source_id` to `source_ids`, while preserving the existing primary `source_id` as the Schedule/combined source for migration compatibility.

New API operations:

- Upload accepts `dataset_type` and returns it with source metadata.
- Validate accepts the source mapping as today and returns dataset-aware mapping errors.
- `POST /projects/{project_id}/reconciliations` accepts schedule, progress and cost source IDs plus mappings and returns a merged preview, coverage and issues without publishing.
- `POST /projects/{project_id}/reconciliations/publish` repeats reconciliation inside the transaction and creates the snapshot only when no blocking issue exists.

The server must recompute reconciliation during publication; it must not trust an earlier browser preview.

## Data Center interface

The existing import panel gains a **Jenis data** selector. The source list shows a type badge and validation state. A new reconciliation panel presents three source selectors, a compact coverage summary, blocking issue table, and a merged activity preview. The publish button moves into this panel for multi-file data. The legacy combined source retains its existing single-source publish path.

## Error handling

Errors identify dataset, source, row and activity ID where applicable. A reconciliation with conflicts does not alter the active snapshot. API calls remain project-scoped. The UI preserves selected sources after a failed reconciliation so the user can correct or replace only the affected file.

## Verification

Domain tests cover merge precedence, missing coverage, duplicate IDs, unmatched IDs and evidence propagation. HTTP tests cover project isolation, reconciliation preview, publishing a valid three-source set and rejection of conflicts. Frontend build and a headed browser journey verify selection, coverage feedback and a successful publication.

## Deliberate scope limits

This increment accepts one reporting snapshot and one row per activity in each dataset. Cost transaction aggregation, multiple progress periods, WBS rollups, resource data, automated mapping templates, source history comparison and MPP/XER parsing stay outside this increment.

