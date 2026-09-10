# Forecast Readiness design

## Purpose

Forecast Readiness tells a project team whether the published evidence is sufficient to begin a completion-date or delay-risk forecast. It is a gate for a later forecast engine, not a forecast itself. It never produces a finish date, probability, recovery duration, root cause, or critical path.

## User outcome

From Overview, the user sees one of three statuses:

- **Belum siap**: required evidence is absent.
- **Perlu perbaikan**: evidence exists but schedule integrity prevents using it safely.
- **Siap untuk forecast method**: inputs meet the readiness gate; a later method may be chosen explicitly.

The card lists the missing or blocking inputs in Indonesian. It also states which snapshot version and reporting period were assessed.

## Readiness rules

The assessment is deterministic and project-scoped. It examines the active snapshot plus retained history.

1. At least two published snapshots must have different reporting dates.
2. The active snapshot must include `planned_start`, `planned_finish`, and `actual_progress` for every activity.
3. The active snapshot must include complete `predecessor_ids` coverage for every activity.
4. The dependency network must not contain cycles or relationships outside the published snapshot.
5. At least one schedule activity must remain incomplete; otherwise forecasting a remaining completion has no purpose.

A readiness result preserves coverage counts, IDs of blockers where applicable, and plain-language next actions. Missing values are not interpreted as zero. A complete relationship column with empty predecessor lists is valid for a one-activity schedule; for larger schedules it can be assessed but will surface isolated activities as a warning, not a blocker.

## API and domain

`forecast_readiness.py` is a pure module. It accepts an active snapshot, a list of historical snapshot summaries, and schedule analysis. It returns:

```json
{
  "status": "not_ready | needs_attention | ready_for_method",
  "snapshot_id": "...",
  "snapshot_version": 2,
  "reporting_dates": ["2026-09-08", "2026-09-15"],
  "checks": [{"id":"history", "status":"pass | missing | blocked", "detail":"..."}],
  "blockers": ["..."],
  "warnings": ["..."],
  "limitations": ["Forecast belum dihitung..."]
}
```

`GET /api/projects/{project_id}/forecast-readiness` returns the result for the active snapshot. Overview embeds the same object to avoid a second client request. The assistant receives this typed context. The local assistant can answer readiness questions but abstains from a date or probability request.

## UI

The Overview card appears after the snapshot comparison. It shows the status, pass/attention checks, and a link to Data Center. It does not show an action to "run forecast". The AI Assistant has a suggested prompt: “Apakah data saya siap untuk forecast?”

## Failure handling and trust

With no active snapshot the endpoint returns the existing publication-required response. A malformed or unavailable analysis result is treated as not ready with an explicit limitation. The provider receives only the bounded readiness object already derived from approved data. No uploaded file, database credential, or external source is added.

## Tests

Tests cover a ready schedule, each missing input, dependency cycle and external-link blockers, no remaining work warning, project isolation through the HTTP endpoint, and assistant readiness wording. Existing analytics, comparison, and browser build regression checks remain required.
