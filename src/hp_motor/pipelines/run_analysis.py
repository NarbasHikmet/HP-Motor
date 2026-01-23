from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import yaml

from hp_motor.core.cdl_models import MetricValue
from hp_motor.core.evidence_models import EvidenceGraph, EvidenceNode, Hypothesis
from hp_motor.core.provenance import RunProvenance

from hp_motor.viz.renderer import PlotRenderer, RenderContext
from hp_motor.viz.table_factory import TableFactory
from hp_motor.viz.list_factory import ListFactory

from hp_motor.ingest.provider_registry import ProviderRegistry
from hp_motor.mapping.canonical_mapper import CanonicalMapper
from hp_motor.validation.sot_validator import SOTValidator


BASE_DIR = Path(__file__).resolve().parents[1]  # .../src/hp_motor
REG_PATH = BASE_DIR / "registries" / "master_registry.yaml"
AO_DIR = BASE_DIR / "pipelines" / "analysis_objects"
PROVIDER_MAP_PATH = BASE_DIR / "registries" / "mappings" / "provider_generic_csv.yaml"


class SovereignOrchestrator:
    def __init__(self, registry_path: Path = REG_PATH):
        self.registry_path = registry_path
        self.registry = self._load_registry(registry_path)

        # Provider mapping (generic CSV auto-discovery)
        self.provider_registry = ProviderRegistry(PROVIDER_MAP_PATH) if PROVIDER_MAP_PATH.exists() else None
        self.mapper = CanonicalMapper(self.provider_registry) if self.provider_registry else None

        # Renderer/Factories
        self.renderer = PlotRenderer()
        self.tf = TableFactory()
        self.lf = ListFactory()

    def _load_registry(self, path: Path) -> Dict[str, Any]:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data or {}

    def _load_analysis_object(self, analysis_object_id: str) -> Dict[str, Any]:
        p = AO_DIR / f"{analysis_object_id}.yaml"
        if not p.exists():
            raise FileNotFoundError(f"Analysis object not found: {p}")
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}

    def execute(
        self,
        analysis_object_id: str,
        raw_df: pd.DataFrame,
        entity_id: str,
        role: Optional[str] = None,
        phase: str = "ACTION_GENERIC",
        source: str = "raw_df",
    ) -> Dict[str, Any]:
        """
        Contract output:
          status, metrics, evidence_graph, deliverables, tables, lists, figure_objects (optional)
        Added:
          data_quality, mapping_report
        """

        # ---------- Analysis object load
        ao = self._load_analysis_object(analysis_object_id)

        # ---------- Mapping (rename columns -> canonical keys)
        mapping_report = {"ok": True, "provider_id": None, "mapping_hits": [], "rename_map": {}, "missing_required": []}
        df = raw_df
        if self.mapper is not None:
            df, mapping_report = self.mapper.map_df(raw_df, rename=True)

        # ---------- SOT validation gate
        required_cols = []
        # analysis object might declare required columns (optional)
        if isinstance(ao.get("input_contract"), dict):
            required_cols = ao["input_contract"].get("required_columns", []) or []

        # also require entity column if present in dataset conventions
        if "player_id" in df.columns:
            required_cols = list(set(required_cols + ["player_id"]))

        validator = SOTValidator(required_columns=required_cols, allow_empty=False)
        dq = validator.validate(df)

        if not dq.get("ok", False):
            return {
                "status": "BLOCKED",
                "analysis_object_id": analysis_object_id,
                "entity_id": entity_id,
                "role": role,
                "phase": phase,
                "data_quality": dq,
                "mapping_report": mapping_report,
                "metrics": [],
                "missing_metrics": [],
                "evidence_graph": {},
                "deliverables": {},
                "tables": {},
                "lists": {},
                "figure_objects": {},
            }

        # ---------- Metric computation (v1: simple column read + passthrough)
        col_map = (ao.get("input", {}) or {}).get("col_map", {}) or {}
        metric_values: List[MetricValue] = []
        missing: List[str] = []

        def _get_col(name: str) -> Optional[str]:
            # allow col_map aliasing: canonical_metric -> input column
            return col_map.get(name, name)

        # Example metric ids expected by current AO/renderer
        expected_metrics = (ao.get("deliverables", {}) or {}).get("required_metrics", []) or []
        if not expected_metrics:
            # fallback: minimal set used by plots/tables in your v1.0
            expected_metrics = ["xt_value", "ppda", "progressive_carries_90", "line_break_passes_90", "half_space_receives_90", "turnover_danger_index"]

        for mid in expected_metrics:
            src_col = _get_col(mid)

            if src_col in df.columns:
                series = pd.to_numeric(df[src_col], errors="coerce")
                val = float(series.mean(skipna=True)) if series.notna().any() else None
            else:
                val = None

            if val is None:
                missing.append(mid)
                continue

            metric_values.append(
                MetricValue(
                    metric_id=mid,
                    entity_type="player",
                    entity_id=str(entity_id),
                    value=float(val),
                    unit=None,
                    scope=phase,
                    sample_size=int(df["minutes"].sum()) if "minutes" in df.columns else None,
                )
            )

        # ---------- Evidence graph (Popper-lite v1)
        eg = EvidenceGraph(
            hypotheses=[
                Hypothesis(
                    hypothesis_id="H1",
                    claim=f"{role or 'Player'} role fit under {phase} constraints.",
                    scope={"phase": phase, "role": role, "entity_id": entity_id},
                    falsifiers=[f"missing_metric:{m}" for m in missing],
                )
            ],
            nodes=[
                EvidenceNode(
                    node_id=f"M::{m.metric_id}",
                    axis="metrics",
                    ref={"metric_id": m.metric_id, "value": m.value},
                    strength=0.55,
                    note="Observed metric value",
                )
                for m in metric_values
            ],
            contradictions=[],
            overall_confidence="low" if len(missing) > 2 else "medium",
        )

        # ---------- Renderables
        metric_map = {m.metric_id: m.value for m in metric_values}
        sample_minutes = next((m.sample_size for m in metric_values if getattr(m, "sample_size", None) is not None), None)

        ctx = RenderContext(
            theme=self.renderer.theme,
            sample_minutes=sample_minutes,
            source=source,
            uncertainty=None,
        )

        figures: Dict[str, Any] = {}
        deliver = ao.get("deliverables", {}) or {}
        plot_ids = (deliver.get("plots") or []) if isinstance(deliver.get("plots"), list) else []

        for pid in plot_ids:
            if pid == "risk_scatter":
                spec = {"plot_id": pid, "type": "scatter", "axes": {"x": "xt_value", "y": "turnover_danger_index"}}
            elif pid == "role_radar":
                spec = {
                    "plot_id": pid,
                    "type": "radar",
                    "required_metrics": ["xt_value", "progressive_carries_90", "line_break_passes_90", "turnover_danger_index"],
                }
            elif pid == "half_space_touchmap":
                spec = {"plot_id": pid, "type": "pitch_heatmap"}
            elif pid == "xt_zone_overlay":
                spec = {"plot_id": pid, "type": "pitch_overlay"}
            else:
                continue

            figures[pid] = self.renderer.render(spec, df, metric_map, ctx)

        tables = {
            "evidence_table": self.tf.build_evidence_table(metric_values),
            "role_fit_table": self.tf.build_role_fit_table(
                role=role,
                fit_score=None,
                strengths=[],
                risks=[],
                confidence=eg.overall_confidence,
            ),
            "risk_uncertainty_table": self.tf.build_risk_uncertainty_table(eg, missing),
        }

        lists = {
            "role_tasks_checklist": self.lf.mezzala_tasks_pass_fail(metric_map),
            "top_sequences": self.lf.top_sequences_by_xt_involvement(df),
            "top_turnovers": self.lf.top_turnovers_by_danger(df),
        }

        prov = RunProvenance(
            run_id="run_v1",
            analysis_object_id=analysis_object_id,
            entity_id=str(entity_id),
            notes={"role": role, "phase": phase},
        )

        return {
            "status": "OK",
            "analysis_object_id": analysis_object_id,
            "entity_id": str(entity_id),
            "role": role,
            "phase": phase,
            "provenance": prov.model_dump(),
            "data_quality": dq,
            "mapping_report": mapping_report,
            "missing_metrics": missing,
            "metrics": [m.model_dump() for m in metric_values],
            "evidence_graph": eg.model_dump(),
            "deliverables": deliver,
            "tables": {k: v.to_dict(orient="records") for k, v in tables.items()},
            "lists": lists,
            # Streamlit'de fig objelerini doğrudan kullanmak için
            "figure_objects": figures,
            "figures": list(figures.keys()),
        }