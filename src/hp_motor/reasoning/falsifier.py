from __future__ import annotations

"""Popper Gate (Epistemolojik Temel) – HP Motor

Bu modülün görevi:
  1) Veri sözleşmesi (SOT) sağlıksızsa bunu *bloklayacak* veya *degraded* edecektir.
  2) Metrikler arasında basit çelişki sinyallerini işaretleyecektir.
  3) Girdi yokken, o girdiye bağlı modüllerin "sonuç" üretmesini engelleyecek altyapıyı sağlar.

Not:
  - Bu sürüm kural-tabanlıdır (bootstrap). Tahmin üretmez.
  - İleride: istatistiksel tutarlılık testleri / çapraz-kaynak mutabakatı (Opta↔Tracking) eklenecek.
"""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass(frozen=True)
class PopperAudit:
    status: str  # OK | DEGRADED | BLOCKED
    flags: List[Dict[str, Any]]
    notes: List[str]


class PopperFalsifier:
    """Epistemolojik filtre – minimal v1."""

    def verify(
        self,
        *,
        raw_df: Optional[pd.DataFrame],
        sot_report: Dict[str, Any],
        metrics: Dict[str, Any],
        evidence: Optional[Dict[str, Any]] = None,
        input_manifest: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        flags: List[Dict[str, Any]] = []
        notes: List[str] = []

        # 1) SOT sağlığı
        sot_status = (sot_report or {}).get("status", "UNKNOWN")
        if sot_status in {"DEGRADED", "BROKEN"}:
            flags.append({"code": "SOT_NOT_HEALTHY", "severity": "HIGH", "details": sot_report.get("issues", [])})
            notes.append("SOT sağlıksız: sonuçlar otomatik olarak ihtiyatlı işaretlendi.")

        # 2) Girdi manifesti (var olmayan girdiden üretme)
        # input_manifest örnek: {"has_csv": True, "has_mp4": False, ...}
        if input_manifest:
            if input_manifest.get("has_mp4") is False:
                # Video gerektiren iddiaları/çıktıları bloke etmeye hazır sinyal
                flags.append({"code": "NO_VIDEO_INPUT", "severity": "MED", "details": "MP4 yok: CV/spatial modüller kapalı olmalı."})

        # 3) Basit metrik çelişkileri (tahminsiz)
        # Örnek: PPDA çok düşük (çok pres) + DecisionSpeed çok düşük (çok yavaş) -> “çelişki sinyali”
        ppda = metrics.get("ppda", {}).get("value") if isinstance(metrics.get("ppda"), dict) else metrics.get("ppda")
        ds = metrics.get("decision_speed", {}).get("value") if isinstance(metrics.get("decision_speed"), dict) else metrics.get("decision_speed")

        if _is_number(ppda) and _is_number(ds):
            # Bu eşikler “çıktı üretmek” değil, sadece bayrak: ileride kalibre edilir
            if ppda < 8 and ds < 0.35:
                flags.append({"code": "METRIC_TENSION_PPDA_DECISIONSPEED", "severity": "LOW"})
                notes.append("Yüksek pres sinyali + düşük karar hızı: veri/bağlam kontrolü önerilir.")

        # 4) Raw DF kontrolü (no silent drops)
        if raw_df is None or not isinstance(raw_df, pd.DataFrame) or raw_df.empty:
            flags.append({"code": "NO_EVENTS_TABLE", "severity": "HIGH"})
            return asdict(PopperAudit(status="BLOCKED", flags=flags, notes=["Events tablosu yok."]))

        # Sonuç statüsü
        status = "OK"
        if any(f.get("severity") == "HIGH" for f in flags):
            status = "DEGRADED"
        if any(f.get("code") == "NO_EVENTS_TABLE" for f in flags):
            status = "BLOCKED"

        return asdict(PopperAudit(status=status, flags=flags, notes=notes))


def _is_number(x: Any) -> bool:
    try:
        return x is not None and float(x) == float(x)
    except Exception:
        return False