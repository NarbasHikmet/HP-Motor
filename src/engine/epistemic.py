class EpistemicGuardrail:
    """v1.5: Sistemin 'Bilmiyorum' deme hakkını korur."""
    def assess_confidence(self, df):
        # Veri kalitesi, eksik koordinat ve model çatışması denetimi
        completeness = df[['pos_x', 'pos_y']].notnull().mean().mean()
        
        # v1.5 Epistemik kural: Koordinat kaybı > %10 ise güven düşer.
        confidence_score = 1.0 if completeness > 0.9 else 0.65
        return {
            "score": confidence_score,
            "status": "SECURE" if confidence_score > 0.8 else "CAUTION"
        }
