import kloppy
from src.engine.validator import SOTValidator

class HP_Ingestion:
    """HP-CDL: Tüm sağlayıcıları (Opta, StatsBomb, Wyscout) tek dile çevirir."""
    def __init__(self):
        self.validator = SOTValidator()

    def load_and_standardize(self, file_path, provider="opta"):
        # Veri yükleme ve standardizasyon (v1.0)
        # 0.0 koordinat koruması burada devreye girer.
        dataset = kloppy.load_event_data(file_path, provider=provider)
        df = dataset.to_pandas()
        return self.validator.ensure_sot(df) # Single Source of Truth Gate
