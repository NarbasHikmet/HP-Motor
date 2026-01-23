from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, List, Optional
import os
import yaml
import pandas as pd

from hp_motor.core.cdl_models import MetricValue
from hp_motor.core.cognition import extract_cognitive_signals, extract_orientation_signals
from hp_motor.viz.renderer import PlotRenderer, RenderContext
from hp_motor.viz.table_factory import TableFactory
from hp_motor.viz.list_factory import ListFactory


class SovereignOrchestrator:
    """
    v1.1: Tek analysis object (player_role_fit) ile:
      - provider mapping (yaml)
      - metric compute (baseline + cognitive + biomechanics)
      - evidence_graph
      - deliverables: tables + lists + figures
    """

    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ao_dir = os.path.join(base_dir, "analysis_objects")

        # src/hp_motor/pipelines -> src/hp_motor/registries/mappings
        hp_motor_dir = os.path.dirname(base_dir)
        self.map_dir = os.path.join(hp_motor_dir, "registries", "mappings")

        self.renderer = PlotRenderer()
        self.tf = TableFactory()
        self.lf = ListFactory()

    def execute(
        self,
        analysis_object_id: str,
        raw_df: pd.DataFrame,
        entity_id: str = "entity",
        role: str = "Mezzala",
        phase: str = "ACTION_GENERIC",
        provider_hint: Optional[str] = None,
    ) -> Dict[str, Any]:

        ao = self._load_analysis_object(analysis_object_id)

        provider = provider_hint or self._choose_provider(raw_df)
        col_map = self._load_mapping(provider)

        canonical_df, mapping_report = self._apply_mapping(raw_df, provider, col_map)

        metric_values, missing = self._compute_player_role_fit_metrics(
            canonical_df,
            entity_id=str(entity_id),
            role=role,
        )

        evidence_graph = self._build_evidence_graph(metric_values, missing, ao)

        # ---- Renderables
        metric_map = {m.metric_id: m.value for m in metric_values}
        sample_minutes = next((m.sample_size for m in metric_values if m.sample_size is not None), None)

        ctx = RenderContext(
            theme=self.renderer.theme,
            sample_minutes=sample_minutes,
            source=provider,
            uncertainty=None,
        )

        figures: Dict[str, Any] = {}
        for pid in ao.get("deliverables", {}).get("plots", []):
            spec = self._minimal_plot_spec(pid)
            if spec is None:
                continue
            figures[pid] = self.renderer.render(spec, canonical_df, metric_map, ctx)

        # Tables (always attempt)
        tables = {
            "evidence_table": self.tf.build_evidence_table(metric_values, evidence_graph),
            "role_fit_table": self.tf.build_role_fit_table(
                role=role,
                metric_map=metric_map,
                confidence=evidence_graph.get("overall_confidence", "medium"),
            ),
            "risk_uncertainty_table": self.tf.build_risk_uncertainty_table(missing, evidence_graph),
        }

        # Lists (always attempt)
        lists = {
            "role_tasks_checklist": self.lf.mezzala_tasks_pass_fail(metric_map),
            "top_sequences": self.lf.top_sequences_by_xt_involvement(canonical_df),
            "top_turnovers": self.lf.top_turnovers_by_danger(canonical_df),
        }

        return {
            "status": "OK",
            "analysis_object_id": analysis_object_id,
            "analysis_id": ao.get("analysis", {}).get("analysis_id", analysis_object_id),
            "phase": phase,
            "provider": provider,
            "mapping_report": mapping_report,
            "missing_metrics": missing,
            "metrics": [m.model_dump() if hasattr(m, "model_dump") else asdict(m) for m in metric_values],
            "evidence_graph": evidence_graph,
            "deliverables": ao.get("deliverables", {}),
            # Streamlit runtime objects (fig) — JSON'a çevirmiyoruz
            "figures": list(figures.keys()),
            "figure_objects": figures,
            # DataFrames -> records
            "tables": {k: v.to_dict(orient="records") for k, v in tables.items()},
            "lists": lists,
        }

    # -------------------------
    # AO & mapping
    # -------------------------
    def _load_analysis_object(self, analysis_object_id: str) -> Dict[str, Any]:
        path = os.path.join(self.ao_dir, f"{analysis_object_id}.yaml")
        if not os.path.exists(path):
            raise FileNotFoundError(f"analysis_object not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def _choose_provider(self, df: pd.DataFrame) -> str:
        # v1 heuristic: app.py ileride provider seçtirebilir
        return "generic_csv"

    def _load_mapping(self, provider: str) -> Dict[str, str]:
        path = os.path.join(self.map_dir, f"provider_{provider}.yaml")
        if not os.path.exists(path):
            return {}
        with open(path, "r", encoding="utf-8") as f:
            y = yaml.safe_load(f) or {}
        return y.get("columns", {}) or {}

    def _apply_mapping(self, df: pd.DataFrame, provider: str, col_map: Dict[str, str]):
        if not col_map:
            return df.copy(), {"provider": "identity", "mapped": 0, "warnings": []}

        out = df.copy()
        mapped = 0
        warnings = []

        for src, canon in col_map.items():
            if src in out.columns and canon not in out.columns:
                out.rename(columns={src: canon}, inplace=True)
                mapped += 1

        for canon_need in ["player_id", "minutes"]:
            if canon_need not in out.columns:
                warnings.append(f"Missing canonical column: {canon_need}")

        return out, {"provider": provider, "mapped": mapped, "warnings": warnings}

    # -------------------------
    # Metric compute
    # -------------------------
    def _safe_mean(self, df: pd.DataFrame, col: str) -> Optional[float]:
        if col not in df.columns:
            return None
        s = pd.to_numeric(df[col], errors="coerce")
        if s.notna().sum() == 0:
            return None
        return float(s.mean())

    def _compute_player_role_fit_metrics(self, df: pd.DataFrame, entity_id: str, role: str):
        missing: List[str] = []
        out: List[MetricValue] = []

        df_e = df.copy()
        if "player_id" in df.columns:
            tmp = df[df["player_id"].astype(str) == str(entity_id)].copy()
            if not tmp.empty:
                df_e = tmp

        minutes = self._safe_mean(df_e, "minutes")

        xt = self._safe_mean(df_e, "xt_value")
        ppda = self._safe_mean(df_e, "ppda")
        prog = self._safe_mean(df_e, "progressive_carries_90")
        lbreak = self._safe_mean(df_e, "line_break_passes_90")
        hs = self._safe_mean(df_e, "half_space_receives")
        tdi = self._safe_mean(df_e, "turnover_danger_index")

        def add(metric_id: str, value: Optional[float], unit: Optional[str] = None, source: str = "raw_df"):
            if value is None:
                missing.append(metric_id)
                return
            out.append(
                MetricValue(
                    metric_id=metric_id,
                    entity_type="player",
                    entity_id=str(entity_id),
                    value=float(value),
                    unit=unit,
                    sample_size=minutes,
                    source=source,
                )
            )

        # Core bundle (AO required_metrics ile uyumlu)
        add("xt_value", xt)
        add("ppda", ppda)
        add("turnover_danger_index", tdi)
        add("progressive_carries_90", prog)
        add("line_break_passes_90", lbreak)
        add("half_space_receives", hs)

        # Cognitive / Orientation (varsa)
        cog = extract_cognitive_signals(df_e)
        add("decision_speed_mean_s", cog.decision_speed_mean_s, unit="s")
        add("scan_freq_10s", cog.scan_freq_10s, unit="per_s")
        add("contextual_awareness_score", cog.contextual_awareness_score, unit="0_1")

        ori = extract_orientation_signals(df_e)
        add("defender_side_on_score", ori.defender_side_on_score, unit="0_1")
        add("square_on_rate", ori.square_on_rate, unit="0_1")
        add("channeling_to_wing_rate", ori.channeling_to_wing_rate, unit="0_1")

        # v1: benchmark stub (AO required, o yüzden “missing”e düşmesin diye 0.0 ile dolduruyoruz)
        out.append(
            MetricValue(
                metric_id="role_benchmark_percentiles",
                entity_type="player",
                entity_id=str(entity_id),
                value=0.0,
                unit="stub",
                sample_size=minutes,
                source="engine",
            )
        )

        missing = sorted(list(set(missing)))
        return out, missing

    def _build_evidence_graph(self, metric_values: List[MetricValue], missing: List[str], ao: Dict[str, Any]) -> Dict[str, Any]:
        required = ao.get("deliverables", {}).get("required_metrics", []) or []
        missing_required = [m for m in missing if m in required]

        if len(required) == 0:
            overall = "medium"
        elif len(missing_required) == 0:
            overall = "high"
        elif len(missing_required) <= max(1, len(required) // 3):
            overall = "medium"
        else:
            overall = "low"

        return {
            "overall_confidence": overall,
            "missing_required": missing_required,
            "nodes": [{"metric_id": m.metric_id, "value": m.value} for m in metric_values],
            "edges": [],
        }

    # -------------------------
    # Minimal plot specs (v1)
    # -------------------------
    def _minimal_plot_spec(self, pid: str) -> Optional[Dict[str, Any]]:
        if pid == "risk_scatter":
            return {"plot_id": pid, "type": "scatter", "axes": {"x": "xt_value", "y": "turnover_danger_index"}}
        if pid == "role_radar":
            return {
                "plot_id": pid,
                "type": "radar",
                "required_metrics": [
                    "xt_value",
                    "progressive_carries_90",
                    "line_break_passes_90",
                    "turnover_danger_index",
                    "contextual_awareness_score",
                ],
            }
        if pid == "half_space_touchmap":
            return {"plot_id": pid, "type": "pitch_heatmap"}
        if pid == "xt_zone_overlay":
            return {"plot_id": pid, "type": "pitch_overlay"}
        return None