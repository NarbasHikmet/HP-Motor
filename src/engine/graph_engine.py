import networkx as nx

class HPGraphEngine:
    """HP Motor v2.0 - Ontoloji ve İlişki Motoru"""
    def __init__(self):
        self.G = nx.DiGraph()
        self._initialize_sovereign_ontology()

    def _initialize_sovereign_ontology(self):
        # 1. Faz Düğümleri (The Canvas)
        self.G.add_node("F4: Incision", type="Phase", voltage_priority=1.0)
        
        # 2. Rol Düğümleri (The Personas)
        self.G.add_node("Mezzala", type="Role", signature="Half-Space Progression")
        
        # 3. İlişkiler (The Tesla Arcs)
        # Diyagramdaki 'Mezzala, Incision fazında aktiftir' bağlantısı:
        self.G.add_edge("Mezzala", "F4: Incision", relationship="Primary Operator")
        
    def get_contextual_weight(self, role, phase):
        """Rol ve Faz arasındaki ontolojik ağırlığı döndürür."""
        if self.G.has_edge(role, phase):
            return self.G[role][phase].get('weight', 1.0)
        return 0.0
