from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from hp_motor.core.scanning import compute_decision_speed
from hp_motor.core.evidence_models import EvidenceGraph
from hp_motor.core.registry_loader import load_master_registry
from hp_motor.core.report_builder import ReportBuilder
from hp_motor.reasoning.falsifier import PopperGate
from hp_motor.validation.abstain_gate import AbstainGate
from hp_motor.validation.sot_validator import SOTValidator

from hp_motor.pipelines.input_manifest import InputManifest
from hp_motor.validation.capability_gate import CapabilityGate


class SovereignOrchestrator:
    """
    Canonical orchestrator for HP Motor.

    Public API:
      - execute(df, **kwargs): canonical
      - run(df, **kwargs): compatibility alias

    Safety:
      - Input-Gated Compute (CapabilityGate)
      - No Silent Drop (SOTValidator report, never drops rows)
      - Evidence-only claims (PopperGate)
      - Fail-closed on BLOCKED
    """

    def __init__(self):
        self.registry = load_master_registry()
        self.report_builder = ReportBuilder()
        self.abstain_gate = AbstainGate()
        self.popper_gate = PopperGate()
        self.sot_validator = SOTValidator(required_columns=["event_type"])
        self.capability_gate = CapabilityGate()

    def execute(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        registry_metrics = self.registry.get("metrics", {})

        analysis_type = str(kwargs.get("analysis_type") or "generic")

        # 1) Runtime input inventory (no guessing)
        manifest = InputManifest.from_kwargs(df_provided=(df is not None), kwargs=kwargs)

        # 2) SOT validation (no silent drop, produces quality report)
        sot = self.sot_validator.validate(df)

        # Spatial evidence upgrade rule:
        # - spatial is TRUE only if x,y exist and are not catastrophically invalid
        has_xy = bool(df is not None) and ("x" in df.columns) and ("y" in df.columns)
        bounds = (sot or {}).get("bounds_report") or {}
        x_oob = int(bounds.get("x_out_of_bounds", 0) or 0)
        y_oob = int(bounds.get("y_out_of_bounds", 0) or 0)

        spatial_ok = False
        if has_xy:
            # Conservative: if a lot of rows are OOB, do not treat as spatial evidence.
            # This avoids "fake spatial certainty".
            spatial_ok = (x_oob == 0 and y_oob == 0)

        manifest = manifest.with_spatial(has_spatial=(manifest.has_spatial or spatial_ok))

        # 3) Capability gate (input-gated compute)
        cap = self.capability_gate.decide(analysis_type=analysis_type, manifest=manifest)

        # 4) Prepare metrics bundle (still registry-driven / placeholder-friendly)
        metrics = {
            "ppda": registry_metrics.get("ppda", {}).get("default"),
            "xg": registry_metrics.get("xg", {}).get("default"),
        }
        used_metric_ids: List[str] = list(metrics.keys())

        # 5) Popper gate (evidence-only) using SOT report (optional)
        popper = self.popper_gate.check_dataframe(
            df,
            required_columns=["event_type"],
            sot_report={
                "status": "PASS" if sot.get("ok") else "ERROR",
                "report": sot,
            },
        )

        # 6) Cognitive proxy
        decision_speed = compute_decision_speed(df)

        # 7) Fail-closed abstain rules
        if cap.status == "BLOCKED":
            for mid in used_metric_ids:
                self.abstain_gate.abstain(
                    metric_id=mid,
                    reason=f"CAPABILITY_BLOCK: {', '.join(cap.reasons)}",
                )

        if popper.get("block_downstream"):
            for mid in used_metric_ids:
                self.abstain_gate.abstain(
                    metric_id=mid,
                    reason="POPPER_BLOCK: minimum evidence missing or integrity violation",
                )

        # 8) Evidence graph (always OK to produce bookkeeping evidence)
        eg = EvidenceGraph()
        eg.add_claim("decision_speed", decision_speed, note="Computed decision speed proxy")

        eg.add_claim(
            "input_manifest",
            {
                "has_event": manifest.has_event,
                "has_spatial": manifest.has_spatial,
                "has_fitness": manifest.has_fitness,
                "has_video": manifest.has_video,
                "has_tracking": manifest.has_tracking,
                "has_doc": manifest.has_doc,
                "notes": manifest.notes,
            },
            note="Runtime input inventory (no guessing)",
        )

        eg.add_claim("sot_report", sot, note="SOT validation report (no silent drop)")
        eg.add_claim("capability_gate", cap.to_dict(), note="Input-gated compute decision")
        eg.add_claim("popper_gate", popper, note="Popper gate report (evidence-only)")

        evidence = eg.to_dict()

        # 9) ABSTAIN gate evaluation
        abstain = self.abstain_gate.evaluate(
            registry_metrics=registry_metrics,
            used_metric_ids=used_metric_ids,
        )

        popper_blocks = bool(popper.get("block_downstream"))

        # 10) Build report shell (never hallucinate: status tells truth)
        report = self.report_builder.build(df=df, metrics=metrics, evidence=evidence)

        # Status policy:
        # - BLOCKED => ABSTAINED
        # - Popper BLOCK => ABSTAINED
        # - Abstain => ABSTAINED
        # - DEGRADED => DEGRADED
        status = "OK"
        if cap.status == "BLOCKED" or popper_blocks or abstain.abstained:
            status = "ABSTAINED"
        elif cap.status == "DEGRADED":
            status = "DEGRADED"

        safety_note = None
        if cap.status == "BLOCKED":
            safety_note = "Missing input → module disabled to prevent hallucination."
        elif cap.status == "DEGRADED":
            safety_note = "Partial input → output degraded; no hard claims beyond evidence."

        return {
            "status": status,
            "analysis_type": analysis_type,
            "safety_note": safety_note,
            "capability_gate": cap.to_dict(),
            "input_manifest": {
                "has_event": manifest.has_event,
                "has_spatial": manifest.has_spatial,
                "has_fitness": manifest.has_fitness,
                "has_video": manifest.has_video,
                "has_tracking": manifest.has_tracking,
                "has_doc": manifest.has_doc,
                "notes": manifest.notes,
            },
            "sot": sot,
            "popper_gate": popper,
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

    def run(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        return self.execute(df, **kwargs)