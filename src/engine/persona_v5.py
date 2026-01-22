class SovereignPersonaManager:
    """HP Motor v5.0 - Persona Karar Yüzeyi Yönetimi"""
    
    def __init__(self):
        self.personas = {
            "Match Analyst": {
                "archetype": "Pep/Tuchel",
                "required_tables": ["Phase Contribution", "Evidence Table"],
                "required_plots": ["Phase Dominance", "xT Momentum"],
                "focus": "Structural Causality"
            },
            "Scout": {
                "archetype": "Rangnick",
                "required_tables": ["Role-Fit", "Risk & Availability"],
                "required_plots": ["Role Radar", "Similarity Map"],
                "focus": "Behavioral Trauma & Scale"
            },
            "Sporting Director": {
                "archetype": "Wenger",
                "required_tables": ["Decision Matrix", "Contract/Value"],
                "required_plots": ["Risk-Value Scatter", "Age Curve"],
                "focus": "Sustainability & Economics"
            }
            # ... Diğer 20 persona buraya 'Registry' olarak eklenir.
        }

    def get_persona_manifest(self, persona_name):
        return self.personas.get(persona_name, self.personas["Match Analyst"])
