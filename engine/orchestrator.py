from engine.validator import SOTValidator
from engine.registry import MetricRegistry

class MasterOrchestrator:
    def __init__(self):
        self.validator = SOTValidator()
        self.registry = MetricRegistry()

    def run_analysis(self, raw_df):
        # 1. SOT Gate: Veri Temizliği ve Normalizasyon
        report, data = self.validator.clean_and_normalize(raw_df)
        
        # 2. Faz Bazlı Metrik Gruplama
        # Örnek: F1 (Build-up) fazındaki metriklerin tespiti
        f1_metrics = self.registry.get_phase_metrics("F1")
        
        # 3. Kanıt Zinciri (Claims) - Popperian Yaklaşım
        # Burada metrikler arası 'Relatif Bağlar' kontrol edilir
        claims = self._generate_claims(data)
        
        return {
            "report": report,
            "data": data,
            "claims": claims
        }

    def _generate_claims(self, df):
        # Bu kısım ileride ACM∞ (Alternatif Bakış) ile genişleyecek
        claims = []
        # Örnek bir otomatik iddia:
        if "xG" in df.columns and df["xG"].sum() > 1.5:
            claims.append({
                "hypothesis": "Hücum Organizasyonu (F3) yüksek verimlilikte.",
                "evidence": ["Total xG > 1.5"],
                "falsification": "Shot Conversion Rate < %10 ise 'Kısır Baskı' hipotezi değerlendirilir."
            })
        return claims
