# Snapshot history and period comparison

## Decision

A published snapshot remains immutable. Each publication carries its own reporting date, and the active snapshot can be compared with the immediately previous published snapshot for the same project.

## Comparison contract

The comparison returns progress, SPI, CPI, and overdue-count deltas only when both snapshots provide each metric; IDs added, removed, with changed actual progress, newly overdue, and no longer overdue; and prior/current snapshot identity and provenance.

It does not infer a cause, forecast a completion date, or treat added or removed activities as performance movement. Activity-level comparisons require the same `activity_id`.

## Flow

1. Choose the reporting date while publishing through the Ingestion Agent or advanced review.
2. The API publishes a new immutable snapshot and activates it.
3. Overview returns history and a comparison with the prior version.
4. Grounded AI receives the bounded comparison context and must still cite active snapshot evidence.
