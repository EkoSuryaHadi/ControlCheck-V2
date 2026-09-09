# Autonomous Ingestion Agent Design

## Goal

Make data intake a one-step workflow. A user uploads a CSV, XLSX, or Microsoft Project MPP file and ControlCheck AI reads, classifies, maps, validates, reconciles, and publishes it without requiring the user to configure sheets, headers, formats, mappings, or publication.

## User flow

1. The user selects one or more files and presses **Analyze project data**.
2. The Ingestion Agent inspects each workbook or CSV, chooses the most likely data sheet and header row, and infers date, decimal, and progress formats.
3. It classifies each source as Schedule, Progress, Cost, or Combined using the inferred semantic fields.
4. It applies the existing local schema mapper, validates rows, and reconciles Schedule with optional Progress and Cost sources.
5. When all blocking checks pass, it creates and activates a snapshot automatically.
6. The interface displays a compact receipt: files used, agent decisions, row coverage, validation warnings, snapshot version, and direct links to Overview and Assistant.

The existing detailed Data Center controls remain available as an advanced review path. They do not interrupt a successful automatic intake.

## Microsoft Project MPP

MPP is a direct Schedule source. The MPP reader extracts task identifiers, names, WBS hierarchy, planned and actual dates, durations, percent complete, dependencies, baselines, resources, and task costs when those fields are present in the file. Summary rows are retained for hierarchy context but are excluded from activity-level performance calculations unless explicitly supported by a later semantic-model rule.

The reader uses a maintained project-file parser behind an adapter so the application is not coupled to one file-library API. It maps the extracted task table to the same Schedule semantic fields used by CSV/XLSX, retains MPP task UID and source evidence, and then runs the ordinary quality gate and automatic publication flow. Microsoft Project XML is supported as a fallback input when an MPP file cannot be read.

MPP parsing failure never replaces the active snapshot. The receipt explains that the project file could not be read and offers the XML fallback or advanced review path.

## Decision policy

The agent is deterministic in the MVP. It uses inspection metadata, field aliases, and validation rules already present in the API. It does not call an external language model or require a provider key.

It publishes automatically only when:

- a source maps every required field for its inferred type;
- all values pass the current blocking quality checks;
- a Schedule or Combined source is available;
- optional Progress and Cost activity IDs match the Schedule; and
- all selected files belong to the current project upload request.

It stops without changing the active snapshot when it encounters unsupported files, ambiguous source classification, missing required fields, invalid values, duplicate IDs, or unmatched IDs. The response gives a concise explanation, the affected source, and a link to the advanced review panel.

Warnings do not block automatic publication. They appear in the receipt so the user can inspect their impact.

## API and domain model

`POST /api/projects/{pid}/ingestions` accepts one or more CSV, XLSX, MPP, or Microsoft Project XML upload files. It returns an immutable ingestion receipt with status `published` or `needs_attention`.

The receipt contains:

- `status`, `summary`, `snapshot` when published;
- `sources`, including chosen sheet/header/normalization/type/mapping;
- `coverage` for Schedule, Progress, and Cost;
- validation warnings and blocking issues; and
- an ordered `decisions` log suitable for showing in the UI and for later audit.

An `ingestion.py` service coordinates importer, mapper, validator, reconciler, and repository publication. Existing source and reconciliation endpoints stay supported for the advanced path. The service always recalculates its result before repository publication; the browser never authorizes a snapshot merely by reporting a prior preview.

## Interface

Data Center gains a primary **Drop project files here** panel. Users may upload a single Schedule file, one Combined file, or a batch containing Schedule plus Progress and/or Cost. A processing state shows the five agent steps. Successful intake replaces the panel with a publication receipt and an **Open project overview** button. Attention-needed intake retains the uploaded sources and presents a single **Review data** action.

The prior sheet/header/mapping controls move below this primary panel under **Advanced data review**.

## Testing

Domain tests cover classification, decision logging, schedule-only publication, multi-file publication, and no-publication paths. HTTP tests cover a complete one-upload journey and a batch with unmatched IDs. Frontend tests/build verify the simple upload path and receipt rendering. Browser verification creates a project, uploads data, and reaches Overview without manual mapping.

## Future extension

An optional model-backed interpreter may later propose mappings when deterministic aliases are insufficient. It must emit the same receipt structure and may only publish after the existing deterministic quality gate passes. Primavera XER is the next project-schedule import after MPP/XML.
