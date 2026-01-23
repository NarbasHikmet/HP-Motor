from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Hypothesis(BaseModel):
    hypothesis_id: str
    claim: str
    scope: Dict[str, Any] = Field(default_factory=dict)
    falsifiers: List[str] = Field(default_factory=list)  # machine-readable rules (v1.0 string DSL ok)


class EvidenceNode(BaseModel):
    node_id: str
    axis: Literal["metrics", "benchmark", "video", "document", "model"]
    ref: Dict[str, Any] = Field(default_factory=dict)  # link to metric_id/entity_id, clip_id, doc_span, etc.
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    note: Optional[str] = None


class Contradiction(BaseModel):
    contradiction_id: str
    hypothesis_id: str
    explanation_candidate: str
    status: Literal["open", "resolved", "accepted"] = "open"
    conflicting_nodes: List[str] = Field(default_factory=list)


class EvidenceGraph(BaseModel):
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    nodes: List[EvidenceNode] = Field(default_factory=list)
    contradictions: List[Contradiction] = Field(default_factory=list)

    overall_confidence: Literal["low", "medium", "medium_high", "high"] = "medium"