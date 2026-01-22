from engine.validator import SOTValidator
from engine.registry_manager import RegistryManager
from engine.popper_core import PopperCore

class HPMotorOrchestrator:
    def __init__(self):
        self.validator = SOTValidator()
        self.registry = RegistryManager()
        self.popper = PopperCore()

    def process_match_data(self, raw_df, provider="SportsBase"):
        # 1. SOT Gate: Veri Temizliği (0.0 Koruma)
        report, clean_data = self.validator.clean_and_normalize(raw_df)
        
        # 2. Metrik Çözümleme
        resolved_signals = []
        for col in clean_data.columns:
            family = self.registry.resolve_metric(col)
            if family != "UNKNOWN_SIGNAL":
                resolved_signals.append(family)

        # 3. Analiz ve Hipotez Üretimi (Örnek: Atletico v GS Set Piece)
        # Not: Buraya Atletico_Madrid_vs_Galatasaray_Pre_Match_Analysis.md'deki veriler girer.
        claims = []
        if "Set Piece Goals" in clean_data.columns or True:
            claims.append(self.popper.generate_claim(
                hypothesis="Atletico Madrid set-piece etkinliğiyle (F5/F6) fark yaratıyor.",
                evidence_list=["Set Piece Goals: 4", "GS Conceded: 0"],
                falsification_condition="Atletico Set-Piece xG < 0.1"
            ))

        return {
            "audit": report,
            "data": clean_data,
            "claims": claims,
            "signals_detected": resolved_signals
        }
