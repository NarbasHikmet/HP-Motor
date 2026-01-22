import pandas as pd

class HPLegoLogic:
    """
    HP Motor - Matematiksel LEGO Katmanı
    Görevi: Ham metrikleri birleştirerek 'Egemen İçgörü' üretmek.
    """
    @staticmethod
    def calculate_sga(df):
        # Bitiricilik: PSxG - xG
        if 'psxg' in df.columns and 'xg' in df.columns:
            return df['psxg'] - df['xg']
        return 0

    @staticmethod
    def calculate_bdp(df):
        # Baskı Etkinliği: (Exp Pass% - Actual Pass%) / Exp
        if 'exp_pass_pct' in df.columns and 'actual_pass_pct' in df.columns:
            return (df['exp_pass_pct'] - df['actual_pass_pct']) / df['exp_pass_pct']
        return 0

    @staticmethod
    def calculate_prog_score(df):
        # Top İlerleme Score: (Prog*3) + (F3rd*2) + (Box*4)
        weights = {'prog_passes': 3, 'f3rd_entries': 2, 'box_entries': 4}
        score = 0
        for col, weight in weights.items():
            if col in df.columns:
                score += df[col] * weight
        return score
