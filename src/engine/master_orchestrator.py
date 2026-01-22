from src.engine.validator import SOTValidator
from src.engine.processor import HPProcessor
from src.engine.analyst import HPAnalyst
from src.engine.formulas import HPLegoLogic
from src.engine.reference_linker import HPReferenceLinker

class HPAureliaOrchestrator:
    """
    HP Engine - AURELIA Master Orchestrator
    'Her Şeyin Teorisi'nin ilk otonom icra makamı.
    """
    def __init__(self):
        self.validator = SOTValidator()
        self.processor = HPProcessor()
        self.analyst = HPAnalyst()
        self.logic = HPLegoLogic()
        self.linker = HPReferenceLinker()

    def execute_sovereign_analysis(self, raw_df, context="Atletico vs GS"):
        # 1. Veri Namusu (Validator)
        audit, df = self.validator.validate_and_normalize(raw_df)
        
        # 2. Taktiksel Lens & Matematiksel LEGO (Processor & Logic)
        df = self.processor.apply_lens_and_logic(df)
        
        # 3. Kanıt Zinciri Üretimi (Analyst)
        # Örnek: SGA (Bitiricilik) ve BDP (Baskı) üzerinden otomatik hipotez
        total_sga = df['sga_hp'].sum() if 'sga_hp' in df.columns else 1.2 # Örnek değer
        
        report = self.analyst.generate_report(
            hypothesis=f"{context}: Bitiricilik ve Sistemik Baskı Analizi",
            falsification=f"SGA < 0 veya BDP < 0.1 ise {context} taktiksel çöküştedir."
        )
        
        # 4. Akademik Mühür (Linker)
        report['claims'][0]['citations'].append(self.linker.link("build_up"))
        
        return {
            "audit_report": audit,
            "processed_data": df,
            "sovereign_intelligence": report
        }
