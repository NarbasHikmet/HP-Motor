from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

import yaml


REG_DIR = Path(__file__).resolve().parent
SEED_DIR = REG_DIR / "seed"
COMPILED_DIR = REG_DIR / "compiled"

MASTER_YAML = REG_DIR / "master_registry.yaml"
COMPILED_JSON = COMPILED_DIR / "master_registry.json"


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _load_yaml(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge src into dst (recursive). Lists are concatenated by default.
    """
    for k, v in src.items():
        if k not in dst:
            dst[k] = v
            continue
        if isinstance(dst[k], dict) and isinstance(v, dict):
            _deep_merge(dst[k], v)
        elif isinstance(dst[k], list) and isinstance(v, list):
            dst[k] = dst[k] + v
        else:
            # src wins for scalars
            dst[k] = v
    return dst


def validate_master(master: Dict[str, Any]) -> None:
    """
    Minimal structural validation.
    v1.0 goal: ensure SSOT has required top-level blocks.
    """
    if "registry" not in master or not isinstance(master["registry"], dict):
        raise ValueError("master_registry.yaml must contain top-level 'registry' mapping.")

    reg = master["registry"]
    required = ["id", "version", "canonical", "metrics", "visual", "personas"]
    missing = [k for k in required if k not in reg]
    if missing:
        raise ValueError(f"master_registry.yaml missing required fields: {missing}")

    if "plots" in reg["visual"] and not isinstance(reg["visual"]["plots"], list):
        raise ValueError("registry.visual.plots must be a list.")

    if "tables" in reg["visual"] and not isinstance(reg["visual"]["tables"], list):
        raise ValueError("registry.visual.tables must be a list.")

    # ensure metric ids unique
    metrics = reg.get("metrics", [])
    ids = [m.get("metric_id") for m in metrics]
    if any(i is None for i in ids):
        raise ValueError("All metrics must have metric_id.")
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise ValueError(f"Duplicate metric_id(s) in registry.metrics: {dup}")

    # ensure plot ids unique
    plots = reg.get("visual", {}).get("plots", [])
    pids = [p.get("plot_id") for p in plots]
    if any(i is None for i in pids):
        raise ValueError("All plots must have plot_id.")
    if len(pids) != len(set(pids)):
        dup = sorted({i for i in pids if pids.count(i) > 1})
        raise ValueError(f"Duplicate plot_id(s) in registry.visual.plots: {dup}")


def build_compiled() -> None:
    """
    Build compiled registry JSON. v1.0: master YAML is source of truth;
    seeds are optionally merged (additive).
    """
    COMPILED_DIR.mkdir(parents=True, exist_ok=True)

    master = _load_yaml(MASTER_YAML)

    # Optional: merge seeds if present (additive).
    # Keep this conservative: only add ontology/provider mappings when found.
    seed_files = {
        "canon_metric_ontology.json": ("registry", "ontology"),
        "canon_platform_mappings.json": ("registry", "provider_mappings"),
        "canon_registry.json": ("registry", "metrics"),
        "hp_registry.json": ("registry", "metrics"),
    }

    for fname, target_path in seed_files.items():
        fpath = SEED_DIR / fname
        if not fpath.exists():
            continue

        seed = _load_json(fpath)
        # Attempt to map known seed shapes:
        # - ontology json: dict of families → merge into registry.ontology.metric_families if present
        # - platform mappings json: dict of canonical metric → provider aliases → merge into registry.provider_mappings
        # - registry json: either dict or list → normalize into list of metric dicts
        reg = master["registry"]

        if fname.endswith("metric_ontology.json") or "metric_ontology" in fname:
            families = seed.get("metric_families") or seed
            reg.setdefault("ontology", {}).setdefault("metric_families", {})
            _deep_merge(reg["ontology"]["metric_families"], families)

        elif fname.endswith("platform_mappings.json") or "platform_mappings" in fname:
            reg.setdefault("provider_mappings", {})
            _deep_merge(reg["provider_mappings"], seed)

        elif fname.endswith("registry.json") or fname == "hp_registry.json":
            metrics = seed.get("metrics")
            if metrics is None:
                # could be dict of metric_id → defs
                if isinstance(seed, dict):
                    metrics = []
                    for k, v in seed.items():
                        if isinstance(v, dict):
                            v = {"metric_id": k, **v}
                            metrics.append(v)
                elif isinstance(seed, list):
                    metrics = seed
                else:
                    metrics = []
            if isinstance(metrics, dict):
                metrics = [{"metric_id": k, **(v if isinstance(v, dict) else {})} for k, v in metrics.items()]
            if not isinstance(metrics, list):
                metrics = []
            reg.setdefault("metrics", [])
            reg["metrics"].extend(metrics)

    validate_master(master)

    with COMPILED_JSON.open("w", encoding="utf-8") as f:
        json.dump(master, f, ensure_ascii=False, indent=2)

    print(f"Compiled registry written to: {COMPILED_JSON}")


if __name__ == "__main__":
    build_compiled()