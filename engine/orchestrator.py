from src.engine.validator import SOTValidator
from src.engine.processor import HPProcessor
from src.engine.analyst import HPAnalyst
from src.engine.reference_linker import HPReferenceLinker

class HPMasterBrain:
    """
    HP Motor - Master Orchestrator (Sovereign Intelligence)
    Görevi: Veriyi alıp 'Hukuki, Teknik ve Akademik' bir rapora dönüştürmek.
    """
    def __init__(self):
        self.validator = SOTValidator()
        self.processor = HPProcessor()
        self.analyst = HPAnalyst()
        self.linker = HPReferenceLinker()

    def run_full_analysis(self, raw_df, match_name="Atletico Madrid vs Galatasaray"):
        # 1. Veri Namusu (0.0 Koruma)
        audit, df = self.validator.validate_and_normalize(raw_df)
        
        # 2. HP Lens & LEGO Logic (6 Faz + Formüller)
        df = self.processor.apply_lens_and_logic(df)
        
        # 3. Popperian İddia Üretimi
        # (Örnek: Bitiricilik kalitesini ölçen SGA hipotezi)
        report = self.analyst.generate_report(
            hypothesis=f"{match_name}: Bitiricilik (SGA) Verimliliği",
            falsification="SGA < 0 ise oyuncu bitiriciliği gürültüdür (noise)."
        )
        
        # 4. Akademik Mühür (Referans Linker)
        report['claims'][0]['citations'].append(self.linker.link("build_up"))
        
        return {"audit": audit, "processed_data": df, "sovereign_report": report}
