from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def _find_repo_root(start: Path, max_hops: int = 12) -> Optional[Path]:
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


def _load_yaml(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_canon_index() -> Dict[str, Any]:
    repo_root = _find_repo_root(Path(__file__).resolve().parent)
    if repo_root is None:
        return {}
    idx = repo_root / "canon" / "index.yaml"
    if not idx.exists():
        return {}
    try:
        return _load_yaml(idx)
    except Exception:
        return {}


def _load_legacy_repo_registry(repo_root: Path) -> Dict[str, Any]:
    """
    Fallback legacy: repo-root canon/registry.json
    Accepts:
      - {"metrics": {...}}
      - {"metrics": [ {...}, ... ]}
      - direct dict keyed by metric_id
    """
    registry_path = repo_root / "canon" / "registry.json"
    if not registry_path.exists():
        return {}

    try:
        reg = _load_json(registry_path)
    except Exception:
        return {}

    metrics: Dict[str, Any] = {}
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


def _load_engine_registry_if_present(repo_root: Path, index: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optional primary: canon/engine_registry/metrics_core_v1.yaml (list or dict based)
    Normalized to dict keyed by canonical_name/metric_id.
    """
    sources = (index or {}).get("sources", {}) or {}
    eng = (sources.get("engine") or {}) if isinstance(sources, dict) else {}
    reg_root = eng.get("engine_registry_root", "canon/engine_registry")
    reg_path = repo_root / reg_root / "metrics_core_v1.yaml"
    if not reg_path.exists():
        return {}

    try:
        data = _load_yaml(reg_path)
    except Exception:
        return {}

    out: Dict[str, Any] = {}
    metrics = (data or {}).get("metrics")
    if isinstance(metrics, list):
        for m in metrics:
            if not isinstance(m, dict):
                continue
            key = (m.get("canonical_name") or m.get("metric_id") or m.get("id") or "").strip()
            if key:
                out[key] = m
    elif isinstance(metrics, dict):
        for k, v in metrics.items():
            if isinstance(k, str) and k.strip():
                out[k.strip()] = v
    return out


def load_canon_metrics() -> Dict[str, Any]:
    """
    SSOT rule:
      1) Engine registry (if exists) is primary
      2) Legacy repo canon/registry.json fills gaps only
    """
    repo_root = _find_repo_root(Path(__file__).resolve().parent)
    if repo_root is None:
        return {}

    index = load_canon_index()

    legacy = _load_legacy_repo_registry(repo_root)
    engine = _load_engine_registry_if_present(repo_root, index)

    merged = dict(legacy)
    merged.update(engine)  # Engine primary overwrites same keys
    return merged