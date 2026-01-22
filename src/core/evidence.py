# src/core/evidence.py
class EvidenceEngine:
    """Metrikleri 'Kanıt'a, kanıtları 'Karar'a dönüştürür."""
    def validate_claim(self, metrics, hypothesis):
        # Üçgenleme (Triangular Validation) kontrolü
        valid_axes = [m for m in metrics if m.uncertainty < 0.2]
        if len(valid_axes) >= 2:
            return "VALIDATED_CLAIM"
        return "INSUFFICIENT_EVIDENCE"
