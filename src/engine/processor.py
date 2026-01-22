class HPProcessor:
    """
    HP Lens Processor
    Görevi: Veriyi 6 Faza (F1-F6) ve 3 Katmana (Micro-Mezzo-Macro) ayırmak.
    """
    def __init__(self):
        self.phase_map = {
            "F1": "Organized Defense", "F2": "Defensive Transition",
            "F3": "Build-Up", "F4": "Organized Attack",
            "F5": "Offensive Transition", "F6": "Set-Pieces"
        }

    def apply_lens(self, df: pd.DataFrame):
        # Başlangıçta tüm aksiyonlar 'Micro' katmanındadır.
        df['layer_hp'] = "micro"
        df['phase_hp'] = "F3" # Default Build-up
        
        if 'action' in df.columns:
            # Örnek: Duran top aksiyonlarını F6'ya mühürle
            df.loc[df['action'].str.contains('corner|free|penalty', case=False, na=False), 'phase_hp'] = "F6"
            # Savunma aksiyonlarını F1'e mühürle
            df.loc[df['action'].str.contains('tackle|interception|block', case=False, na=False), 'phase_hp'] = "F1"
            
        return df
