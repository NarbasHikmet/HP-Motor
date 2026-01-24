from __future__ import annotations

from typing import Dict, Any, List
import pandas as pd

from hp_motor.core.scanning import compute_decision_speed
from hp_motor.core.evidence_models import EvidenceGraph
from hp_motor.core.registry_loader import load_master_registry
from hp_motor.core.report_builder import ReportBuilder
from hp_motor.validation.abstain_gate import AbstainGate


class SovereignOrchestrator:
    """
    Canonical orchestrator for HP Motor.

    Public API:
      - execute(df, **kwargs): canonical
      - run(df, **kwargs): backward/CI/UI compatible alias
    """

    def __init__(self):
        self.registry = load_master_registry()
        self.report_builder = ReportBuilder()
        self.abstain_gate = AbstainGate()

    # -------------------------
    # CANONICAL ENTRYPOINT
    # -------------------------
    def execute(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        registry_metrics = self.registry.get("metrics", {})

        metrics = {
            "ppda": registry_metrics.get("ppda", {}).get("default"),
            "xg": registry_metrics.get("xg", {}).get("default"),
        }
        used_metric_ids: List[str] = list(metrics.keys())

        # Cognitive proxy
        decision_speed = compute_decision_speed(df)

        # Evidence graph
        eg = EvidenceGraph()
        eg.add_claim(
            claim_id="decision_speed",
            value=decision_speed,
            note="Computed decision speed proxy",
        )
        evidence = eg.to_dict()

        # ABSTAIN Gate
        abstain = self.abstain_gate.evaluate(
            registry_metrics=registry_metrics,
            used_metric_ids=used_metric_ids,
        )

        # Report builder
        report = self.report_builder.build(
            df=df,
            metrics=metrics,
            evidence=evidence,
        )

        status = "ABSTAINED" if abstain.abstained else "OK"

        return {
            "status": status,
            "abstain": {
                "abstained": abstain.abstained,
                "reasons": abstain.reasons,
                "blocking_metrics": abstain.blocking_metrics,
                "note": abstain.note,
            },
            "metrics": metrics,
            "evidence": evidence,
            **report,
        }

    # -------------------------
    # COMPATIBILITY ALIAS
    # -------------------------
    def run(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        """
        Alias for execute().
        Required for:
          - Streamlit UI
          - CI smoke import tests
          - Legacy calls
        """
        return self.execute(df, **kwargs)