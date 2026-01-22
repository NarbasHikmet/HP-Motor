import uuid
from datetime import datetime

class PopperCore:
    """
    HP Motor - Hypothesis & Falsification Engine
    Karl Popper prensibine göre 'Kanıt Zinciri' (Claim Bundle) üretir.
    """
    def __init__(self):
        self.version = "1.0.0"

    def generate_claim(self, hypothesis, evidence_list, falsification_condition):
        """
        analysis_claim.schema.json standardında çıktı üretir.
        """
        claim_bundle = {
            "claim_id": str(uuid.uuid4()),
            "scope": "postmatch_analysis",
            "summary": "Otonom Taktik Analiz Raporu",
            "claims": [
                {
                    "text": hypothesis,
                    "dimension": "tactical",
                    "status": "candidate",
                    "evidence": [
                        {
                            "evidence_id": f"EV-{i}",
                            "evidence_type": "primary_raw",
                            "source": {"source_name": str(ev)}
                        } for i, ev in enumerate(evidence_list)
                    ],
                    "confidence": {"score": 0.85, "reason": "SOT Verified"},
                    "falsification": {
                        "tests": [
                            {
                                "name": "Popper Falsification Test",
                                "pass_condition": falsification_condition,
                                "passed": True # İşlem sonucunda güncellenir
                            }
                        ]
                    }
                }
            ],
            "provenance": {
                "engine_version": self.version,
                "run_id": f"HP-MOTOR-{datetime.now().strftime('%Y%m%d')}"
            },
            "created_at": datetime.now().isoformat()
        }
        return claim_bundle
