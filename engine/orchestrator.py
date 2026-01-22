from src.engine.validator import SOTValidator
from src.engine.processor import HPProcessor
from src.engine.behavioral_engine import BehavioralEngine
from src.engine.analyst import HPAnalyst

class HPMasterOrchestrator:
    def __init__(self):
        self.validator = SOTValidator()
        self.processor = HPProcessor()
        self.behavioral = BehavioralEngine()
        self.analyst = HPAnalyst()
        # UI Standardı mühürlendi; ileride bu protokol grafikleri çizecek.
        self.aesthetic_protocol = "SOVEREIGN_TENEBRISM_V2"

    def process_match(self, raw_data):
        # 1. Veri Namusu (0.0 Koruma)
        audit, df = self.validator.validate_and_normalize(raw_data)
        
        # 2. Taktiksel Lens (6 Faz)
        df = self.processor.apply_lens_and_logic(df)
        
        # 3. Davranışsal Analiz (Sapolsky/Mate)
        df = self.behavioral.analyze_trauma_loops(df)
        df = self.behavioral.calculate_emotional_load(df)
        
        # 4. Popperian Kanıt Zinciri
        # Örnek: SGA ve Stres yükü arasındaki korelasyon
        report = self.analyst.generate_report(
            "Yüksek Stres Altında Karar Mekanizması Çöküşü",
            "stress_load > 0.6 iken SGA < 0 ise hipotez doğrulanır."
        )
        
        return df, report
