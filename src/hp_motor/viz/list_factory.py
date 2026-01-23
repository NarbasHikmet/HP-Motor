from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


class ListFactory:
    def mezzala_tasks_pass_fail(self, metric_map: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        v1: Mezzala görev checklisti (basit eşiklerle).
        """
        xt = float(metric_map.get("xt_value", 0.0) or 0.0)
        prog = float(metric_map.get("progressive_carries_90", 0.0) or 0.0)
        lb = float(metric_map.get("line_break_passes_90", 0.0) or 0.0)
        risk = float(metric_map.get("turnover_danger_index", 0.0) or 0.0)

        return [
            {"task": "Değer üretimi (xT)", "pass": xt >= 0.4, "value": xt, "target": ">=0.4"},
            {"task": "İlerletici taşıma", "pass": prog >= 3.5, "value": prog, "target": ">=3.5"},
            {"task": "Hat kırıcı pas", "pass": lb >= 2.5, "value": lb, "target": ">=2.5"},
            {"task": "Top güvenliği", "pass": risk <= 1.0, "value": risk, "target": "<=1.0"},
        ]

    def top_sequences_by_xt_involvement(self, df) -> List[Dict[str, Any]]:
        """
        v1: Eğer df içinde xT varsa en yüksek xT satırlarını listeler.
        """
        if df is None or df.empty or "xT" not in df.columns:
            return []
        x = pd.to_numeric(df["xT"], errors="coerce")
        tmp = df.copy()
        tmp["_xT"] = x
        tmp = tmp.dropna(subset=["_xT"]).sort_values("_xT", ascending=False).head(8)
        rows = []
        for _, r in tmp.iterrows():
            rows.append({"xT": float(r["_xT"]), "x": r.get("x", None), "y": r.get("y", None)})
        return rows

    def top_turnovers_by_danger(self, df) -> List[Dict[str, Any]]:
        if df is None or df.empty or "turnover_danger_90" not in df.columns:
            return []
        x = pd.to_numeric(df["turnover_danger_90"], errors="coerce")
        tmp = df.copy()
        tmp["_td"] = x
        tmp = tmp.dropna(subset=["_td"]).sort_values("_td", ascending=False).head(8)
        rows = []
        for _, r in tmp.iterrows():
            rows.append({"turnover_danger_90": float(r["_td"]), "x": r.get("x", None), "y": r.get("y", None)})
        return rows