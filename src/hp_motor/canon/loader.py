from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def _find_repo_root(start: Path, max_hops: int = 10) -> Optional[Path]:
    """
    Walk upwards to locate a repo root heuristically.
    Markers:
      - pyproject.toml
      - .git (dir)
      - README.md
    """
    cur = start.resolve()
    for _ in range(max_hops):
        if (cur / "pyproject.toml").exists() or (cur / ".git").exists() or (cur / "README.md").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_canon_metrics() -> Dict[str, Any]:
    """
    Loads canon metrics into memory.

    Supported layouts (antifragile):
      A) Package-local: src/hp_motor/canon/canon_data/**/*.metric_spec.json
      B) Repo-root: canon/registry.json (fallback; current repo has this)
    """
    metrics: Dict[str, Any] = {}

    # A) Package-local canon_data (preferred if present)
    canon_data_root = Path(__file__).resolve().parent / "canon_data"
    if canon_data_root.exists():
        for spec_file in canon_data_root.rglob("*.metric_spec.json"):
            try:
                spec = _load_json(spec_file)
                metric_id = (spec.get("metric_id") or spec.get("id") or "").strip()
                if metric_id:
                    metrics[metric_id] = spec
            except Exception:
                continue

        if metrics:
            return metrics

    # B) Repo-root canon/registry.json (fallback)
    repo_root = _find_repo_root(Path(__file__).resolve().parent)
    if repo_root is None:
        return metrics

    registry_path = repo_root / "canon" / "registry.json"
    if not registry_path.exists():
        return metrics

    try:
        reg = _load_json(registry_path)
    except Exception:
        return {}

    # Accept common shapes:
    # - {"metrics": {...}}
    # - {"metrics": [ {...}, ... ]}
    # - direct dict keyed by metric_id
    if isinstance(reg, dict):
        m = reg.get("metrics", reg)
        if isinstance(m, dict):
            for k, v in m.items():
                if isinstance(k, str) and k.strip():
                    metrics[k.strip()] = v
        elif isinstance(m, list):
            for obj in m:
                if isinstance(obj, dict):
                    mid = (obj.get("metric_id") or obj.get("id") or "").strip()
                    if mid:
                        metrics[mid] = obj

    return metrics