class HPProcessor:
    def apply_lens(self, df):
        # Zihin haritandaki kural setlerini uygular
        df['phase_hp'] = "F0: Neutral"
        if 'action' in df.columns:
            df.loc[df['action'].str.contains('pass|build', na=False), 'phase_hp'] = "F3: Build-Up"
            df.loc[df['action'].str.contains('tackle|interception', na=False), 'phase_hp'] = "F1: Org-Defense"
            df.loc[df['action'].str.contains('corner|free kick', na=False), 'phase_hp'] = "F6: Set-Pieces"
        
        df['layer_hp'] = "micro" # Varsayılan bireysel eylem
        return df
