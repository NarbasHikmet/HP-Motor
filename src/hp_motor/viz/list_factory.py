from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


class ListFactory:
    """
    v1.0 lists are rule-based and opportunistic:
    - if columns exist → produce list
    - else → return empty with reason
    """

    def top_sequences_by_xt_involvement(self, df: pd.DataFrame, top_n: int = 10) -> List[Dict[str, Any]]:
        # Expect columns: sequence_id, xT_gain, player_involved (optional)
        required = {"sequence_id", "xT_gain"}
        if not required.issubset(df.columns):
            return []

        sdf = df.sort_values("xT_gain", ascending=False).head(top_n)
        out = []
        for _, r in sdf.iterrows():
            out.append({
                "sequence_id": r["sequence_id"],
                "xT_gain": float(r["xT_gain"]),
                "note": r.get("note", None),
            })
        return out

    def top_turnovers_by_danger(self, df: pd.DataFrame, top_n: int = 10) -> List[Dict[str, Any]]:
        # Expect columns: turnover_id, turnover_danger
        required = {"turnover_id", "turnover_danger"}
        if not required.issubset(df.columns):
            return []

        sdf = df.sort_values("turnover_danger", ascending=False).head(top_n)
        out = []
        for _, r in sdf.iterrows():
            out.append({
                "turnover_id": r["turnover_id"],
                "turnover_danger": float(r["turnover_danger"]),
                "x": float(r["x"]) if "x" in sdf.columns else None,
                "y": float(r["y"]) if "y" in sdf.columns else None,
            })
        return out

    def mezzala_tasks_pass_fail(self, metrics: Dict[str, float]) -> List[Dict[str, Any]]:
        # v1.0 heuristic checklist
        tasks = [
            ("Half-space involvement", "half_space_receives", 5.0),
            ("Progression carrying", "progressive_carries_90", 3.0),
            ("Line-breaking passing", "line_break_passes_90", 3.0),
        ]
        out = []
        for name, mid, thr in tasks:
            v = metrics.get(mid)
            out.append({
                "task": name,
                "metric": mid,
                "value": v,
                "pass": (v is not None and v >= thr),
                "threshold": thr,
            })
        return out