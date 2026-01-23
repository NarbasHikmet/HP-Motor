from __future__ import annotations

from typing import Dict, Any, List
import pandas as pd


class ListFactory:
    # --- existing style: keep simple, deterministic

    def mezzala_tasks_pass_fail(self, metric_map: Dict[str, float]) -> List[Dict[str, Any]]:
        xt = float(metric_map.get("xt_value", 0.0) or 0.0)
        prog = float(metric_map.get("progressive_carries_90", 0.0) or 0.0)
        lb = float(metric_map.get("line_break_passes_90", 0.0) or 0.0)
        risk = float(metric_map.get("turnover_danger_index", 0.0) or 0.0)

        return [
            {"task": "Half-space threat contribution", "pass": xt >= 0.35, "signal": xt},
            {"task": "Progressive carry volume", "pass": prog >= 3.0, "signal": prog},
            {"task": "Line-break passing", "pass": lb >= 2.5, "signal": lb},
            {"task": "Turnover discipline", "pass": risk <= 1.0, "signal": risk},
        ]

    def top_sequences_by_xt_involvement(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        # v1: if sequence_id exists, aggregate xt_value
        if df is None or df.empty:
            return []
        if "sequence_id" not in df.columns:
            return [{"note": "sequence_id yok; top_sequences üretilemedi (v1)."}]

        col = "xt_value" if "xt_value" in df.columns else ("xT" if "xT" in df.columns else None)
        if col is None:
            return [{"note": "xt_value/xT yok; top_sequences üretilemedi (v1)."}]

        tmp = df.copy()
        tmp[col] = pd.to_numeric(tmp[col], errors="coerce").fillna(0.0)
        g = tmp.groupby("sequence_id")[col].sum().sort_values(ascending=False).head(8)
        return [{"sequence_id": str(k), "xt_sum": float(v)} for k, v in g.items()]

    def top_turnovers_by_danger(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []
        col = "turnover_danger_index" if "turnover_danger_index" in df.columns else (
            "turnover_danger_90" if "turnover_danger_90" in df.columns else None
        )
        if col is None:
            return [{"note": "turnover danger kolonu yok; top_turnovers üretilemedi (v1)."}]

        tmp = df.copy()
        tmp[col] = pd.to_numeric(tmp[col], errors="coerce")
        tmp = tmp[tmp[col].notna()].sort_values(col, ascending=False).head(10)

        keep = [c for c in ["player_id", "minute", "second", "x", "y", col] if c in tmp.columns]
        out = []
        for _, r in tmp[keep].iterrows():
            out.append({k: (float(r[k]) if k == col else r[k]) for k in keep})
        return out

    # -------------------------
    # Dossier lists
    # -------------------------
    def strengths_list(self, metric_map: Dict[str, float]) -> List[str]:
        strengths = []
        if float(metric_map.get("xt_value", 0.0) or 0.0) >= 0.5:
            strengths.append("Threat üretimi (xT) üst bant")
        if float(metric_map.get("progressive_carries_90", 0.0) or 0.0) >= 4:
            strengths.append("Topu dikine taşıma hacmi yüksek")
        if float(metric_map.get("line_break_passes_90", 0.0) or 0.0) >= 3:
            strengths.append("Hat kırıcı pas kapasitesi iyi")
        if float(metric_map.get("contextual_awareness_score", 0.0) or 0.0) >= 0.65:
            strengths.append("Bilişsel hazırlık (awareness) güçlü")
        return strengths or ["Belirgin güçlü sinyal yok (v1)."]

    def risks_list(self, metric_map: Dict[str, float]) -> List[str]:
        risks = []
        if float(metric_map.get("turnover_danger_index", 0.0) or 0.0) >= 1.0:
            risks.append("Top kaybı tehlikesi yüksek (turnover danger)")
        if float(metric_map.get("decision_speed_mean_s", 9.9) or 9.9) >= 0.75:
            risks.append("Karar hızı yavaş (decision speed)")
        return risks or ["Belirgin risk sinyali yok (v1)."]

    def watchlist_prompts(self, role: str) -> List[str]:
        r = (role or "").lower().strip()
        base = [
            "İlk kontrol öncesi omuz kontrolü var mı? (scanning proxy)",
            "Baskı altında ilk aksiyon: geri mi, yan mı, ileri mi?",
            "Half-space alımında gövde açısı (open/closed) gözlenmeli.",
        ]
        if r in ("mezzala", "8", "cm", "box_to_box"):
            base += [
                "Üçüncü adam bağlantısı kuruyor mu?",
                "Half-space -> merkez kırılımını ne sıklıkla deniyor?",
            ]
        if r in ("pivot", "6", "dm"):
            base += [
                "Yarım dönüş (half-turn) ile baskı kırıyor mu?",
                "Tek/çift temasla yön değiştiriyor mu?",
            ]
        return base