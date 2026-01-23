from __future__ import annotations

from typing import Dict, List

import pandas as pd


class TableFactory:
    def build_evidence_table(self, metric_values: List[dict], evidence_graph: Dict) -> pd.DataFrame:
        # metric_values in run_analysis is list of dicts in return; here accept MetricValue dicts or objects
        rows = []
        for m in metric_values:
            if isinstance(m, dict):
                rows.append(
                    {
                        "metric_id": m.get("metric_id"),
                        "value": m.get("value"),
                        "sample_minutes": m.get("sample_size"),
                        "source": m.get("source", "raw_df"),
                    }
                )
            else:
                rows.append(
                    {
                        "metric_id": getattr(m, "metric_id", None),
                        "value": getattr(m, "value", None),
                        "sample_minutes": getattr(m, "sample_size", None),
                        "source": getattr(m, "source", "raw_df"),
                    }
                )
        df = pd.DataFrame(rows)
        df["confidence"] = (evidence_graph or {}).get("overall_confidence", "medium")
        return df

    def build_role_fit_table(self, role: str, metric_map: Dict[str, float], confidence: str) -> pd.DataFrame:
        # v1 heuristic scoring (replace later with norms/percentiles)
        xt = float(metric_map.get("xt_value", 0.0) or 0.0)
        prog = float(metric_map.get("progressive_carries_90", 0.0) or 0.0)
        lb = float(metric_map.get("line_break_passes_90", 0.0) or 0.0)
        risk = float(metric_map.get("turnover_danger_index", 0.0) or 0.0)

        # crude score: reward xt/prog/lb, penalize risk
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