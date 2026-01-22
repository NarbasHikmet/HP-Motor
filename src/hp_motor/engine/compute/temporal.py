import pandas as pd

class TemporalEngine:
    """Identify momentum shifts and regime changes."""
    def detect_regime_shifts(self, df):
        # Action density per minute
        df['minute'] = (df['start'] // 60).astype(int)
        density = df.groupby(['minute', 'code']).size().unstack().fillna(0)
        # Momentum shift is a significant change in rolling average
        momentum = density.rolling(window=5).mean().diff()
        return momentum
