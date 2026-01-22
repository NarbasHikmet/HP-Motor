from pydantic import BaseModel
from typing import List, Optional, Any

class EvidenceNode(BaseModel):
    """v1.0: Karar ve Tablo Fabrikasının ortak dili."""
    metric_id: str
    metric_name: str
    value: Any
    sample_size: int
    source: str
    confidence_score: float
    uncertainty: float
    scope: str = "open_play"

class AnalysisObject(BaseModel):
    """v1.0: Her analiz bir 'Niyet' ile başlar."""
    analysis_id: str
    question: str
    metric_bundle: List[str]
    evidence_policy: dict
    persona_outputs: List[str]
