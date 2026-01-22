import pandas as pd
import json
import logging

class SignalProcessor:
    """
    HP Motor - Signal Ingestion Layer
    Görevi: Ham veriyi 'HP Engine Signal' formatına valide ederek çevirmek.
    """
    def __init__(self, signal_schema_path="schemas/signal.schema.json"):
        with open(signal_schema_path, 'r') as f:
            self.schema = json.load(f)

    def ingest(self, df: pd.DataFrame, provider: str):
        # Platform Mappings üzerinden kolonları eşle
        # SportsBase 'pos_x' -> 'events.start_x'
        signals = []
        for index, row in df.iterrows():
            signal_entry = {
                "signal_id": f"SIG-{index}",
                "timestamp": row.get('start', 0),
                "data": row.to_dict(),
                "provider": provider
            }
            signals.append(signal_entry)
        
        return signals
