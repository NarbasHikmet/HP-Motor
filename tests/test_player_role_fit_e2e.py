import pandas as pd

from hp_motor.pipelines.run_analysis import SovereignOrchestrator


def test_player_role_fit_e2e_runs():
    df = pd.DataFrame({
        "player_id": ["p1"] * 5,
        "minutes": [90, 90, 90, 90, 90],
        "xT": [0.3, 0.4, 0.2, 0.35, 0.25],
        "ppda": [10, 12, 11, 9, 13],
        "prog_carries_90": [4, 3, 5, 4, 4],
        "line_break_passes_90": [2, 3, 2, 4, 3],
        "half_space_receives_90": [6, 7, 5, 8, 6],
        "turnover_danger_90": [0.8, 1.1, 0.7, 0.9, 1.0],
        "x": [30, 40, 50, 60, 70],
        "y": [20, 30, 40, 25, 35],
    })

    orch = SovereignOrchestrator()
    out = orch.execute("player_role_fit", raw_df=df, entity_id="p1", role="Mezzala")

    assert out["status"] == "OK"
    assert "metrics" in out and len(out["metrics"]) >= 2
    assert "evidence_graph" in out
    assert "deliverables" in out
    assert "figures" in out
    assert "figure_objects" in out
    assert "tables" in out
    assert "lists" in out