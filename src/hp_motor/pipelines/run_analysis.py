from __future__ import annotations

from typing import Any, Dict, Optional

import pandas as pd

from hp_motor.core.evidence_models import EvidenceGraph, Hypothesis, RawArtifact
from hp_motor.core.registry_loader import load_master_registry
from hp_motor.core.scanning import compute_decision_speed


class SovereignOrchestrator:
    """
    v1: Event/Tablo DF alır, minimal metrik seti + evidence_graph üretir.
    v2+: xT, packing, phase-lens, biomech gate vb. buraya genişler.
    """

    def __init__(self) -> None:
        self.registry = load_master_registry()

    def execute_full_analysis(self, artifact: RawArtifact, phase: str) -> Dict[str, Any]:
        """
        Legacy uyumu: app.py eski çağrıları için.
        """
        df = artifact.df if isinstance(artifact, RawArtifact) else artifact
        return self.execute(
            analysis_object_id="player_role_fit",
            raw_df=df,
            entity_id="entity",
            role="Mezzala",
            phase=phase,
        )

    def execute(
        self,
        analysis_object_id: str,
        raw_df: pd.DataFrame,
        entity_id: str,
        role: str,
        phase: str,
        archetype_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # 0) Data quality gate
        if raw_df is None or len(raw_df) == 0:
            return {
                "status": "ABSTAINED",
                "reason": "Empty dataframe",
                "missing_metrics": ["ppda", "xg"],
                "metrics": [],
                "tables": {},
                "lists": {},
                "figure_objects": {},
                "evidence_graph": {"overall_confidence": "low"},
            }

        # 1) Minimal core metrics (şimdilik placeholders + registry defaults)
        metrics_reg = (self.registry or {}).get("metrics", {}) or {}
        ppda_default = float(metrics_reg.get("ppda", {}).get("default", 12.0))
        xg_default = float(metrics_reg.get("xg", {}).get("default", 0.0))

        metrics = [
            {"metric_id": "ppda", "value": ppda_default},
            {"metric_id": "xg", "value": xg_default},
        ]

        # 2) Cognitive speed proxy (scanning inference)
        cog = compute_decision_speed(raw_df, entity_id=entity_id)
        if cog.get("avg_decision_speed_sec") is not None:
            metrics.append({"metric_id": "cognitive_speed_sec", "value": cog["avg_decision_speed_sec"]})
            metrics.append({"metric_id": "cognitive_speed_status", "value": cog["status"]})

        # 3) Evidence graph
        overall = "medium"
        if cog.get("status") == "ELITE":
            overall = "high"
        if cog.get("status") in ("UNKNOWN", None):
            overall = "medium"

        eg = EvidenceGraph(
            overall_confidence=overall,
            hypotheses=[
                Hypothesis(
                    id="H_COG",
                    claim="Player shows decision-speed proxy consistent with scanning readiness.",
                    confidence=overall,
                    supporting=["cognitive_speed_sec"] if cog.get("avg_decision_speed_sec") is not None else [],
                    contradicting=[],
                    notes=cog.get("note"),
                )
            ],
        )

        # 4) Archetype check (registry-based)
        archetype_report = None
        if archetype_id:
            archetype_report = self._evaluate_archetype(archetype_id, metrics)

        return {
            "status": "OK",
            "analysis_object_id": analysis_object_id,
            "entity_id": entity_id,
            "role": role,
            "phase": phase,
            "metrics": metrics,
            "missing_metrics": [],
            "tables": {},
            "lists": {"archetype": archetype_report} if archetype_report else {},
            "figure_objects": {},
            "evidence_graph": {
                "overall_confidence": eg.overall_confidence,
                "hypotheses": [
                    {
                        "id": h.id,
                        "claim": h.claim,
                        "confidence": h.confidence,
                        "supporting": h.supporting,
                        "contradicting": h.contradicting,
                        "notes": h.notes,
                    }
                    for h in eg.hypotheses
                ],
            },
        }

    def _evaluate_archetype(self, archetype_id: str, metrics: list) -> Dict[str, Any]:
        archetypes = (self.registry or {}).get("archetypes", []) or []
        spec = next((a for a in archetypes if a.get("id") == archetype_id), None)
        if not spec:
            return {"id": archetype_id, "status": "UNKNOWN_ARCHETYPE"}

        # metrics list -> dict
        m = {}
        for row in metrics:
            mid = row.get("metric_id")
            if mid is not None:
                m[mid] = row.get("value")

        req = spec.get("required_metrics", {}) or {}
        checks = []
        passed = True

        for k, rule in req.items():
            val = m.get(k)
            rmin = rule.get("min")
            rmax = rule.get("max")

            ok = True
            if val is None:
                ok = False
            if rmin is not None and val is not None and float(val) < float(rmin):
                ok = False
            if rmax is not None and val is not None and float(val) > float(rmax):
                ok = False

            checks.append({"metric": k, "value": val, "rule": rule, "ok": ok})
            if not ok:
                passed = False

        return {
            "id": spec.get("id"),
            "name": spec.get("name"),
            "status": "PASS" if passed else "FAIL",
            "checks": checks,
        }