import json

class MetricRegistry:
    def __init__(self):
        # metric_ontology.json'daki 47 aileyi ve 400+ takma adı (alias) tanır
        with open("canon/metric_ontology.json", "r") as f:
            self.ontology = json.load(f)

    def resolve(self, raw_name):
        # SportsBase kolonunu HP-CDL Kanonik ailesine bağlar
        for family_id, info in self.ontology['canonical_families'].items():
            if raw_name in info.get('aliases', []) or raw_name == family_id:
                return family_id
        return "UNKNOWN_SIGNAL"
