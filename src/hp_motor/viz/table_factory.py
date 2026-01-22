import pandas as pd

class HPTableFactory:
    """v5.0 Table Generation - The Clinical Data Standard."""
    def create_evidence_table(self, nodes: list):
        """Metrik | Değer | Örneklem | Güven | Kaynak"""
        data = []
        for node in nodes:
            data.append({
                "Metrik": node.metric_name,
                "Değer": node.value,
                "Örneklem (n)": node.sample_size,
                "Güven (%)": f"{node.confidence_score * 100}%",
                "Kaynak": node.source
            })
        return pd.DataFrame(data)

    def create_risk_table(self, player_id, loops_count):
        return pd.DataFrame([{
            "Oyuncu": player_id,
            "Travma Döngüsü": loops_count,
            "Risk Durumu": "YÜKSEK" if loops_count > 5 else "STABİL"
        }])
