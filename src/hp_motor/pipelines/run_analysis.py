import pandas as pd
from src.hp_motor.reasoning.uncertainty import UncertaintyEngine
from src.hp_motor.engine.compute.cognitive import CognitiveEngine
from src.hp_motor.engine.compute.temporal import TemporalEngine
from src.hp_motor.engine.compute.behavioral import BehavioralEngine

class SovereignOrchestrator:
    def __init__(self):
        self.uncertainty = UncertaintyEngine()
        self.cognitive = CognitiveEngine()
        self.temporal = TemporalEngine()
        self.behavioral = BehavioralEngine()

    def execute_full_analysis(self, raw_data):
        audit = self.uncertainty.calculate_confidence(raw_data)
        results = {
            "confidence": audit,
            "momentum": self.temporal.detect_regime_shifts(raw_data),
            "trauma_loops": self.behavioral.analyze_trauma_loops(raw_data),
            "cognitive_speed": self.cognitive.analyze_decision_speed(raw_data)
        }
        return results
