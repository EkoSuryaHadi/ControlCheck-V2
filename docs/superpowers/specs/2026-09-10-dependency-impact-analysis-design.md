# Dependency Impact Analysis Design

## Goal

Show downstream schedule exposure only when predecessor relationships are present in the uploaded Microsoft Project XML or MPP file.

## Source and canonical model

* The project-file adapter exports a `Predecessor IDs` column containing semicolon-separated task UIDs.
* Microsoft Project XML reads each task's `PredecessorLink/PredecessorUID` values.
* MPXJ reads each task predecessor relation's source task UID.
* The semantic model stores these as `predecessor_ids`, a tuple of source IDs. Empty values remain absent.

## Deterministic analysis

1. Build a reverse graph from predecessor ID to successor activities that are present in the published snapshot.
2. Start from activities that are both critical and overdue.
3. Traverse their reachable successors, with cycle protection.
4. Report only reachable downstream activities, and separately count milestones among them.

The result states that a successor is in the *jalur dampak* of a late critical activity. It does not predict completion dates, delay duration, causality, or recovery success.

## Product output

Metrics expose dependency metadata coverage, downstream activities, and downstream milestones. An insight appears only when a late critical activity has actual downstream links. The overview shows the dependency exposure count with its source-data coverage.

## Guardrails

* Missing dependency metadata produces a limitation, not a zero-risk conclusion.
* Links to activities outside the snapshot are ignored in traversal and counted as unavailable source context.
* CSV/XLSX can also use the optional `Predecessor IDs` column, but no relation is inferred from names or dates.
