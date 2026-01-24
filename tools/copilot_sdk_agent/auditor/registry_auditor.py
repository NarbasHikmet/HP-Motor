from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from tools.copilot_sdk_agent.auditor.report_schema import AuditReport, Finding, derive_status


def _safe_read_text(p: Path, limit: int = 250_000) -> str:
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")[:limit]


def _load_yaml(p: Path) -> Optional[Dict[str, Any]]:
    if not p.exists():
        return None
    try:
        return yaml.safe_load(_safe_read_text(p)) or {}
    except Exception as e:
        return {"__parse_error__": str(e)}


def _list_yaml_files(dir_path: Path) -> List[Path]:
    if not dir_path.exists():
        return []
    out: List[Path] = []
    for ext in ("*.yml", "*.yaml"):
        out.extend(sorted(dir_path.glob(ext)))
    return out


def _guess_registry_metrics(reg: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], str]:
    """
    Supports multiple master registry styles:

    A) metrics as LIST of objects:
       metrics:
         - metric_id: xg
           label: xG
           ...

    B) metrics as DICT keyed by metric_id (current HP Motor):
       metrics:
         xg: { default: 0.0, ... }
         ppda: { default: 12.0, ... }

    C) nested registry.metrics:
       registry:
         metrics: ...
    """
    if reg is None:
        return [], "missing"

    # root(list) is supported for flexibility
    if isinstance(reg, list):
        return [x for x in reg if isinstance(x, dict)], "root(list)"

    # Style A: metrics: [ ... ]
    m = reg.get("metrics")
    if isinstance(m, list):
        return [x for x in m if isinstance(x, dict)], "metrics(list)"

    # Style B: metrics: { id: {...}, ... }
    if isinstance(m, dict):
        out: List[Dict[str, Any]] = []
        for k, v in m.items():
            if not isinstance(k, str) or not k.strip():
                continue
            if isinstance(v, dict):
                out.append({"metric_id": k.strip(), **v})
            else:
                # allow scalar default-only definitions: xg: 0.0
                out.append({"metric_id": k.strip(), "value": v})
        return out, "metrics(dict)"

    # nested registry
    r = reg.get("registry")
    if isinstance(r, dict):
        rm = r.get("metrics")
        if isinstance(rm, list):
            return [x for x in rm if isinstance(x, dict)], "registry.metrics(list)"
        if isinstance(rm, dict):
            out = []
            for k, v in rm.items():
                if not isinstance(k, str) or not k.strip():
                    continue
                out.append({"metric_id": k.strip(), **(v if isinstance(v, dict) else {"value": v})})
            return out, "registry.metrics(dict)"

    return [], "unknown"


def _metric_id(m: Dict[str, Any]) -> Optional[str]:
    for k in ("metric_id", "id", "key", "name_id"):
        v = m.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _extract_metric_refs_from_ao(ao: Dict[str, Any]) -> List[str]:
    """
    Supports:
      - ao.metric_bundle: [metric_id...]
      - ao.deliverables.required_metrics: [metric_id...]
      - ao.required_metrics: [metric_id...]   (common shortcut)
      - ao.metrics: [metric_id...]            (common shortcut)
    """
    refs: List[str] = []
    if not isinstance(ao, dict):
        return refs

    mb = ao.get("metric_bundle")
    if isinstance(mb, list):
        refs.extend([str(x).strip() for x in mb if str(x).strip()])

    deliver = ao.get("deliverables")
    if isinstance(deliver, dict):
        rm = deliver.get("required_metrics")
        if isinstance(rm, list):
            refs.extend([str(x).strip() for x in rm if str(x).strip()])

    rm2 = ao.get("required_metrics")
    if isinstance(rm2, list):
        refs.extend([str(x).strip() for x in rm2 if str(x).strip()])

    m2 = ao.get("metrics")
    if isinstance(m2, list):
        refs.extend([str(x).strip() for x in m2 if str(x).strip()])

    # uniq preserve order
    seen = set()
    out = []
    for r in refs:
        if r not in seen:
            out.append(r)
            seen.add(r)
    return out


def _extract_plot_ids_from_ao(ao: Dict[str, Any]) -> List[str]:
    if not isinstance(ao, dict):
        return []
    deliver = ao.get("deliverables")
    if not isinstance(deliver, dict):
        return []
    plots = deliver.get("plots")
    if isinstance(plots, list):
        return [str(x).strip() for x in plots if str(x).strip()]
    return []


class RegistryAuditor:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.master_registry_path = repo_root / "src" / "hp_motor" / "registries" / "master_registry.yaml"
        self.analysis_objects_dir = repo_root / "src" / "hp_motor" / "pipelines" / "analysis_objects"
        self.mappings_dir = repo_root / "src" / "hp_motor" / "registries" / "mappings"

    def run(self) -> AuditReport:
        rid = f"registry_audit_{int(time.time())}"
        findings: List[Finding] = []

        # ---- Existence checks
        if not self.master_registry_path.exists():
            findings.append(
                Finding(
                    code="REG_MISSING_MASTER",
                    severity="ERROR",
                    title="master_registry.yaml missing",
                    detail=f"Expected at: {self.master_registry_path.as_posix()}",
                    file=self.master_registry_path.as_posix(),
                )
            )

        if not self.analysis_objects_dir.exists():
            findings.append(
                Finding(
                    code="AO_DIR_MISSING",
                    severity="ERROR",
                    title="analysis_objects directory missing",
                    detail=f"Expected at: {self.analysis_objects_dir.as_posix()}",
                    file=self.analysis_objects_dir.as_posix(),
                )
            )

        # ---- Load registry
        reg = _load_yaml(self.master_registry_path) if self.master_registry_path.exists() else None
        if isinstance(reg, dict) and "__parse_error__" in reg:
            findings.append(
                Finding(
                    code="REG_PARSE_ERROR",
                    severity="ERROR",
                    title="master_registry.yaml cannot be parsed",
                    detail=str(reg.get("__parse_error__")),
                    file=self.master_registry_path.as_posix(),
                )
            )
            reg = None

        metrics, metrics_loc = _guess_registry_metrics(reg or {})
        if reg is not None and not metrics:
            findings.append(
                Finding(
                    code="REG_NO_METRICS",
                    severity="ERROR",
                    title="No metrics found in master registry",
                    detail=f"Could not find metrics list/dict. Location guess: {metrics_loc}",
                    file=self.master_registry_path.as_posix(),
                    hint="Define metrics under `metrics:` as either a list of objects or a dict keyed by metric_id.",
                )
            )

        # ---- Validate metrics
        metric_ids: List[str] = []
        missing_id_count = 0
        default_only_count = 0

        for m in metrics:
            mid = _metric_id(m)
            if not mid:
                missing_id_count += 1
                continue
            metric_ids.append(mid)

            # Detect "default-only" placeholder metrics
            keys = set(m.keys())
            if keys.issubset({"metric_id", "default", "value"}):
                default_only_count += 1

        if metrics_loc.endswith("(dict)"):
            findings.append(
                Finding(
                    code="REG_METRICS_DICT_STYLE",
                    severity="INFO",
                    title="Registry metrics use dict style",
                    detail="metrics are defined as a dict keyed by metric_id (supported).",
                    file=self.master_registry_path.as_posix(),
                )
            )

        dupes = sorted({x for x in metric_ids if metric_ids.count(x) > 1})
        if dupes:
            findings.append(
                Finding(
                    code="REG_DUP_METRIC_ID",
                    severity="ERROR",
                    title="Duplicate metric_id values",
                    detail=f"Duplicates: {', '.join(dupes[:30])}" + (" ..." if len(dupes) > 30 else ""),
                    file=self.master_registry_path.as_posix(),
                )
            )

        if missing_id_count > 0:
            findings.append(
                Finding(
                    code="REG_METRIC_ID_MISSING",
                    severity="WARN",
                    title="Some metrics are missing metric_id",
                    detail=f"{missing_id_count} metric entries have no metric_id/id/key.",
                    file=self.master_registry_path.as_posix(),
                )
            )

        if default_only_count == len(metric_ids) and len(metric_ids) > 0:
            findings.append(
                Finding(
                    code="REG_METRICS_DEFAULT_ONLY",
                    severity="WARN",
                    title="All metrics appear to be default-only placeholders",
                    detail=(
                        f"Detected {default_only_count}/{len(metric_ids)} metrics with only default/value fields. "
                        "This usually means the engine will 'talk with defaults' instead of computing."
                    ),
                    file=self.master_registry_path.as_posix(),
                    hint="Add compute metadata (inputs, required columns, calc refs) or enforce ABSTAIN when only defaults exist.",
                )
            )

        metric_id_set = set(metric_ids)

        # ---- Analysis Objects
        ao_files = _list_yaml_files(self.analysis_objects_dir) if self.analysis_objects_dir.exists() else []
        if not ao_files:
            findings.append(
                Finding(
                    code="AO_NONE",
                    severity="WARN",
                    title="No analysis objects found",
                    detail=f"No YAML files in {self.analysis_objects_dir.as_posix()}",
                    file=self.analysis_objects_dir.as_posix(),
                    hint="Create analysis_objects YAMLs to declare deliverables, required metrics, and plots.",
                )
            )

        ao_metric_refs_total = 0
        ao_missing_metric_refs: Dict[str, List[str]] = {}
        ao_plot_ids_total = 0

        for p in ao_files:
            ao = _load_yaml(p)
            if isinstance(ao, dict) and "__parse_error__" in (ao or {}):
                findings.append(
                    Finding(
                        code="AO_PARSE_ERROR",
                        severity="ERROR",
                        title="Analysis object YAML cannot be parsed",
                        detail=str((ao or {}).get("__parse_error__")),
                        file=p.as_posix(),
                    )
                )
                continue

            metric_refs = _extract_metric_refs_from_ao(ao or {})
            ao_metric_refs_total += len(metric_refs)

            missing = [m for m in metric_refs if m not in metric_id_set]
            if missing:
                ao_missing_metric_refs[p.name] = missing

            plot_ids = _extract_plot_ids_from_ao(ao or {})
            ao_plot_ids_total += len(plot_ids)

        if ao_missing_metric_refs:
            first_key = next(iter(ao_missing_metric_refs.keys()))
            sample = ao_missing_metric_refs[first_key][:15]
            findings.append(
                Finding(
                    code="AO_REF_UNKNOWN_METRIC",
                    severity="ERROR",
                    title="Analysis Objects reference unknown metric_ids",
                    detail=(
                        f"{len(ao_missing_metric_refs)} AO file(s) reference missing metrics. "
                        f"Example: {first_key} -> {', '.join(sample)}"
                        + (" ..." if len(ao_missing_metric_refs[first_key]) > 15 else "")
                    ),
                    file=self.analysis_objects_dir.as_posix(),
                    hint="Either add the missing metrics to master_registry.yaml or fix AO references.",
                )
            )

        # ---- Provider mappings
        mapping_files = _list_yaml_files(self.mappings_dir) if self.mappings_dir.exists() else []
        if not mapping_files:
            findings.append(
                Finding(
                    code="MAP_NONE",
                    severity="WARN",
                    title="No provider mapping files detected",
                    detail=f"No YAML files found under {self.mappings_dir.as_posix()}",
                    file=self.mappings_dir.as_posix(),
                    hint="Add mappings to standardize incoming columns (CSV/XML/XLSX providers).",
                )
            )

        status = derive_status(findings)
        summary = (
            f"Registry audit complete. metrics={len(metric_ids)}, analysis_objects={len(ao_files)}, "
            f"ao_metric_refs={ao_metric_refs_total}, plots_in_aos={ao_plot_ids_total}. status={status}."
        )

        next_actions: List[str] = []
        if any(f.code == "REG_METRICS_DEFAULT_ONLY" for f in findings):
            next_actions.append("Enforce ABSTAIN when only default metrics exist (no compute evidence).")
        if any(f.code == "MAP_NONE" for f in findings):
            next_actions.append("Add provider mappings under src/hp_motor/registries/mappings to normalize columns.")
        if len(ao_files) == 0:
            next_actions.append("Create at least 1 analysis_object YAML to declare tables/plots deliverables.")

        report = AuditReport(
            report_id=rid,
            status=status,
            summary=summary,
            stats={
                "metrics_count": len(metric_ids),
                "analysis_object_count": len(ao_files),
                "ao_metric_refs_total": ao_metric_refs_total,
                "ao_plot_ids_total": ao_plot_ids_total,
                "mapping_file_count": len(mapping_files),
                "master_registry_location_guess": metrics_loc,
                "default_only_metrics_count": default_only_count,
            },
            findings=findings,
            risks=[],
            next_actions=next_actions,
        )
        return report

    def render_markdown(self, report: AuditReport) -> str:
        lines: List[str] = []
        lines.append("# HP Motor Registry Audit")
        lines.append("")
        lines.append(f"- **report_id:** `{report.report_id}`")
        lines.append(f"- **status:** `{report.status}`")
        lines.append(f"- **summary:** {report.summary}")
        lines.append("")
        lines.append("## Stats")
        for k, v in (report.stats or {}).items():
            lines.append(f"- **{k}:** {v}")
        lines.append("")
        lines.append("## Findings")
        if not report.findings:
            lines.append("- (none)")
        else:
            for f in report.findings:
                loc = f" ({f.file})" if f.file else ""
                lines.append(f"- **[{f.severity}] {f.code}** — {f.title}{loc}")
                lines.append(f"  - {f.detail}")
                if f.hint:
                    lines.append(f"  - _hint:_ {f.hint}")
        lines.append("")
        if report.next_actions:
            lines.append("## Next actions")
            for a in report.next_actions:
                lines.append(f"- {a}")
            lines.append("")
        return "\n".join(lines)

    def write_artifacts(self, report: AuditReport) -> AuditReport:
        reports_dir = self.repo_root / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        json_path = reports_dir / f"{report.report_id}.json"
        md_path = reports_dir / f"{report.report_id}.md"

        json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        md_path.write_text(self.render_markdown(report), encoding="utf-8")

        report.artifacts["json"] = json_path.as_posix()
        report.artifacts["md"] = md_path.as_posix()
        return report