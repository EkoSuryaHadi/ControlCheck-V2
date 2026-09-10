# Grounded AI MVP with SumoPod Implementation Plan

1. Add a tested OpenAI-compatible SumoPod gateway with model allow-list and safe failure handling.
2. Build an evidence-bounded assistant that validates returned citations and falls back to local analysis.
3. Add optional AI mapping proposals guarded by existing mapping validation and manual approval.
4. Persist assistant exchanges per project/snapshot and expose model availability without secrets.
5. Add model selection and saved conversation display to the UI.
6. Verify citation rejection, prompt-injection boundary, project isolation, unavailable-provider fallback, tests, and production build.
