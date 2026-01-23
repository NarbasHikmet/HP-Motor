from __future__ import annotations

from typing import Literal, Optional, Tuple

from pydantic import BaseModel, Field


PitchXY = Tuple[float, float]


class Context(BaseModel):
    match_id: str
    period: int = 1
    score_state: Optional[Literal["leading", "drawing", "trailing"]] = None
    home_away: Optional[Literal["home", "away"]] = None


class Action(BaseModel):
    match_id: str
    team_id: str
    player_id: str
    time_s: float = Field(ge=0.0)
    action_type: str  # "pass", "carry", "shot", ...
    start_xy: Optional[PitchXY] = None
    end_xy: Optional[PitchXY] = None
    outcome: Optional[str] = None
    under_pressure: Optional[bool] = None
    source: str = "unknown"


class PhaseSegment(BaseModel):
    match_id: str
    phase_id: str  # F1..F6 or HP labels
    subphase_id: Optional[str] = None
    start_s: float = Field(ge=0.0)
    end_s: float = Field(ge=0.0)
    trigger: Optional[str] = None


class MetricValue(BaseModel):
    metric_id: str
    entity_type: Literal["player", "team", "match"]
    entity_id: str
    value: float
    unit: Optional[str] = None
    scope: Optional[str] = None  # open_play, set_piece, etc.
    sample_size: Optional[float] = None  # minutes, n_actions
    source: str = "unknown"
    uncertainty: Optional[float] = None  # 0..1 or sd, depending on policy