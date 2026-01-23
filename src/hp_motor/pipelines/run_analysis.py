class SovereignOrchestrator:
    def __init__(self, registry_path="registries/master_registry.yaml"):
        with open(registry_path, 'r') as f:
            self.registry = yaml.safe_load(f)

    def execute_full_analysis(self, artifact: RawArtifact, phase: str):
        # 1. Normalization (Registry'deki mapping'e göre)
        df = self._normalize_by_registry(artifact)
        
        # 2. Metric Calculation (Registry'deki listeye göre dinamik)
        results = {}
        for metric_spec in self.registry['metrics']:
            metric_id = metric_spec['id']
            # Eğer fonksiyona sahipse çalıştır, yoksa fallback kullan
            results[metric_id] = self._calculate_or_fallback(df, metric_spec)
            
        return self._create_analysis_object(results, phase)

    def _calculate_or_fallback(self, df, spec):
        # Registry'de tanımlı logic'i dinamik çağırır
        if self._has_required_fields(df, spec):
            return self._execute_logic(df, spec['full_logic'])
        return spec['fallback']
