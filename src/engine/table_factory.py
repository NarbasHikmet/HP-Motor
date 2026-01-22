import pandas as pd

class HPTableFactory:
    """HP Motor v5.0 - 15 Çekirdek Tablo Tipi Üreticisi"""
    
    def create_evidence_table(self, hypothesis_id, evidence_nodes):
        """Popperian Kanıt Tablosu: Metrik | Değer | Örneklem | Güven"""
        data = []
        for node in evidence_nodes:
            data.append({
                "Metrik": node.metric_name,
                "Değer": node.value,
                "Örneklem (n)": node.sample_size,
                "Güven (%)": node.confidence_score,
                "Kaynak": node.source
            })
        return pd.DataFrame(data)

    def create_risk_table(self, player_id, behavioral_data):
        """Sapolsky/Mate Odaklı Risk Tablosu"""
        return pd.DataFrame([{
            "Oyuncu": player_id,
            "Yük": behavioral_data['load'],
            "Travma Döngüsü": behavioral_data['loops'],
            "Risk Seviyesi": "KRİTİK" if behavioral_data['loops'] > 10 else "STABİL"
        }])
