from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from tools.copilot_sdk_agent.auditor.report_schema import AuditReport, Finding, derive_status


def _safe_read_text(p: Path, limit: int = 200_000) -> str:
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
    Tries common shapes:
      - reg["metrics"] as list[dict]
      - reg["registry"]["metrics"] as list[dict]
      - reg itself as list (rare) -> treated as metrics list
    Returns: (metrics_list, location_string)
    """
    if reg is None:
        return [], "missing"

    if isinstance(reg, list):
        return [x for x in reg if isinstance(x, dict)], "root(list)"

    if isinstance(reg.get("metrics"), list):
        return [x for x in reg["metrics"] if isinstance(x, dict)], "metrics"

    r = reg.get("registry")
    if isinstance(r, dict) and isinstance(r.get("metrics"), list):
        return [x for x in r["metrics"] if isinstance(x, dict)], "registry.metrics"

    return [], "unknown"


def _metric_id(m: Dict[str, Any]) -> Optional[str]:
    for k in ("metric_id", "id", "key", "name_id"):
        v = m.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _extract_required_metrics_from_ao(ao: Dict[str, Any]) -> List[str]:
    """
    Looks for:
      ao.deliverables.required_metrics: list[str]
    """
    if not isinstance(ao, dict):
        return []
    deliver = ao.get("deliverables")
    if not isinstance(deliver, dict):
        return []
    rm = deliver.get("required_metrics")
    if isinstance(rm, list):
        return [str(x).strip() for x in rm if str(x).strip()]
    return []


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

        # canonical locations expected by HP Motor
        self.master_registry_path = repo_root / "src" / "hp_motor" / "registries" / "master_registry.yaml"
        self.analysis_objects_dir = repo_root / "src" / "hp_motor" / "pipelines" / "analysis_objects"
        self.mappings_dir = repo_root / "src" / "hp_motor" / "registries" / "mappings"
        self.specs_dir = repo_root / "src" / "hp_motor" / "viz" / "specs"

    def run(self) -> AuditReport:
        rid = f"registry_audit_{int(time.time())}"
        findings: List[Finding] = []

        # 1) Existence checks
        if not self.master_registry_path.exists():
            findings.append(
                Finding(
                    code="REG_MISSING_MASTER",
                    severity="ERROR",
                    title="master_registry.yaml missing",
                    detail=f"Expected at: {self.master_registry_path.as_posix()}",
                    file=self.master_registry_path.as_posix(),
                    hint="Create src/hp_motor/registries/master_registry.yaml (YAML).",
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
                    hint="Create src/hp_motor/pipelines/analysis_objects and add at least player_role_fit.yaml",
                )
            )

        # 2) Parse master registry
        reg = _load_yaml(self.master_registry_path) if self.master_registry_path.exists() else None
        if isinstance(reg, dict) and "__parse_error__" in reg:
            findings.append(
                Finding(
                    code="REG_PARSE_ERROR",
                    severity="ERROR",
                    title="master_registry.yaml cannot be parsed",
                    detail=str(reg.get("__parse_error__")),
                    file=self.master_registry_path.as_posix(),
                    hint="Fix YAML syntax; validate with a YAML linter.",
                )
            )
            reg = None

        metrics, metrics_loc = _guess_registry_metrics(reg or {})
        if reg is not None and not metrics:
            findings.append(
                Finding(
                    code="REG_NO_METRICS",
                    severity="WARN",
                    title="No metrics found in master registry",
                    detail=f"Could not find metrics list in expected locations (metrics / registry.metrics). Location guess: {metrics_loc}",
                    file=self.master_registry_path.as_posix(),
                    hint="Ensure master_registry.yaml contains a list of metrics with metric_id.",
                )
            )

        # 3) Metric hygiene checks
        metric_ids: List[str] = []
        missing_id_count = 0
        field_gaps = 0

        for m in metrics:
            mid = _metric_id(m)
            if not mid:
                missing_id_count += 1
                continue
            metric_ids.append(mid)

            # soft schema checks
            if not m.get("label") and not m.get("name"):
                field_gaps += 1
            if not m.get("description"):
                field_gaps += 1

        dupes = sorted({x for x in metric_ids if metric_ids.count(x) > 1})
        if dupes:
            findings.append(
                Finding(
                    code="REG_DUP_METRIC_ID",
                    severity="ERROR",
                    title="Duplicate metric_id values",
                    detail=f"Duplicates: {', '.join(dupes[:30])}" + (" ..." if len(dupes) > 30 else ""),
                    file=self.master_registry_path.as_posix(),
                    hint="Each metric_id must be unique across the registry.",
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
                    hint="Add metric_id to every metric dict. This is the canonical key.",
                )
            )

        if field_gaps > 0:
            findings.append(
                Finding(
                    code="REG_METRIC_FIELDS_GAPS",
                    severity="INFO",
                    title="Some metrics lack label/description",
                    detail=f"Detected {field_gaps} missing label/name/description fields across metrics (soft schema).",
                    file=self.master_registry_path.as_posix(),
                    hint="Add label + description for narrative quality and explainability.",
                )
            )

        metric_id_set = set(metric_ids)

        # 4) Analysis object checks
        ao_files = _list_yaml_files(self.analysis_objects_dir) if self.analysis_objects_dir.exists() else []
        if not ao_files:
            findings.append(
                Finding(
                    code="AO_NONE",
                    severity="WARN",
                    title="No analysis objects found",
                    detail=f"No YAML files in {self.analysis_objects_dir.as_posix()}",
                    file=self.analysis_objects_dir.as_posix(),
                    hint="Add at least player_role_fit.yaml to begin.",
                )
            )

        ao_required_total = 0
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
                        hint="Fix YAML syntax for this analysis object.",
                    )
                )
                continue

            required_metrics = _extract_required_metrics_from_ao(ao or {})
            ao_required_total += len(required_metrics)

            missing = [m for m in required_metrics if m not in metric_id_set]
            if missing:
                ao_missing_metric_refs[p.name] = missing

            plot_ids = _extract_plot_ids_from_ao(ao or {})
            ao_plot_ids_total += len(plot_ids)

        if ao_missing_metric_refs:
            # ERROR: AO refers to non-existent registry metric_id
            first_key = next(iter(ao_missing_metric_refs.keys()))
            sample = ao_missing_metric_refs[first_key][:15]
            findings.append(
                Finding(
                    code="AO_REF_UNKNOWN_METRIC",
                    severity="ERROR",
                    title="Analysis Objects reference unknown metric_ids",
                    detail=(
                        f"{len(ao_missing_metric_refs)} AO file(s) reference missing metrics. "
                        f"Example: {first_key} -> {', '.join(sample)}" + (" ..." if len(ao_missing_metric_refs[first_key]) > 15 else "")
                    ),
                    file=self.analysis_objects_dir.as_posix(),
                    hint="Either add these metric_ids to master_registry.yaml or correct AO required_metrics to canonical ids.",
                )
            )

        # 5) Mappings / specs presence (soft)
        mapping_files = _list_yaml_files(self.mappings_dir) if self.mappings_dir.exists() else []
        if not mapping_files:
            findings.append(
                Finding(
                    code="MAP_NONE",
                    severity="INFO",
                    title="No provider mapping files detected",
                    detail=f"No YAML files found under {self.mappings_dir.as_posix()}",
                    file=self.mappings_dir.as_posix(),
                    hint="Add provider_generic_csv.yaml and provider mappings for platforms (FBref/StatsBomb/etc.) when ready.",
                )
            )

        # 6) Summarize
        status = derive_status(findings)
        metric_count = len(metric_ids)
        summary = (
            f"Registry audit complete. metrics={metric_count}, analysis_objects={len(ao_files)}, "
            f"required_metric_refs={ao_required_total}, plots_in_aos={ao_plot_ids_total}. status={status}."
        )

        risks: List[str] = []
        next_actions: List[str] = []

        if status in ("FAIL", "WARN"):
            risks.append("Registry/AO inconsistencies will cause missing_metrics, weak evidence graphs, and unstable narratives.")
            risks.append("Provider mapping gaps will limit CSV/XML portability across data sources.")
        if any(f.code == "AO_REF_UNKNOWN_METRIC" for f in findings):
            next_actions.append("Normalize metric_id vocabulary: fix AO required_metrics to match master_registry.yaml (canonical ids).")
        if any(f.code == "REG_NO_METRICS" for f in findings):
            next_actions.append("Populate master_registry.yaml with at least the core v1.0 metric set used by player_role_fit.")
        if any(f.code == "MAP_NONE" for f in findings):
            next_actions.append("Add provider mapping YAMLs for CSV/XML ingestion (platform → canonical column map).")

        report = AuditReport(
            report_id=rid,
            status=status,
            summary=summary,
            stats={
                "metrics_count": metric_count,
                "analysis_object_count": len(ao_files),
                "ao_required_metric_refs_total": ao_required_total,
                "ao_plot_ids_total": ao_plot_ids_total,
                "mapping_file_count": len(mapping_files),
                "master_registry_location_guess": metrics_loc,
            },
            findings=findings,
            risks=risks,
            next_actions=next_actions,
        )
        return report

    def render_markdown(self, report: AuditReport) -> str:
        lines: List[str] = []
        lines.append(f"# HP Motor Registry Audit تقرير")
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
        lines.append("## Risks")
        if not report.risks:
            lines.append("- (none)")
        else:
            for r in report.risks:
                lines.append(f"- {r}")
        lines.append("")
        lines.append("## Next actions (ordered)")
        if not report.next_actions:
            lines.append("- (none)")
        else:
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