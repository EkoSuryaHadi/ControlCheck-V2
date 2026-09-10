# Schedule Integrity Check Implementation Plan

1. Add failing semantic and analytics tests for explicit blank predecessor cells, cycles, and isolated activities.
2. Preserve an explicit empty predecessor tuple when its source column is mapped.
3. Derive cycle components and isolated activities from the actual dependency graph.
4. Add evidence-backed review insights and a local assistant response.
5. Run the full test suite and production build, then publish the verified increment.
