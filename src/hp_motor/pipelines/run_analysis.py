from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
import pandas as pd

from hp_motor.core.cdl_models import MetricValue
from hp_motor.core.evidence_models import EvidenceGraph, EvidenceNode, Hypothesis
from hp_motor.core.provenance import RunProvenance

from hp_motor.viz.renderer import PlotRenderer, RenderContext
from hp_motor.viz.table_factory import TableFactory
from hp_motor.viz.list_factory import ListFactory


# ---- FIXED: REG_PATH DEFINED
REG_PATH = Path(__file__).resolve().parents[1] / "registries" / "master_registry.yaml"
ANALYSIS_DIR = Path(__file__).resolve().parent / "analysis_objects"


class SovereignOrchestrator:
    def __init__(self, registry_path: Path = REG_PATH):
        with registry_path.open("r", encoding="utf-8") as f:
            self.registry = yaml.safe_load(f)["registry"]

    def _load_analysis_object(self, analysis_object_id: str) -> Dict[str, Any]:
        path = ANALYSIS_DIR / f"{analysis_object_id}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Analysis object not found: {path}")
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f)["analysis"]

    def execute(
        self,
        analysis_object_id: str,
        raw_df: pd.DataFrame,
        entity_id: str,
        role: str = "Mezzala",
    ) -> Dict[str, Any]:

        ao = self._load_analysis_object(analysis_object_id)

        prov = RunProvenance(
            run_id=f"run_{analysis_object_id}_{entity_id}",
            registry_version=self.registry.get("version", "unknown"),
        )

        # ---- METRICS
        metric_values: List[MetricValue] = []
        missing: List[str] = []

        for mid in ao.get("metric_bundle", []):
            mv = self._compute_metric(mid, raw_df, entity_id)
            if mv is None:
                missing.append(mid)
            else:
                metric_values.append(mv)

        if len(metric_values) < 2:
            return {
                "status": "UNKNOWN",
                "reason": "Insufficient metrics",
                "missing_metrics": missing,
            }

        # ---- EVIDENCE
        eg = self._build_evidence_graph(metric_values, role)

        # ---- RENDER
        metric_map = {m.metric_id: m.value for m in metric_values}
        sample_minutes = next(
            (m.sample_size for m in metric_values if m.sample_size is not None),
            None,
        )

        renderer = PlotRenderer()
        ctx = RenderContext(
            theme=renderer.theme,
            sample_minutes=sample_minutes,
            source="raw_df",
            uncertainty=None,
        )

        figures: Dict[str, Any] = {}
        for pid in ao.get("deliverables", {}).get("plots", []):
            if pid == "risk_scatter":
                spec = {
                    "plot_id": pid,
                    "type": "scatter",
                    "axes": {"x": "xt_value", "y": "turnover_danger_index"},
                }
            elif pid == "role_radar":
                spec = {
                    "plot_id": pid,
                    "type": "radar",
                    "required_metrics": [
                        "xt_value",
                        "progressive_carries_90",
                        "line_break_passes_90",
                        "turnover_danger_index",
                    ],
                }
            elif pid == "half_space_touchmap":
                spec = {"plot_id": pid, "type": "pitch_heatmap"}
            elif pid == "xt_zone_overlay":
                spec = {"plot_id": pid, "type": "pitch_overlay"}
            else:
                continue

            figures[pid] = renderer.render(spec, raw_df, metric_map, ctx)

        # ---- TABLES
        tf = TableFactory()
        tables = {
            "evidence_table": tf.build_evidence_table(metric_values),
            "role_fit_table": tf.build_role_fit_table(
                role=role,
                fit_score=None,
                strengths=[],
                risks=[],
                confidence=eg.overall_confidence,
            ),
            "risk_uncertainty_table": tf.build_risk_uncertainty_table(eg, missing),
        }

        # ---- LISTS
        lf = ListFactory()
        lists = {
            "role_tasks_checklist": lf.mezzala_tasks_pass_fail(metric_map),
            "top_sequences": lf.top_sequences_by_xt_involvement(raw_df),
            "top_turnovers": lf.top_turnovers_by_danger(raw_df),
        }

        return {
            "status": "OK",
            "metrics": [m.model_dump() for m in metric_values],
            "evidence_graph": eg.model_dump(),
            "figure_objects": figures,
            "tables": {k: v.to_dict(orient="records") for k, v in tables.items()},
            "lists": lists,
            "provenance": prov.__dict__,
        }

    def _compute_metric(
        self, metric_id: str, df: pd.DataFrame, entity_id: str
    ) -> Optional[MetricValue]:

        col_map = {
            "ppda": "ppda",
            "xt_value": "xT",
            "progressive_carries_90": "prog_carries_90",
            "line_break_passes_90": "line_break_passes_90",
            "half_space_receives": "half_space_receives_90",
            "turnover_danger_index": "turnover_danger_90",
        }

        col = col_map.get(metric_id)
        if col not in df.columns:
            return None

        sdf = df[df["player_id"] == entity_id] if "player_id" in df.columns else df
        if sdf.empty:
            return None

        return MetricValue(
            metric_id=metric_id,
            entity_type="player",
            entity_id=entity_id,
            value=float(sdf[col].mean()),
            sample_size=float(sdf["minutes"].sum()) if "minutes" in sdf.columns else None,
            source="raw_df",
        )

    def _build_evidence_graph(
        self, metrics: List[MetricValue], role: str
    ) -> EvidenceGraph:

        h = Hypothesis(
            hypothesis_id="H1",
            claim=f"{role} rol uyumu yüksek",
            falsifiers=["xt_value low", "turnover_danger_index high"],
        )

        nodes = [
            EvidenceNode(
                node_id=f"N{i}",
                axis="metrics",
                ref={"metric_id": m.metric_id, "value": m.value},
                strength=0.6,
            )
            for i, m in enumerate(metrics, 1)
        ]

        return EvidenceGraph(
            hypotheses=[h],
            nodes=nodes,
            contradictions=[],
            overall_confidence="medium",
        )