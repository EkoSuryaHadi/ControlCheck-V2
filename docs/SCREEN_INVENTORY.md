# Screen inventory

Visual direction: calm, precise project-control workspace; warm neutral canvas, deep green navigation and restrained amber risk accents. Indonesian labels; semantic field names remain stable English identifiers. Desktop-first tables adapt with horizontal scrolling, forms stack on small screens, all controls have labels and keyboard focus.

| Screen | Primary job | Interaction | Empty/loading/error states |
|---|---|---|---|
| Project selector / creation | Establish data boundary | Create project with name, currency, reporting date; switch current project | First-project guidance; validation message; disable duplicate submissions |
| Overview | Understand the published snapshot | Metrics, coverage, activity register, go to upload/assistant | No fabricated demo metrics; upload CTA; API unavailable message |
| Data Center | Convert source into approved data | Inspect file, preview rows, select sheet/header/date/decimal/progress conventions, review mapping and publish | Inspection/upload progress; parse failures; blocking quality findings; missing optional fields |
| AI Assistant | Ask about validated project evidence | Suggested prompts, question form, answer, citations | Explicit local-analysis mode; abstention for unsupported questions; session conversation clears on project change |
| Insights | Prioritize evidence-backed issues | Severity, rationale, source rows and response suggestions | No published data; no triggered rule is not a claim that project is risk-free |
| Reports | Produce executive snapshot | Preview dated report and download Markdown | No snapshot disables export; report carries version, currency, provenance and limitations |
| Settings | Inspect boundaries and project metadata | Read project currency/date, supported inputs and AI mode | Read-only in scaffold; future settings editing is a roadmap item |

## Required review details
Data Center displays the inspected matrix with the selected header highlighted, explicit normalization settings, suggestion confidence/rationale, a field mapping editor, source preview, row count, selected sheet, source ID and publication policy. Publication must never be enabled before a successful quality check of the current mapping. Changing mapping invalidates that check.

## Follow-up screens
Dataset history/compare, multi-table reconciliation, mapping templates, quality resolution editor, source evidence drawer, conversation history, report templates, forecasting assumptions/results, agent action approvals and workspace membership. These are designed as roadmap boundaries, not represented as functional screens in this scaffold.

