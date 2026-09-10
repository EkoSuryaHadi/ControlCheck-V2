# Primavera P6 XER importer design

## Purpose

ControlCheck accepts a Primavera P6 XER schedule through the same approved-data pipeline as MPP and Microsoft Project XML. The importer extracts a schedule activity table and relationship facts while retaining P6-specific source metadata for review. It does not calculate a critical path, forecast a date, repair a schedule, or alter the XER source.

## Adapter decision

The existing MPXJ Java adapter is extended through its UniversalProjectReader. This keeps MPP and XER parsing in one constrained file-reader boundary and avoids a second, partial XER parser. Java 17 and the existing MPXJ dependency are required for XER just as they are for MPP.

## Input and normalization

The importer accepts the `.xer` extension only. It writes the bounded upload to a temporary `.xer` file, reads it through MPXJ, deletes the temporary file, and returns the ordinary source-table shape.

Each non-summary P6 activity becomes one row. `Activity ID` uses P6 activity ID when available, falling back to the opaque task unique ID only when the activity ID is absent. A P6 relationship resolves to the source activity’s Activity ID, so `Predecessor IDs` can be reconciled against the same visible ID. The schedule fields are:

- Activity ID, Name, Planned Start, Planned Finish, Actual Progress
- Budget and Actual Cost when MPXJ exposes them
- Is Critical, Is Milestone, Total Slack, Predecessor IDs

The source table also retains un-mapped audit columns: Task UID, Calendar, Constraint Type, Constraint Date, Baseline Start, and Baseline Finish. These remain source evidence and are not silently used as semantic facts until a later contract explicitly supports them.

## Diagnostics and publication

An unreadable XER, unavailable Java/MPXJ runtime, no usable activities, duplicate activity IDs, or an invalid normalized schedule follows existing import error handling. Automatic ingestion returns `needs_attention`; no invalid source changes the active snapshot. Manual upload returns a clear HTTP validation error.

The existing 5 MB, 10,000-row, 100-column bounds remain in effect. No raw XER bytes are retained. The source retains filename, SHA-256, selected synthetic sheet label `Primavera P6`, parsing normalization, headers, and rows.

## User interface

Data Center allows `.xer` in the primary multi-file input and labels it “Primavera P6 XER”. The helper text tells users that Java 17 is required. The ordinary agent receipt shows XER classification, mapping, quality findings, and publication state. Advanced review exposes P6 metadata columns in source preview but only canonical schedule fields are selectable for semantic mapping.

## Boundaries

Calendar, constraints, and baseline values are preserved as source metadata only. The application does not infer a working calendar, calculate float, set a baseline, select a P6 project when an export contains more than one, or make forecast claims. If MPXJ cannot select a usable schedule, import stops with a diagnostic.

## Tests

Unit tests cover P6 ID preference, predecessor Activity ID resolution, preservation of audit metadata, and no-summary-row behavior through a normalized task fixture. Importer tests cover `.xer` routing and a controlled parser-unavailable diagnostic. API tests cover successful XER source inspection/upload with a parser double and ensure failed XER import cannot activate a snapshot. Regression verification includes all backend tests, frontend production build, and OpenAPI export.
