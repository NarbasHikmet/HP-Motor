from __future__ import annotations

from typing import Dict, Any
import pandas as pd

from hp_motor.core.scanning import compute_decision_speed
from hp_motor.core.evidence_models import EvidenceGraph
from hp_motor.core.registry_loader import load_master_registry
from hp_motor.core.report_builder import ReportBuilder


class SovereignOrchestrator:
    def __init__(self):
        self.registry = load_master_registry()
        self.report_builder = ReportBuilder()

    def execute(self, df: pd.DataFrame) -> Dict[str, Any]:
        # --- Metrics (still placeholder-aware)
        metrics = {
            "ppda": self.registry.get("metrics", {}).get("ppda", {}).get("default"),
            "xg": self.registry.get("metrics", {}).get("xg", {}).get("default"),
        }

        # --- Cognitive proxy
        decision_speed = compute_decision_speed(df)

        # --- Evidence graph
        eg = EvidenceGraph()
        eg.add_claim(
            claim_id="decision_speed",
            value=decision_speed,
            note="Computed decision speed proxy",
        )

        evidence = eg.to_dict()

        # --- Report builder (NEW)
        report = self.report_builder.build(
            df=df,
            metrics=metrics,
            evidence=evidence,
        )

        return {
            "metrics": metrics,
            "evidence": evidence,
            **report,
        }