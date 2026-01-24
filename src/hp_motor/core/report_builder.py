from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
import matplotlib.pyplot as plt

from hp_motor.viz.table_factory import TableFactory
from hp_motor.viz.list_factory import ListFactory


class ReportBuilder:
    """
    Artifact builder (tables / lists / figures).

    Contract:
      - Always returns keys: tables, lists, figure_objects, evidence_graph, diagnostics.
      - Tables are pandas.DataFrame.
      - Figures are matplotlib Figure objects.
      - If insufficient data: build_abstained_output provides coverage + diagnostics.
    """

    def __init__(self, registry: Optional[Dict[str, Any]] = None) -> None:
        self.registry = registry or {}
        self.table_factory = TableFactory()
        self.list_factory = ListFactory()

    def build_abstained_output(
        self,
        analysis_object_id: str,
        entity_id: str,
        role: str,
        phase: str,
        reason: str,
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        diagnostics = diagnostics or {}
        df = diagnostics.get("df")
        tables: Dict[str, pd.DataFrame] = {}

        if isinstance(df, pd.DataFrame):
            tables["data_coverage"] = self._build_data_coverage_table(df)
        else:
            tables["data_coverage"] = pd.DataFrame([{"note": "no_df_available"}])

        evidence_graph = {
            "overall_confidence": "low",
            "hypotheses": [
                {
                    "id": "H_ABSTAIN",
                    "claim": "System abstained due to insufficient or invalid input.",
                    "confidence": "low",
                    "supporting": [],
                    "contradicting": [],
                    "notes": reason,
                }
            ],
        }

        return {
            "status": "ABSTAINED",
            "analysis_object_id": analysis_object_id,
            "entity_id": entity_id,
            "role": role,
            "phase": phase,
            "metrics": [],
            "missing_metrics": diagnostics.get("missing_metrics", []),
            "tables": tables,
            "lists": {"abstain_reason": [{"reason": reason}]},
            "figure_objects": {},
            "evidence_graph": evidence_graph,
            "diagnostics": diagnostics,
        }

    def build(
        self,
        df: pd.DataFrame,
        role: str,
        metrics: List[Dict[str, Any]],
        missing_metrics: List[str],
        evidence_graph: Dict[str, Any],
        diagnostics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        diagnostics = diagnostics or {}

        metric_map = self._metric_list_to_map(metrics)

        tables: Dict[str, pd.DataFrame] = {}
        lists: Dict[str, Any] = {}
        figures: Dict[str, Any] = {}

        # --- Tables
        tables["data_coverage"] = self._build_data_coverage_table(df)
        tables["evidence"] = self.table_factory.build_evidence_table(metrics, evidence_graph)
        tables["risk_uncertainty"] = self.table_factory.build_risk_uncertainty_table(missing_metrics, evidence_graph)

        # Role-fit table expects some known metric ids; fallbacks -> 0 but OK because it's a role-fit heuristic, not claimed fact.
        # Important: do NOT fabricate ppda/xg; those are handled upstream (missing if absent).
        tables["role_fit_v1"] = self.table_factory.build_role_fit_table(
            role=role,
            metric_map=metric_map,
            confidence=(evidence_graph or {}).get("overall_confidence", "medium"),
        )

        # --- Lists
        lists["strengths"] = self.list_factory.strengths_list(metric_map)
        lists["risks"] = self.list_factory.risks_list(metric_map)
        lists["watchlist"] = self.list_factory.watchlist_prompts(role)

        # Role task pass/fail (Mezzala baseline)
        lists["role_tasks"] = self.list_factory.mezzala_tasks_pass_fail(metric_map)

        # Sequences & turnovers if possible
        lists["top_sequences"] = self.list_factory.top_sequences_by_xt_involvement(df)
        lists["top_turnovers"] = self.list_factory.top_turnovers_by_danger(df)

        # --- Figures (minimal, deterministic)
        heatmap_fig = self._build_event_heatmap(df)
        if heatmap_fig is not None:
            figures["event_heatmap_xy"] = heatmap_fig

        return {
            "tables": tables,
            "lists": lists,
            "figure_objects": figures,
            "evidence_graph": evidence_graph,
            "diagnostics": diagnostics,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _metric_list_to_map(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for m in metrics or []:
            if not isinstance(m, dict):
                continue
            mid = m.get("metric_id")
            if mid is None:
                continue
            out[str(mid)] = m.get("value")
        return out

    @staticmethod
    def _build_data_coverage_table(df: pd.DataFrame) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        n = int(len(df))
        for c in df.columns:
            s = df[c]
            null_rate = float(s.isna().mean()) if n > 0 else 1.0
            dtype = str(s.dtype)
            unique = int(s.nunique(dropna=True)) if n > 0 else 0
            sample = None
            try:
                sample = s.dropna().iloc[0]
            except Exception:
                sample = None
            rows.append(
                {
                    "column": str(c),
                    "dtype": dtype,
                    "null_rate": round(null_rate, 4),
                    "unique_non_null": unique,
                    "sample_non_null": sample,
                }
            )
        return pd.DataFrame(rows).sort_values(["null_rate", "column"], ascending=[True, True]).reset_index(drop=True)

    @staticmethod
    def _build_event_heatmap(df: pd.DataFrame) -> Optional[plt.Figure]:
        if df is None or df.empty:
            return None

        # prefer canonical columns
        xcol = "x" if "x" in df.columns else ("pos_x" if "pos_x" in df.columns else None)
        ycol = "y" if "y" in df.columns else ("pos_y" if "pos_y" in df.columns else None)
        if xcol is None or ycol is None:
            return None

        x = pd.to_numeric(df[xcol], errors="coerce")
        y = pd.to_numeric(df[ycol], errors="coerce")
        mask = x.notna() & y.notna()
        if int(mask.sum()) == 0:
            return None

        fig = plt.figure()
        plt.hist2d(x[mask], y[mask], bins=25)
        plt.title("Event Heatmap (x,y)")
        plt.xlabel(xcol)
        plt.ylabel(ycol)
        plt.tight_layout()
        return fig