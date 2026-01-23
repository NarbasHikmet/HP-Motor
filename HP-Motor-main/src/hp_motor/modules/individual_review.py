from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, List

import pandas as pd

from hp_motor.core.scanning import ScanningEngine
from hp_motor.core.cognition import CognitiveEngine
from hp_motor.validation.biomechanic_gate import BiomechanicGate


@dataclass
class IndividualProfile:
    player_id: int
    summary: Dict[str, Any]
    metrics: List[Dict[str, Any]]


class IndividualReviewEngine:
    """
    Individual Review (v1):
    - Cognitive Speed (timestamp proxy)
    - Scanning Score (derived proxy)
    - Biomechanic: 45° defense + half-turn receiving (angle column if exists)
    """

    def __init__(self):
        self.scanner = ScanningEngine()
        self.cognition = CognitiveEngine()
        self.bio_gate = BiomechanicGate()

    def build_player_profile(self, df: pd.DataFrame, player_id: int) -> IndividualProfile:
        player_df = df[df["player_id"] == player_id] if "player_id" in df.columns else df.copy()

        cog = self.cognition.compute_cognitive_speed(df, player_id)
        scan = self.scanner.estimate_scanning_score(cog["value"])

        # Biomechanics: attempt; may abstain
        bio_45 = self.bio_gate.validate_defender_45_degree(player_df, defender_id=player_id)
        half_turn = self.bio_gate.validate_half_turn_receiving(player_df, player_id=player_id)

        metrics = [
            {
                "metric_id": "cognitive_speed_sec",
                "value": cog["value"],
                "interpretation": cog["interpretation"],
                "note": cog["note"],
            },
            {
                "metric_id": "scanning_proxy_score",
                "value": scan["scanning_score"],
                "interpretation": scan["scanning_interpretation"],
                "note": scan["note"],
            },
            {
                "metric_id": bio_45.metric_id,
                "value": bio_45.value,
                "interpretation": bio_45.status,
                "note": bio_45.note,
                "evidence": bio_45.evidence,
            },
            {
                "metric_id": half_turn.metric_id,
                "value": half_turn.value,
                "interpretation": half_turn.status,
                "note": half_turn.note,
                "evidence": half_turn.evidence,
            },
        ]

        # Summary line for UI / report
        summary = {
            "player_id": player_id,
            "cognitive_speed_sec": cog["value"],
            "scanning_proxy_score": scan["scanning_score"],
            "defense_45deg_status": bio_45.status,
            "half_turn_status": half_turn.status,
        }

        return IndividualProfile(player_id=player_id, summary=summary, metrics=metrics)