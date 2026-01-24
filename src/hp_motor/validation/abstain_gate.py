from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class AbstainResult:
    abstained: bool
    reasons: List[str]
    blocking_metrics: List[str]
    note: str


class AbstainGate:
    """
    ABSTAIN Gate (v1)

    Policy:
      - If a metric is present ONLY as a default (no compute evidence),
        the engine must not produce a definitive verdict based on it.
      - This gate does not crash execution; it marks the output as ABSTAINED.

    Expected registry metric shapes:
      metrics:
        xg:
          default: 0.0
        ppda:
          default: 12.0
    """

    def evaluate(self, registry_metrics: Dict[str, Any], used_metric_ids: List[str]) -> AbstainResult:
        reasons: List[str] = []
        blocking: List[str] = []

        for mid in used_metric_ids:
            spec = registry_metrics.get(mid)
            if not isinstance(spec, dict):
                continue

            keys = set(spec.keys())
            # default-only (or value-only) detection
            if keys.issubset({"default", "value", "note", "aliases"}):
                blocking.append(mid)
                reasons.append(
                    f"Metric '{mid}' is default-only (no compute evidence); definitive claims are not allowed."
                )

        if blocking:
            return AbstainResult(
                abstained=True,
                reasons=reasons,
                blocking_metrics=blocking,
                note="ABSTAINED due to default-only metrics.",
            )

        return AbstainResult(
            abstained=False,
            reasons=[],
            blocking_metrics=[],
            note="No abstain conditions met.",
        )