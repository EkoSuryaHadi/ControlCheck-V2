# Grounded AI MVP with SumoPod

## Goal

Offer a conversational Project Intelligence Assistant through SumoPod while retaining deterministic project calculations, approved snapshots, and traceable evidence as the source of truth.

## Provider contract

The server reads `SUMOPOD_API_KEY` only from its environment and calls SumoPod's OpenAI-compatible Chat Completions endpoint at `https://ai.sumopod.com/v1`. The client may choose from an allow-listed model catalogue. The key never reaches the browser, database, report, or logs.

## Grounding boundary

The model receives a bounded, typed context derived from the active snapshot: project metadata, deterministic metrics, rule insights, limitations, and activity evidence. File contents are data, never instructions. The model returns JSON containing prose and citation tokens. Every citation token is validated against the snapshot before it is shown. An invalid provider response, timeout, missing key, or missing evidence falls back to local analytics.

## Schema mapping

For unknown spreadsheet headers, the provider may propose only canonical allow-listed fields. It cannot publish a source. Existing mapping validation still rejects duplicate or invalid targets, and the user must confirm the mapping.

## Conversation persistence

Question and response records are retained locally per project and snapshot version. They are read-only records in this increment. No cross-project conversation lookup is allowed.

## Non-goals

No AI provider credentials in the UI, no autonomous actions, no external file retrieval, no forecast claims, and no model-generated numeric calculation. Deterministic analytics remain authoritative.
