from __future__ import annotations

from typing import Dict, List, Any, Optional
import pandas as pd


class TableFactory:
    """
    Tek API:
      - build_evidence_table(metric_values, evidence_graph)
      - build_role_fit_table(role, metric_map, confidence)
      - build_risk_uncertainty_table(missing_metrics, evidence_graph)

    Dossier tabloları:
      - build_dossier_summary_table(...)
      - build_capability_breakdown_table(...)
      - build_missing_assumptions_table(...)
    """

    def build_evidence_table(self, metric_values: List[Any], evidence_graph: Dict) -> pd.DataFrame:
        rows = []
        for m in metric_values or []:
            if isinstance(m, dict):
                rows.append(
                    {
                        "metric_id": m.get("metric_id"),
                        "entity_type": m.get("entity_type"),
                        "entity_id": m.get("entity_id"),
                        "value": m.get("value"),
                        "unit": m.get("unit"),
                        "sample_size": m.get("sample_size"),
                        "source": m.get("source", "raw_df"),
                        "uncertainty": m.get("uncertainty"),
                    }
                )
            else:
                rows.append(
                    {
                        "metric_id": getattr(m, "metric_id", None),
                        "entity_type": getattr(m, "entity_type", None),
                        "entity_id": getattr(m, "entity_id", None),
                        "value": getattr(m, "value", None),
                        "unit": getattr(m, "unit", None),
                        "sample_size": getattr(m, "sample_size", None),
                        "source": getattr(m, "source", "raw_df"),
                        "uncertainty": getattr(m, "uncertainty", None),
                    }
                )

        df = pd.DataFrame(rows)
        df["confidence"] = (evidence_graph or {}).get("overall_confidence", "medium")
        return df

    def build_role_fit_table(self, role: str, metric_map: Dict[str, float], confidence: str) -> pd.DataFrame:
        xt = float(metric_map.get("xt_value", 0.0) or 0.0)
        prog = float(metric_map.get("progressive_carries_90", 0.0) or 0.0)
        lb = float(metric_map.get("line_break_passes_90", 0.0) or 0.0)
        risk = float(metric_map.get("turnover_danger_index", 0.0) or 0.0)

        # v1 heuristic score
        score = (0.4 * xt) + (0.25 * prog) + (0.25 * lb) - (0.3 * risk)

        strengths = []
        risks = []

        if xt >= 0.5:
            strengths.append("xT üretimi yüksek")
        if prog >= 4:
            strengths.append("ilerletici taşıma hacmi iyi")
        if lb >= 3:
            strengths.append("hat kırıcı pas hacmi iyi")
        if risk >= 1.0:
            risks.append("turnover tehlikesi yüksek")

        return pd.DataFrame(
            [
                {
                    "role": role,
                    "fit_score_v1": round(float(score), 3),
                    "strengths": "; ".join(strengths) if strengths else "-",
                    "risks": "; ".join(risks) if risks else "-",
                    "confidence": confidence,
                }
            ]
        )

    def build_risk_uncertainty_table(self, missing_metrics: List[str], evidence_graph: Dict) -> pd.DataFrame:
        conf = (evidence_graph or {}).get("overall_confidence", "medium")
        rows = []
        for m in (missing_metrics or []):
            rows.append({"missing_metric_id": m, "impact": "reduces_confidence", "confidence": conf})
        return pd.DataFrame(rows)

    # -------------------------
    # Dossier tables
    # -------------------------
    def build_dossier_summary_table(
        self,
        entity_id: str,
        role: str,
        regime: str,
        h_score: float,
        confidence: str,
        fit_score: Optional[float],
        headline: str,
    ) -> pd.DataFrame:
        return pd.DataFrame(
            [
                {
                    "entity_id": entity_id,
                    "role": role,
                    "regime": regime,
                    "h_score": round(float(h_score), 3),
                    "confidence": confidence,
                    "fit_score_v1": None if fit_score is None else round(float(fit_score), 3),
                    "headline": headline,
                }
            ]
        )

    def build_capability_breakdown_table(self, capability_rows: List[Dict[str, Any]]) -> pd.DataFrame:
        # Expect list of dicts: {capability_id,label,score,band,drivers}
        return pd.DataFrame(capability_rows)

    def build_missing_assumptions_table(self, missing: List[str], required: List[str]) -> pd.DataFrame:
        rows = []
        miss_required = [m for m in (missing or []) if m in (required or [])]
        for m in (missing or []):
            rows.append(
                {
                    "missing_metric_id": m,
                    "is_required": bool(m in miss_required),
                    "assumption": "neutral_baseline_or_not_inferred",
                    "popper_note": "Eksik veri -> iddia zayıflatıldı (falsifiability korunuyor).",
                }
            )
        return pd.DataFrame(rows)