import pandas as pd

class HPProcessor:
    """
    HP Motor - 6 Fazlı Segmentasyon ve Katman İşlemcisi
    """
    def __init__(self):
        self.phases = {
            "F1": "Organized Defense",
            "F2": "Defensive Transition",
            "F3": "Organized Attack",
            "F4": "Offensive Transition",
            "F5": "Set Pieces (Att)",
            "F6": "Set Pieces (Def)"
        }

    def segment_phases(self, df):
        """
        Ham veriyi zaman damgası ve aksiyon tipine göre 6 faza ayırır.
        """
        # Örnek kural bazlı segmentasyon (SportsBase 'action' kolonuna göre)
        df['phase_hp'] = "UNKNOWN"
        
        # Basit kural seti:
        if 'action' in df.columns:
            df.loc[df['action'].str.contains('corner|free kick', na=False), 'phase_hp'] = "F5"
            df.loc[df['action'].str.contains('tackle|interception', na=False), 'phase_hp'] = "F1"
            df.loc[df['action'].str.contains('shot|cross', na=False), 'phase_hp'] = "F3"
            
        return df

    def apply_layers(self, df):
        """
        Veriyi Mikro (Bireysel), Mezzo (Grup), Makro (Takım) olarak etiketler.
        """
        df['layer_hp'] = "micro" # Varsayılan: Bireysel aksiyon
        # Agregasyon varsa mezzo/macro etiketleri buraya gelir
        return df
