# HP Motor – Development Rules (No Regressions)

## Non-negotiables
1) No regression: Existing features and outputs must not be broken by new work.
2) Every change must keep CI green.
3) If an API/contract changes, add an adapter; do not break callers.

## Contracts (must remain stable)
- SovereignOrchestrator.execute(...) returns:
  - status
  - metrics
  - evidence_graph
  - tables
  - lists
  - figure_objects (optional, for Streamlit)

## Workflow
- Step 1: Add/modify feature behind stable contract
- Step 2: Add/update tests (minimum: smoke import + one e2e)
- Step 3: Update CHANGELOG.md with:
  - Added
  - Changed (compatible)
  - Fixed
  - Risks/Notes

## CI Gates
- Smoke import must pass
- E2E minimal test must pass
- Required files must exist:
  - src/hp_motor/registries/master_registry.yaml
  - src/hp_motor/pipelines/analysis_objects/player_role_fit.yaml