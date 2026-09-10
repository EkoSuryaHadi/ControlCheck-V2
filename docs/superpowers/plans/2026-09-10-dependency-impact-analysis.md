# Dependency Impact Analysis Implementation Plan

1. Add failing tests for project-file predecessor export, semantic normalization, and deterministic downstream impact.
2. Preserve predecessor IDs from Microsoft Project XML and MPP adapters.
3. Add the canonical predecessor field and strict list parsing.
4. Build a cycle-safe reverse dependency graph in analytics and emit factual exposure metrics and insights.
5. Surface the metrics in the overview, then run API tests and the production web build.
