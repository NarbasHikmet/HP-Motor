import yaml
from pathlib import Path

class HPProviderRegistry:
    """Provider alias sözlüklerini yönetir."""
    def __init__(self):
        self.config_path = Path(__file__).resolve().parent / "provider_generic_csv.yaml"

    def get_mapping(self):
        """CSV auto-discovery için alias listesini döner."""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f)
                return config.get("columns", {})
        except Exception:
            # Fallback (temel kolonlar)
            return {
                "event_type": ["type", "action", "event"],
                "x": ["pos_x", "start_x", "x"],
                "y": ["pos_y", "start_y", "y"]
            }
