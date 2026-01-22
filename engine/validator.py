import pandas as pd
import numpy as np

class SOTValidator:
    """
    SOT (Source of Truth) Gate
    Görevi: 0.0 koordinatlarını korumak ve veriyi 105x68 düzlemine normalize etmek.
    """
    def __init__(self):
        self.dims = {'x': 105, 'y': 68}

    def clean_and_normalize(self, df: pd.DataFrame):
        # 0.0 koordinatları HP Motor için birer veridir, silinmez.
        if 'pos_x' in df.columns and 'pos_y' in df.columns:
            df['x_std'] = df['pos_x'].fillna(0) * (self.dims['x'] / 100)
            df['y_std'] = df['pos_y'].fillna(0) * (self.dims['y'] / 100)
        
        # Sinyal kalitesi denetimi
        quality_report = {
            "coverage": df.notnull().mean().to_dict(),
            "status": "HEALTHY" if df.notnull().mean().mean() > 0.85 else "DEGRADED",
            "row_count": len(df)
        }
        return quality_report, df
