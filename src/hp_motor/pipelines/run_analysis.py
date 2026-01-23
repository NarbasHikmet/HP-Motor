from __future__ import annotations

from dataclasses import asdict
from typing import Dict, Any, List, Optional
import os
import yaml
import pandas as pd

from hp_motor.core.cdl_models import MetricValue
from hp_motor.core.cognition import extract_cognitive_signals, extract_orientation_signals
from hp_motor.engine.hp_engine_v12 import HPEngineV12
from hp_motor.viz.renderer import PlotRenderer, RenderContext
from hp_motor.viz.table_factory import TableFactory
from hp_motor.viz.list_factory import ListFactory


class SovereignOrchestrator:
    """
    v1.2:
      - player_role_fit
      - player_dossier
    """

    def __init__(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ao_dir = os.path.join(base_dir, "analysis_objects")

        hp_motor_dir = os.path.dirname(base_dir)
        self.map_dir = os.path.join(hp_motor_dir, "registries", "mappings")
        self.cap_path = os.path.join(hp_motor_dir, "registries", "capabilities.yaml")

        self.renderer = PlotRenderer()
        self.tf = TableFactory()
        self.lf = ListFactory()
        self.engine = HPEngineV12()

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

        if analysis_object_id == "player_dossier":
            return self._execute_player_dossier(ao, canonical_df, mapping_report, entity_id, role, phase, provider)

        # default: player_role_fit
        return self._execute_player_role_fit(ao, canonical_df, mapping_report, entity_id, role, phase, provider)

    # -------------------------
    # AO runners
    # -------------------------
    def _execute_player_role_fit(
        self,
        ao: Dict[str, Any],
        df: pd.DataFrame,
        mapping_report: Dict[str, Any],
        entity_id: str,
        role: str,
        phase: str,
        provider: str,
    ) -> Dict[str, Any]:

        metric_values, missing = self._compute_player_role_fit_metrics(df, entity_id=str(entity_id), role=role)
        evidence_graph = self._build_evidence_graph(metric_values, missing, ao)

        metric_map = {m.metric_id: m.value for m in metric_values}
        sample_minutes = next((m.sample_size for m in metric_values if m.sample_size is not None), None)

        ctx = RenderContext(theme=self.renderer.theme, sample_minutes=sample_minutes, source=provider, uncertainty=None)

        figures: Dict[str, Any] = {}
        for pid in ao.get("deliverables", {}).get("plots", []):
            spec = self._minimal_plot_spec(pid)
            if spec is None:
                continue
            figures[pid] = self.renderer.render(spec, df, metric_map, ctx)

        tables = {
            "evidence_table": self.tf.build_evidence_table(metric_values, evidence_graph),
            "role_fit_table": self.tf.build_role_fit_table(
                role=role,
                metric_map=metric_map,
                confidence=evidence_graph.get("overall_confidence", "medium"),
            ),
            "risk_uncertainty_table": self.tf.build_risk_uncertainty_table(missing, evidence_graph),
        }

        lists = {
            "role_tasks_checklist": self.lf.mezzala_tasks_pass_fail(metric_map),
            "top_sequences": self.lf.top_sequences_by_xt_involvement(df),
            "top_turnovers": self.lf.top_turnovers_by_danger(df),
        }

        return {
            "status": "OK",
            "analysis_object_id": "player_role_fit",
            "phase": phase,
            "provider": provider,
            "mapping_report": mapping_report,
            "missing_metrics": missing,
            "metrics": [m.model_dump() if hasattr(m, "model_dump") else asdict(m) for m in metric_values],
            "evidence_graph": evidence_graph,
            "deliverables": ao.get("deliverables", {}),
            "figures": list(figures.keys()),
            "figure_objects": figures,
            "tables": {k: v.to_dict(orient="records") for k, v in tables.items()},
            "lists": lists,
        }

    def _execute_player_dossier(
        self,
        ao: Dict[str, Any],
        df: pd.DataFrame,
        mapping_report: Dict[str, Any],
        entity_id: str,
        role: str,
        phase: str,
        provider: str,
    ) -> Dict[str, Any]:

        # 1) compute same metric bundle
        metric_values, missing = self._compute_player_role_fit_metrics(df, entity_id=str(entity_id), role=role)
        evidence_graph = self._build_evidence_graph(metric_values, missing, ao)
        metric_map = {m.metric_id: m.value for m in metric_values}

        # 2) compute regime (H-score) from events if possible; otherwise light default
        h_score = 0.50
        regime = "MIXED"
        if df is not None and not df.empty and "event_type" in df.columns:
            # run engine on last 50 events (or all if less)
            tail = df.tail(50)
            for _, r in tail.iterrows():
                out = self.engine.process_match_event(r.to_dict())
            formatted = self.engine.format_output(out)
            h_score = float(formatted.get("h_score", 0.50))
            regime = str(formatted.get("regime", "MIXED"))

        confidence = evidence_graph.get("overall_confidence", "medium")

        # 3) capability breakdown
        caps = self._load_capabilities()
        cap_rows = self._score_capabilities(caps, metric_map)

        # 4) fit score (reuse role fit heuristic)
        fit_df = self.tf.build_role_fit_table(role=role, metric_map=metric_map, confidence=confidence)
        fit_score = None
        if not fit_df.empty and "fit_score_v1" in fit_df.columns:
            try:
                fit_score = float(fit_df["fit_score_v1"].iloc[0])
            except Exception:
                fit_score = None

        # 5) headline (v1 deterministic)
        headline = self._headline(role, cap_rows, metric_map, regime)

        # 6) render figures
        sample_minutes = next((m.sample_size for m in metric_values if m.sample_size is not None), None)
        ctx = RenderContext(theme=self.renderer.theme, sample_minutes=sample_minutes, source=provider, uncertainty=None)

        figures: Dict[str, Any] = {}
        for pid in ao.get("deliverables", {}).get("plots", []):
            spec = self._minimal_plot_spec(pid)
            if spec is None:
                continue
            figures[pid] = self.renderer.render(spec, df, metric_map, ctx)

        # 7) tables
        required = ao.get("deliverables", {}).get("required_metrics", []) or []
        tables = {
            "dossier_summary_table": self.tf.build_dossier_summary_table(
                entity_id=str(entity_id),
                role=role,
                regime=regime,
                h_score=h_score,
                confidence=confidence,
                fit_score=fit_score,
                headline=headline,
            ),
            "capability_breakdown_table": self.tf.build_capability_breakdown_table(cap_rows),
            "evidence_table": self.tf.build_evidence_table(metric_values, evidence_graph),
            "missing_and_assumptions_table": self.tf.build_missing_assumptions_table(missing, required),
        }

        # 8) lists
        lists = {
            "role_tasks_checklist": self.lf.mezzala_tasks_pass_fail(metric_map),
            "strengths_list": self.lf.strengths_list(metric_map),
            "risks_list": self.lf.risks_list(metric_map),
            "watchlist_prompts": self.lf.watchlist_prompts(role),
        }

        return {
            "status": "OK",
            "analysis_object_id": "player_dossier",
            "phase": phase,
            "provider": provider,
            "mapping_report": mapping_report,
            "missing_metrics": missing,
            "metrics": [m.model_dump() if hasattr(m, "model_dump") else asdict(m) for m in metric_values],
            "evidence_graph": evidence_graph,
            "deliverables": ao.get("deliverables", {}),
            "figures": list(figures.keys()),
            "figure_objects": figures,
            "tables": {k: v.to_dict(orient="records") for k, v in tables.items()},
            "lists": lists,
            "dossier": {
                "regime": regime,
                "h_score": h_score,
                "headline": headline,
            },
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
    # Metrics
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

        # core (try common aliases)
        xt = self._safe_mean(df_e, "xt_value")
        if xt is None and "xT" in df_e.columns:
            xt = self._safe_mean(df_e, "xT")

        ppda = self._safe_mean(df_e, "ppda")
        prog = self._safe_mean(df_e, "progressive_carries_90")
        if prog is None and "prog_carries_90" in df_e.columns:
            prog = self._safe_mean(df_e, "prog_carries_90")

        lbreak = self._safe_mean(df_e, "line_break_passes_90")
        hs = self._safe_mean(df_e, "half_space_receives")
        tdi = self._safe_mean(df_e, "turnover_danger_index")
        if tdi is None and "turnover_danger_90" in df_e.columns:
            tdi = self._safe_mean(df_e, "turnover_danger_90")

        add("xt_value", xt)
        add("ppda", ppda)
        add("turnover_danger_index", tdi)
        add("progressive_carries_90", prog)
        add("line_break_passes_90", lbreak)
        add("half_space_receives", hs)

        # cognitive / orientation (if extractors can infer)
        cog = extract_cognitive_signals(df_e)
        add("decision_speed_mean_s", getattr(cog, "decision_speed_mean_s", None), unit="s")
        add("scan_freq_10s", getattr(cog, "scan_freq_10s", None), unit="per_s")
        add("contextual_awareness_score", getattr(cog, "contextual_awareness_score", None), unit="0_1")

        ori = extract_orientation_signals(df_e)
        add("defender_side_on_score", getattr(ori, "defender_side_on_score", None), unit="0_1")
        add("square_on_rate", getattr(ori, "square_on_rate", None), unit="0_1")
        add("channeling_to_wing_rate", getattr(ori, "channeling_to_wing_rate", None), unit="0_1")

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
    # Capabilities
    # -------------------------
    def _load_capabilities(self) -> Dict[str, Any]:
        if not os.path.exists(self.cap_path):
            return {"capabilities": {}}
        with open(self.cap_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {"capabilities": {}}

    def _score_capabilities(self, caps_doc: Dict[str, Any], metric_map: Dict[str, float]) -> List[Dict[str, Any]]:
        caps = (caps_doc or {}).get("capabilities", {}) or {}
        rows = []

        for cap_id, spec in caps.items():
            label = spec.get("label", cap_id)
            weights: Dict[str, float] = spec.get("metrics", {}) or {}

            score = 0.0
            drivers = []
            for mid, w in weights.items():
                val = metric_map.get(mid, None)
                if val is None:
                    continue
                score += float(w) * float(val)
                drivers.append(f"{mid}({w:+.2f})={float(val):.2f}")

            # v1 banding (no norms)
            band = "Neutral"
            if score >= 0.75:
                band = "Strong"
            elif score <= -0.50:
                band = "Risk"

            rows.append(
                {
                    "capability_id": cap_id,
                    "label": label,
                    "score_v1": round(float(score), 3),
                    "band": band,
                    "drivers": "; ".join(drivers) if drivers else "no_drivers(v1)",
                }
            )

        # sort by absolute magnitude
        rows.sort(key=lambda r: abs(r.get("score_v1", 0.0)), reverse=True)
        return rows

    def _headline(self, role: str, cap_rows: List[Dict[str, Any]], metric_map: Dict[str, float], regime: str) -> str:
        # deterministic, terse
        top = cap_rows[0]["label"] if cap_rows else "Profile"
        risk = "yüksek" if float(metric_map.get("turnover_danger_index", 0.0) or 0.0) >= 1.0 else "kontrollü"
        return f"{role} profili: {top} ön planda. Rejim={regime}. Turnover riski {risk}."

    # -------------------------
    # Minimal plot specs
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