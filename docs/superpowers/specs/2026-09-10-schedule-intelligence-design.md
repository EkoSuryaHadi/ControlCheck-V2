# Schedule Intelligence Design

## Goal

Turn an imported Microsoft Project schedule into evidence-backed schedule risk intelligence without requiring manual configuration.

## Scope

The MPP/XML adapter retains task UID, WBS outline level, milestone status, critical status, total slack, baseline dates, actual dates, and predecessor task UIDs. The semantic snapshot keeps these as optional schedule metadata alongside the existing activity fields. Spreadsheet sources remain valid and simply omit this metadata.

## Rules

The deterministic analytics layer produces three new schedule signals when source facts exist:

1. Critical activities that are not complete after their planned finish date.
2. Milestones whose planned finish date has passed but are not complete.
3. Critical activities with zero or negative total slack, reported as schedule exposure even before they are overdue.

Each signal links to the imported task row and states its coverage. Summary tasks never enter activity performance or critical counts. Missing critical, milestone, or slack metadata suppresses the corresponding rule and adds a limitation. The system does not calculate a new critical path or completion forecast; it reports the scheduler facts carried by the source plan.

## Data flow

MPP/XML reader → normalized task rows with optional schedule metadata → semantic validation retains metadata → immutable snapshot → analytics returns metrics, insights, limitations, and evidence → Overview/Insights/Assistant use the same result.

For MPP, predecessors are retained as source evidence for later dependency navigation, but the first increment does not render a network diagram or infer downstream dates.

## Interface

Overview adds a Schedule Intelligence strip with critical-task count, critical overdue count, milestone overdue count, and coverage. Insight cards distinguish critical exposure from ordinary overdue work. The activity register adds badges for Critical and Milestone when those source facts exist.

## Testing

Tests cover MPP task normalization, metadata preservation through semantic validation, critical overdue and milestone insights, and the absence of claims when schedule metadata is unavailable. Existing spreadsheet analytics tests remain unchanged.

## Boundaries

Forecasting needs status-date history, calendars, constraints, and a calculation policy; it is out of scope. The agent does not claim root cause or automatically alter schedule data.
