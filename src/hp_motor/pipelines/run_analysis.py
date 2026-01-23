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


REG_PATH = Path(__file__).resolve().parents[1] / "registries" / "master_registry.yaml"
ANALYSIS_DIR = Path(__file__).resolve().parent / "analysis_objects"


class SovereignOrchestrator:
    """
    v1.0 Orchestrator:
      - Loads Analysis Object YAML
      - Computes metric_bundle (minimal column mapping)
      - Builds EvidenceGraph (minimal)
      - Renders figures (matplotlib/mplsoccer)
      - Builds tables (pandas)
      - Builds lists (python list[dict])
    """

    def __init__(self, registry_path: Path = REG_PATH):
        with registry_path.open("r", encoding="utf-8") as f:
            self.registry = yaml.safe_load(f)["registry"]

    def _load_analysis_object(self, analysis_object_id: str) -> Dict[str, Any]:
        """
        analysis_object_id: file stem under analysis_objects/
          example: "player_role_fit" => analysis_objects/player_role_fit.yaml
        """
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
        phase: str = "ACTION_GENERIC",
    ) -> Dict[str, Any]:
        ao = self._load_analysis_object(analysis_object_id)

        prov = RunProvenance(
            run_id=f"run_{analysis_object_id}_{entity_id}",
            registry_version=self.registry.get("version", "unknown"),
        )

        # 1) Metrics
        metric_values: List[MetricValue] = []
        missing: List[str] = []

        metric_bundle = ao.get("metric_bundle", [])
        for mid in metric_bundle:
            mv = self._compute_metric(mid, raw_df, entity_id)
            if mv is None:
                missing.append(mid)
            else:
                metric_values.append(mv)

        # Fail-closed minimal
        if ao.get("evidence_policy", {}).get("fail_closed", True) and len(metric_values) < 2:
            return {
                "status": "UNKNOWN",
                "reason": "Insufficient metrics to satisfy minimal evidence policy.",
                "missing_metrics": missing,
                "analysis_object": ao,
            }

        # 2) Evidence Graph (v1.0 minimal)
        eg = self._build_evidence_graph(metric_values, role)

        # 3) Renderables (Figures / Tables / Lists)
        metric_map = {m.metric_id: m.value for m in metric_values}
        sample_minutes = next((m.sample_size for m in metric_values if m.sample_size is not None), None)

        renderer = PlotRenderer()
        ctx = RenderContext(
            theme=renderer.theme,
            sample_minutes=sample_minutes,
            source="raw_df",
            uncertainty=None,
        )

        figures: Dict[str, Any] = {}
        for pid in ao.get("deliverables", {}).get("plots", []):
            # v1.0: plot specs inline (v1.1: spec loader)
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
                # unknown plot id -> skip
                continue

            figures[pid] = renderer.render(spec, raw_df, metric_map, ctx)

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

        lf = ListFactory()
        lists = {
            "role_tasks_checklist": lf.mezzala_tasks_pass_fail(metric_map),
            "top_sequences": lf.top_sequences_by_xt_involvement(raw_df),
            "top_turnovers": lf.top_turnovers_by_danger(raw_df),
        }

        # IMPORTANT:
        # - For Streamlit, returning the figure objects is useful (st.pyplot(fig)).
        # - For API/JSON, you can store figure keys only; here we return BOTH.
        return {
            "status": "OK",
            "analysis_object": ao,
            "metrics": [m.model_dump() for m in metric_values],
            "missing_metrics": missing,
            "evidence_graph": eg.model_dump(),
            "deliverables": ao.get("deliverables", {}),
            "provenance": prov.__dict__,
            # Renderables
            "figure_objects": figures,  # Streamlit can use these directly
            "figures": list(figures.keys()),  # easy logging
            "tables": {k: v.to_dict(orient="records") for k, v in tables.items()},
            "lists": lists,
        }

    def _compute_metric(self, metric_id: str, df: pd.DataFrame, entity_id: str) -> Optional[MetricValue]:
        """
        v1.0 minimal column mapping. You can adapt col_map to your real CSV schema.
        """
        col_map = {
            "ppda": "ppda",
            "xt_value": "xT",
            "progressive_carries_90": "prog_carries_90",
            "line_break_passes_90": "line_break_passes_90",
            "half_space_receives": "half_space_receives_90",
            "turnover_danger_index": "turnover_danger_90",
            "role_benchmark_percentiles": None,  # v1.1 norms
        }

        col = col_map.get(metric_id, None)
        if col is None:
            return None
        if col not in df.columns:
            return None

        # Filter for entity if player_id exists
        if "player_id" in df.columns:
            sdf = df[df["player_id"] == entity_id]
        else:
            sdf = df

        if sdf.empty:
            return None

        value = float(sdf[col].mean())
        sample_minutes = float(sdf["minutes"].sum()) if "minutes" in sdf.columns else None

        return MetricValue(
            metric_id=metric_id,
            entity_type="player",
            entity_id=entity_id,
            value=value,
            unit=None,
            scope="open_play",
            sample_size=sample_minutes,
            source="raw_df",
            uncertainty=None,
        )

    def _build_evidence_graph(self, metrics: List[MetricValue], role: str) -> EvidenceGraph:
        """
        v1.0 minimal evidence: 1 hypothesis + metric nodes.
        """
        h1 = Hypothesis(
            hypothesis_id="H1_role_fit",
            claim=f"{role} rol uyumu yüksek.",
            falsifiers=[
                "xt_value low",
                "turnover_danger_index high",
            ],
        )

        nodes: List[EvidenceNode] = []
        for i, mv in enumerate(metrics):
            nodes.append(
                EvidenceNode(
                    node_id=f"N{i+1}",
                    axis="metrics",
                    ref={"metric_id": mv.metric_id, "value": mv.value},
                    strength=0.6,
                    note=None,
                )
            )

        return EvidenceGraph(
            hypotheses=[h1],
            nodes=nodes,
            contradictions=[],
            overall_confidence="medium",
        )