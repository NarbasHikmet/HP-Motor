from __future__ import annotations

from typing import Any, Dict, Tuple
import math


class RegimeDetector:
    """
    H-Rejimi: Control vs Chaos.
    v1.0: Bayesyen güncellemenin basit, yanlışlanabilir sürümü.

    H-score 0..1:
      - 0.0 -> kontrol (yüksek düzen, düşük volatilite)
      - 1.0 -> kaos (yüksek geçiş, yüksek top kaybı, yüksek tempo)

    Event bazlı proxy sinyaller:
      - turnover (top kaybı)
      - transition (geçiş)
      - shot (şut)
      - pass risk (riskli pas)
      - duel intensity (ikili mücadele)
    """

    def __init__(self):
        # Prior: orta düzey kaos
        self.p_chaos = 0.5

    def calculate_h_score(self, event: Dict[str, Any]) -> Tuple[float, str, str]:
        et = str(event.get("event_type", "")).lower()

        # Likelihood proxy (falsifiable): olay türüne göre chaos kanıtı
        chaos_likelihood = 0.5
        if et in ("turnover", "ball_lost", "dispossessed"):
            chaos_likelihood = 0.78
        elif et in ("transition", "counter", "counterpress"):
            chaos_likelihood = 0.70
        elif et in ("shot", "dribble", "take_on"):
            chaos_likelihood = 0.62
        elif et in ("pass", "carry"):
            # risk flag varsa kaos artar
            chaos_likelihood = 0.55 + (0.10 if bool(event.get("is_risky")) else 0.0)
        elif et in ("foul", "duel", "tackle"):
            chaos_likelihood = 0.60

        # Bayes update (odds form)
        # posterior_odds = prior_odds * (L / (1-L))
        prior = float(self.p_chaos)
        prior_odds = prior / max(1e-6, (1.0 - prior))
        like_odds = chaos_likelihood / max(1e-6, (1.0 - chaos_likelihood))
        post_odds = prior_odds * like_odds
        post = post_odds / (1.0 + post_odds)

        # Smooth update to avoid oscillation
        self.p_chaos = 0.85 * self.p_chaos + 0.15 * post

        h = float(self.p_chaos)
        regime = "CHAOS" if h >= 0.60 else ("CONTROL" if h <= 0.40 else "MIXED")
        debug = f"RegimeDetector: event={et} like={chaos_likelihood:.2f} prior={prior:.2f} post={post:.2f} h={h:.2f} regime={regime}"
        return h, regime, debug