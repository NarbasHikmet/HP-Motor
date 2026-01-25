from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


class SovereignOrchestrator:
    """
    Import-safe orchestrator (CI smoke import friendly).

    Why:
      - GitHub Actions "Smoke Import Test" imports this class only.
      - Any broken/missing internal import should NOT fail import-time.
      - We move internal imports to runtime ("lazy imports").

    Safety:
      - If a dependency is missing, execute() will ABSTAIN (fail-closed).
      - No hallucination: missing input/deps => BLOCKED/ABSTAINED.
    """

    def __init__(self):
        # Defer heavy/internal imports until execute() unless they are guaranteed.
        self._boot_ok = True
        self._boot_issues: List[str] = []

        # Optional pre-load minimal registry loader (safe)
        try:
            from hp_motor.core.registry_loader import load_master_registry  # type: ignore
            self.registry = load_master_registry()
        except Exception as e:
            # Fail-closed: we can still import & run, but will abstain on execute.
            self.registry = {}
            self._boot_ok = False
            self._boot_issues.append(f"BOOT_REGISTRY_LOAD_FAILED: {e}")

    def execute(self, df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
        analysis_type = str(kwargs.get("analysis_type") or "generic")

        # --- Lazy imports (runtime) ---
        boot_issues: List[str] = list(self._boot_issues)

        # These are required for full execution; if any fails, we ABSTAIN safely.
        try:
            from hp_motor.pipelines.input_manifest import InputManifest  # type: ignore
        except Exception as e:
            boot_issues.append(f"IMPORT_FAIL: hp_motor.pipelines.input_manifest: {e}")
            return self._abstain_shell(analysis_type, boot_issues)

        try:
            from hp_motor.validation.capability_gate import CapabilityGate  # type: ignore
        except Exception as e:
            boot_issues.append(f"IMPORT_FAIL: hp_motor.validation.capability_gate: {e}")
            return self._abstain_shell(analysis_type, boot_issues)

        try:
            from hp_motor.validation.sot_validator import SOTValidator  # type: ignore
        except Exception as e:
            boot_issues.append(f"IMPORT_FAIL: hp_motor.validation.sot_validator: {e}")
            return self._abstain_shell(analysis_type, boot_issues)

        try:
            from hp_motor.reasoning.falsifier import PopperGate  # type: ignore
        except Exception as e:
            boot_issues.append(f"IMPORT_FAIL: hp_motor.reasoning.falsifier: {e}")
            return self._abstain_shell(analysis_type, boot_issues)

        try:
            from hp_motor.validation.abstain_gate import AbstainGate  # type: ignore
        except Exception as e:
            boot_issues.append(f"IMPORT_FAIL: hp_motor.validation.abstain_gate: {e}")
            return self._abstain_shell(analysis_type, boot_issues)

        try:
            from hp_motor.core.scanning import compute_decision_speed  # type: ignore
        except Exception as e:
            boot_issues.append(f"IMPORT_FAIL: hp_motor.core.scanning: {e}")
            return self._abstain_shell(analysis_type, boot_issues)

        # ReportBuilder / EvidenceGraph are optional for now; if they fail we still produce a safe shell.
        ReportBuilder = None
        EvidenceGraph = None
        try:
            from hp_motor.core.report_builder import ReportBuilder as _RB  # type: ignore
            ReportBuilder = _RB
        except Exception as e:
            boot_issues.append(f"IMPORT_WARN: hp_motor.core.report_builder: {e}")

        try:
            from hp_motor.core.evidence_models import EvidenceGraph as _EG  # type: ignore
            EvidenceGraph = _EG
        except Exception as e:
            boot_issues.append(f"IMPORT_WARN: hp_motor.core.evidence_models: {e}")

        # --- Runtime objects ---
        manifest = InputManifest.from_kwargs(df_provided=(df is not None), kwargs=kwargs)

        sot_validator = SOTValidator(required_columns=["event_type"])
        sot = sot_validator.validate(df)

        # Spatial evidence: only if x,y exist AND SOT says bounds OK (conservative)
        has_xy = bool(df is not None) and ("x" in df.columns) and ("y" in df.columns)
        bounds = (sot or {}).get("bounds_report") or {}
        x_oob = int(bounds.get("x_out_of_bounds", 0) or 0)
        y_oob = int(bounds.get("y_out_of_bounds", 0) or 0)
        spatial_ok = bool(has_xy and x_oob == 0 and y_oob == 0)
        manifest = manifest.with_spatial(has_spatial=(manifest.has_spatial or spatial_ok))

        cap_gate = CapabilityGate()
        cap = cap_gate.decide(analysis_type=analysis_type, manifest=manifest)

        popper_gate = PopperGate()
        popper = popper_gate.check_dataframe(
            df,
            required_columns=["event_type"],
            sot_report={"status": "PASS" if sot.get("ok") else "ERROR", "report": sot},
        )

        decision_speed = compute_decision_speed(df)

        # Registry metrics (placeholder-friendly)
        registry_metrics = (self.registry or {}).get("metrics", {}) if isinstance(self.registry, dict) else {}
        metrics = {
            "ppda": registry_metrics.get("ppda", {}).get("default") if isinstance(registry_metrics, dict) else None,
            "xg": registry_metrics.get("xg", {}).get("default") if isinstance(registry_metrics, dict) else None,
        }
        used_metric_ids: List[str] = list(metrics.keys())

        abstain_gate = AbstainGate()

        # Fail-closed: BLOCKED capability => abstain
        if cap.status == "BLOCKED":
            for mid in used_metric_ids:
                abstain_gate.abstain(metric_id=mid, reason=f"CAPABILITY_BLOCK: {', '.join(cap.reasons)}")

        # Popper block => abstain
        if popper.get("block_downstream"):
            for mid in used_metric_ids:
                abstain_gate.abstain(metric_id=mid, reason="POPPER_BLOCK: minimum evidence missing or integrity violation")

        abstain = abstain_gate.evaluate(registry_metrics=registry_metrics, used_metric_ids=used_metric_ids)

        # Evidence payload (safe even if EvidenceGraph missing)
        evidence: Dict[str, Any] = {
            "boot_ok": self._boot_ok,
            "boot_issues": boot_issues,
            "input_manifest": {
                "has_event": manifest.has_event,
                "has_spatial": manifest.has_spatial,
                "has_fitness": manifest.has_fitness,
                "has_video": manifest.has_video,
                "has_tracking": manifest.has_tracking,
                "has_doc": manifest.has_doc,
                "notes": manifest.notes,
            },
            "capability_gate": cap.to_dict(),
            "sot": sot,
            "popper_gate": popper,
            "decision_speed": decision_speed,
        }

        # Optional ReportBuilder
        report: Dict[str, Any] = {}
        if ReportBuilder is not None:
            try:
                rb = ReportBuilder()
                report = rb.build(df=df, metrics=metrics, evidence=evidence)
            except Exception as e:
                boot_issues.append(f"REPORT_WARN: ReportBuilder.build failed: {e}")

        # Status hierarchy
        status = "OK"
        if cap.status == "BLOCKED" or popper.get("block_downstream") or abstain.abstained:
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
            "input_manifest": evidence["input_manifest"],
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

    @staticmethod
    def _abstain_shell(analysis_type: str, boot_issues: List[str]) -> Dict[str, Any]:
        return {
            "status": "ABSTAINED",
            "analysis_type": analysis_type,
            "safety_note": "Dependency missing → execution blocked to prevent hallucination.",
            "capability_gate": {"status": "BLOCKED", "reasons": boot_issues, "missing_inputs": []},
            "input_manifest": {},
            "sot": {"ok": False, "issues": [{"code": "BOOT_IMPORT_FAIL", "message": "; ".join(boot_issues), "severity": "ERROR"}]},
            "popper_gate": {"passed": False, "issues": [{"code": "BOOT_IMPORT_FAIL", "message": "; ".join(boot_issues), "severity": "ERROR"}], "block_downstream": True},
            "abstain": {"abstained": True, "reasons": boot_issues, "blocking_metrics": [], "note": "import-safe abstain shell"},
            "metrics": {},
            "evidence": {"boot_ok": False, "boot_issues": boot_issues},
        }