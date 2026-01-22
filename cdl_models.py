# src/hp_motor/core/cdl_models.py
from pydantic import BaseModel
from typing import List, Optional

class EvidenceNode(BaseModel):
    """v1.0: Karar ve Tablo Fabrikasının ortak dili."""
    metric_id: str
    value: float
    sample_size: int
    source: str
    uncertainty: float
    confidence_score: float
    scope: str = "open_play"

class AnalysisObject(BaseModel):
    """v1.0: Her analiz bir 'Niyet' ile başlar."""
    analysis_id: str
    question: str
    metric_bundle: List[str]
    evidence_policy: dict
    persona_outputs: List[str]
