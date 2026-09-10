# Schedule Integrity Check Design

## Goal

Assess whether the imported dependency network is usable for schedule intelligence without changing or inventing the schedule.

## Checks

The deterministic analyzer reports three source-grounded conditions:

* predecessor links that point outside the published snapshot;
* circular dependency components among activities in the snapshot;
* isolated activities with no inbound or outbound relation when every activity supplied dependency metadata.

## Product behavior

These are review signals, never automatic schedule repairs and never publication blockers. A cycle is high priority because a dependency sequence cannot be traversed unambiguously. An external reference and an isolated activity are review signals: they may be valid only with source context outside the snapshot.

## Data semantics

When a `Predecessor IDs` column is mapped, a blank cell means the activity explicitly has no predecessor. When the column is absent, dependency remains unknown. This distinguishes an intentional root activity from missing dependency data.

## Guardrails

No task relationship is inferred from dates, activity names, WBS, or a critical flag. No critical-path calculation, schedule repair, duration, or completion forecast is produced.
