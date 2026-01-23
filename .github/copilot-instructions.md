# HP Motor – Copilot Instructions (Repository Rules)

These instructions are authoritative for this repository.

## Non-negotiables
1) DO NOT provide patches, diffs, or “add this snippet here” guidance.
   - Always output COMPLETE FILE CONTENTS for any file you want changed.
   - If multiple files are needed, output each file in full, clearly separated.

2) No regressions.
   - Never remove existing capabilities unless explicitly requested.
   - Preserve backward compatibility for public/used entrypoints (e.g., app.py, SovereignOrchestrator).

3) Contract-first development.
   - The core orchestrator output MUST maintain a stable contract:
     - status
     - metrics
     - evidence_graph
     - tables
     - lists
     - figure_objects (optional, UI runtime)
     - missing_metrics (optional)
     - data_quality / mapping_report (optional)

4) Separate runtime vs developer dependencies.
   - Streamlit deployment MUST NOT include dev/agent dependencies.
   - Keep `requirements.txt` minimal/stable (Streamlit runtime only).
   - Put agent/dev tools into `requirements-dev.txt` (or similar).

5) CSV + XML are first-class ingestion formats.
   - The UI must allow selecting CSV and XML files.
   - The ingestion layer must parse CSV and attempt XML parsing (fallback to text extraction if needed).
   - Never silently “hide” formats: if unsupported, return BLOCKED with a clear reason.

6) Determinism & explainability.
   - If a required metric cannot be computed due to missing columns, return:
     - status = "BLOCKED" or "OK" with missing_metrics populated (depending on design),
     - include a clear report (missing columns, mapping hits, data quality issues).

## Architecture conventions
- Keep application runtime stable:
  - Streamlit UI (`app.py`) should not import heavy agent tooling.
  - Agent tooling belongs under `tools/` (e.g., `tools/copilot_sdk_agent/`).

- Avoid import-time side effects:
  - No file IO or network calls at module import time.
  - Defer registry loading/validation to orchestrator init or execution functions.

- Pydantic / models:
  - Use defensive imports for optional symbols.
  - Use fallbacks when a model class is missing (but do not break contract).

## Output format rules for Copilot responses
When modifying code:
- Output the FULL content of each file to be created/updated.
- Use explicit headings:
  - "FILE: path/to/file"
  - then the full content.

Example:
FILE: src/hp_motor/example.py
```python
# full file content here