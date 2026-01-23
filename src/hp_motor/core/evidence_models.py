from __future__ import annotations
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

class EvidenceNode(BaseModel):
    node_id: str
    metric_id: str
    value: float
    status: Literal["supporting", "contradicting", "neutral"] = "neutral"
    strength: float = Field(default=0.5, ge=0.0, le=1.0)

class Contradiction(BaseModel):
    id: str
    metrics: List[str]  # Çelişen metrik çiftleri (örn: ["PPDA", "FIELD_TILT"])
    explanation: str
    severity: Literal["low", "medium", "high"]

class EvidenceGraph(BaseModel):
    nodes: List[EvidenceNode] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)
    overall_confidence: float = 0.0
