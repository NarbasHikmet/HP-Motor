class CanonMetricRegistry:
    """
    Runtime registry for canonical metrics
    """

    def __init__(self):
        self._metrics = {}

    def register_bulk(self, metric_specs: dict):
        for k, v in metric_specs.items():
            self._metrics[k] = v

    def get(self, metric_id: str):
        return self._metrics.get(metric_id)

    def list_metrics(self):
        return list(self._metrics.keys())