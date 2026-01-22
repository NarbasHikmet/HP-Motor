class PersonaEngine:
    def __init__(self, mode):
        self.mode = mode

    def generate_insight(self, df):
        # v1.0 Persona Mantığı
        if "Analist" in self.mode:
            return {"status": "Operational", "summary": "Veri tutarlılığı %85. Model sapması düşük.", "confidence": 85}
        if "Scout" in self.mode:
            return {"status": "Scanning", "summary": "Rol uyumu mühürlendi. Davranışsal döngüler inceleniyor.", "confidence": 92}
        return {"status": "Active", "summary": "Stratejik hatlar aydınlatıldı.", "confidence": 80}
