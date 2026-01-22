import uuid

class EvidenceNode:
    """Ontoloji Diyagramı v2.0: Kanıt Düğümü (Metric/Video/Doc/Model)"""
    def __init__(self, type, source, strength=1.0):
        self.node_id = uuid.uuid4()
        self.type = type # metric, video, doc, model
        self.source = source
        self.strength = strength # Güven skoru (v1.5 Epistemic Layer)

class Hypothesis:
    """Ontoloji Diyagramı v2.0: Popperian Hipotez Çekirdeği"""
    def __init__(self, claim, falsifier):
        self.hypothesis_id = uuid.uuid4()
        self.claim = claim
        self.falsifier = falsifier
        self.supports = []
        self.falsifications = []

    def assess_validity(self):
        # Triangular Validation (v1.0)
        # En az 2 bağımsız kanıt aksı (EvidenceNode) gereklidir.
        if len(self.supports) >= 2 and not self.falsifications:
            return "VALIDATED"
        elif self.falsifications:
            return "FALSIFIED"
        return "PENDING_EVIDENCE"
