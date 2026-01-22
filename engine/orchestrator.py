from engine.validator import SOTValidator

class MasterOrchestrator:
    def __init__(self):
        self.validator = SOTValidator()

    def run_analysis(self, raw_df):
        # 1. Veri Doğrulama
        report, data = self.validator.clean_and_normalize(raw_df)
        
        # 2. Analitik İddia (Claim) Oluşturma - Popperian Şablon
        claims = [
            {
                "claim_id": "HP-001",
                "hypothesis": "Takım dominant bir hücum fazı (F4) sergiliyor.",
                "evidence_metrics": ["xG", "Field Tilt"],
                "falsification_test": "xG < 0.5 ise hipotez reddedilir.",
                "status": "CANDIDATE"
            }
        ]
        
        return {
            "report": report,
            "data": data,
            "claims": claims
        }
