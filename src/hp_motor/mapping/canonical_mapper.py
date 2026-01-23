import pandas as pd

class HPCanonicalMapper:
    """Provider bazlı kolon keşfi ve eşleme (Auto-Discovery)."""
    def __init__(self, mapping_dict):
        self.mapping_dict = mapping_dict  # yaml'dan yüklenen alias sözlüğü

    def map_dataframe(self, df: pd.DataFrame):
        """Headers -> Canonical mapping + Capability Report."""
        col_map = {}
        missing_required = []
        
        # Mapping logic
        for canonical_col, aliases in self.mapping_dict.items():
            found = False
            for alias in aliases:
                if alias in df.columns:
                    col_map[alias] = canonical_col
                    found = True
                    break
            if not found and canonical_col in ["event_type", "team_id", "x", "y"]:
                missing_required.append(canonical_col)

        # Rename columns
        new_df = df.rename(columns=col_map)
        
        capability_report = {
            "mapped_count": len(col_map),
            "missing_required": missing_required,
            "can_analyze": len(missing_required) == 0
        }
        
        return new_df, capability_report
