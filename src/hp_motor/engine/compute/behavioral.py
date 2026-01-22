class BehavioralEngine:
    """Sapolsky/Mate: Detect repeat errors (Trauma Loops) in spatial clusters."""
    def analyze_trauma_loops(self, df):
        # Identify unsuccessful/lost actions
        error_mask = df['action'].str.contains('İsabetsiz|unsuccessful|lost|Faul', na=False, case=False)
        errors = df[error_mask].copy()
        
        # Spatial Clustering (10x10 grids)
        errors['grid_x'] = (errors['pos_x'] // 10).astype(int)
        errors['grid_y'] = (errors['pos_y'] // 10).astype(int)
        
        # A loop is same player failing in same grid within 5 mins (300s)
        errors['prev_grid'] = errors.groupby('code')['grid_x'].shift(1)
        errors['time_gap'] = errors.groupby('code')['start'].diff()
        
        loops = errors[(errors['grid_x'] == errors['prev_grid']) & (errors['time_gap'] < 300)]
        return loops
