from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import datetime as _dt

import pandas as pd

from hp_motor.core.cognition import extract_cognitive_signals, extract_orientation_signals


# ============================================================
# Data models (stable contract)
# ============================================================

@dataclass
class PlayerProfile:
    player_id: int
    summary: Dict[str, Any]
    metrics: List[Dict[str, Any]]
    diagnostics: Dict[str, Any]
    # v22 additions: canonical artifacts
    individual_analysis_markdown: str
    scouting_card_markdown: str


# ============================================================
# Role requirements (extensible)
# ============================================================

@dataclass
class RoleRequirements:
    role_id: str
    # “conditions / dependencies” section of scouting card
    need_overlap: str = "BILINMIYOR"
    need_wall_station: str = "BILINMIYOR"
    need_9_anchor: str = "BILINMIYOR"
    need_far_post_runner: str = "BILINMIYOR"
    # guidance defaults
    usage_defaults: Tuple[str, str, str] = (
        "Rol bağlamını netleştir (ilk opsiyon / ikinci opsiyon).",
        "Topu alacağı bölgeyi önceden tasarla (half-space/çizgi/merkez).",
        "Baskı koşullarını planla (duvar istasyonu / üçüncü adam / tempo).",
    )


ROLE_REQUIREMENTS: Dict[str, RoleRequirements] = {
    # Wingers
    "winger_solver": RoleRequirements(
        role_id="winger_solver",
        need_overlap="EVET",
        need_wall_station="EVET",
        need_9_anchor="EVET",
        need_far_post_runner="EVET",
        usage_defaults=(
            "Bek bindirmesiyle iç koridoru aç; kanadı izole etme.",
            "10/8 duvar istasyonu ile ver-kaç opsiyonu kur.",
            "9 numara sabitlemesiyle half-space'e ikinci dalgayı planla.",
        ),
    ),
    # Midfield
    "mezzala": RoleRequirements(
        role_id="mezzala",
        need_overlap="DURUMA_BAGLI",
        need_wall_station="EVET",
        need_9_anchor="DURUMA_BAGLI",
        need_far_post_runner="DURUMA_BAGLI",
        usage_defaults=(
            "Half-space bağlantısını kur; üçüncü adamı görünür kıl.",
            "Top alımında açık vücut (half-turn) şartlarını üret.",
            "Risk yönetimi: top kaybı bölgelerini disipline et.",
        ),
    ),
    "pivot": RoleRequirements(
        role_id="pivot",
        need_overlap="DURUMA_BAGLI",
        need_wall_station="HAYIR",
        need_9_anchor="DURUMA_BAGLI",
        need_far_post_runner="HAYIR",
        usage_defaults=(
            "İlk pas hattını sabitle; baskı kırma açısını tasarla.",
            "Tek/çift temas kararlarını netleştir (tempo kontrol).",
            "Merkez kaybı riskini azalt (gölge pres / yönlendirme).",
        ),
    ),
    # Defenders
    "cb": RoleRequirements(
        role_id="cb",
        need_overlap="HAYIR",
        need_wall_station="DURUMA_BAGLI",
        need_9_anchor="HAYIR",
        need_far_post_runner="HAYIR",
        usage_defaults=(
            "İlk kontrol sonrası pas açısı üret (body orientation).",
            "Arkaya koşu tehdidinde pozisyon disiplinini koru.",
            "Çıkış pası için 6 numara istasyonu ile bağlantı kur.",
        ),
    ),
    "fb": RoleRequirements(
        role_id="fb",
        need_overlap="EVET",
        need_wall_station="DURUMA_BAGLI",
        need_9_anchor="DURUMA_BAGLI",
        need_far_post_runner="EVET",
        usage_defaults=(
            "Bindirme zamanlamasını 10/8 ile senkronize et.",
            "Geri koşu ve ikili mücadele yoğunluğunu maç planına böl.",
            "Arka direk koşusunu tetiklemek için erken orta penceresi aç.",
        ),
    ),
}


# ============================================================
# Template loader + renderer (no external deps)
# ============================================================

def _load_template(rel_path: str) -> str:
    # src/hp_motor/modules/individual_review.py -> src/hp_motor/templates/*.md
    base = Path(__file__).resolve().parent.parent  # hp_motor/
    tpl = base / "templates" / rel_path
    try:
        return tpl.read_text(encoding="utf-8")
    except Exception:
        # Hard fallback (never crash analysis due to template I/O)
        return ""


def _render_template(template_text: str, ctx: Dict[str, Any]) -> str:
    out = template_text or ""
    for k, v in (ctx or {}).items():
        out = out.replace("{{" + k + "}}", "" if v is None else str(v))
    # any remaining placeholders -> keep readable
    return out


# ============================================================
# Individual Review Engine (v22)
# ============================================================

class IndividualReviewEngine:
    """
    HP ENGINE v22.x — Individual Analysis (Permanent Module)

    Goals:
      1) Produce structured metrics + diagnostics (data truth).
      2) Produce canonical markdown artifacts:
         - Player Analysis Template (multi-section)
         - Scouting Card (one page)
      3) Be extensible by position/role requirements without rewriting templates.

    Epistemic rules:
      - Never fabricate missing numeric claims.
      - If signals missing -> DEGRADED/ABSTAINED with explicit reasons.
    """

    ENGINE_VERSION = "HP ENGINE v22.x"

    def build_player_profile(
        self,
        df: pd.DataFrame,
        player_id: int,
        *,
        meta: Optional[Dict[str, Any]] = None,
        role_id: str = "mezzala",
        identity: Optional[Dict[str, Any]] = None,
        per90: Optional[Dict[str, Any]] = None,
    ) -> PlayerProfile:
        meta = meta or {}
        identity = identity or {}
        per90 = per90 or {}

        # -------------------------
        # Hard gates
        # -------------------------
        if df is None or df.empty:
            md_analysis, md_card = self._render_from_minimum(
                player_id=player_id,
                meta=meta,
                role_id=role_id,
                status="ABSTAINED",
                reason="empty_df",
            )
            return PlayerProfile(
                player_id=int(player_id),
                summary={"status": "ABSTAINED", "reason": "empty_df", "confidence": "low"},
                metrics=[],
                diagnostics={"missing_columns": ["player_id"], "row_count_player": 0},
                individual_analysis_markdown=md_analysis,
                scouting_card_markdown=md_card,
            )

        if "player_id" not in df.columns:
            md_analysis, md_card = self._render_from_minimum(
                player_id=player_id,
                meta=meta,
                role_id=role_id,
                status="ABSTAINED",
                reason="missing_player_id_column",
            )
            return PlayerProfile(
                player_id=int(player_id),
                summary={"status": "ABSTAINED", "reason": "missing_player_id_column", "confidence": "low"},
                metrics=[],
                diagnostics={"missing_columns": ["player_id"], "row_count_player": 0},
                individual_analysis_markdown=md_analysis,
                scouting_card_markdown=md_card,
            )

        w = df[df["player_id"].astype(str) == str(player_id)].copy()
        if w.empty:
            md_analysis, md_card = self._render_from_minimum(
                player_id=player_id,
                meta=meta,
                role_id=role_id,
                status="ABSTAINED",
                reason="no_rows_for_player",
            )
            return PlayerProfile(
                player_id=int(player_id),
                summary={"status": "ABSTAINED", "reason": "no_rows_for_player", "confidence": "low"},
                metrics=[],
                diagnostics={"row_count_player": 0},
                individual_analysis_markdown=md_analysis,
                scouting_card_markdown=md_card,
            )

        diagnostics: Dict[str, Any] = {"row_count_player": int(len(w))}

        # -------------------------
        # Extract signals (existing core)
        # -------------------------
        cog = extract_cognitive_signals(w)
        ori = extract_orientation_signals(w)

        pressure_metrics, pressure_diag = self._pressure_conditioned_speed(w)
        diagnostics.update(pressure_diag)

        # -------------------------
        # Metrics (structured)
        # -------------------------
        metrics: List[Dict[str, Any]] = []

        if cog.decision_speed_mean_s is not None:
            metrics.append({"metric_id": "decision_speed_mean_s", "value": float(cog.decision_speed_mean_s), "unit": "sec"})
        if cog.scan_freq_10s is not None:
            metrics.append({"metric_id": "scan_freq_10s", "value": float(cog.scan_freq_10s), "unit": "hz"})
        if cog.contextual_awareness_score is not None:
            metrics.append({"metric_id": "contextual_awareness_score", "value": float(cog.contextual_awareness_score), "unit": "0..1"})
        metrics.append({"metric_id": "cognitive_note", "value": cog.note})

        if ori.defender_side_on_score is not None:
            metrics.append({"metric_id": "defender_side_on_score", "value": float(ori.defender_side_on_score), "unit": "0..1"})
        if ori.square_on_rate is not None:
            metrics.append({"metric_id": "square_on_rate", "value": float(ori.square_on_rate), "unit": "0..1"})
        if ori.channeling_to_wing_rate is not None:
            metrics.append({"metric_id": "channeling_to_wing_rate", "value": float(ori.channeling_to_wing_rate), "unit": "0..1"})
        metrics.append({"metric_id": "orientation_note", "value": ori.note})

        metrics.extend(pressure_metrics)

        # Map for template filling
        metric_map = self._metrics_to_map(metrics)

        # -------------------------
        # Summary bands (conservative)
        # -------------------------
        missing = []
        if cog.decision_speed_mean_s is None:
            missing.append("decision_speed_mean_s")
        if cog.scan_freq_10s is None and "scan_count_10s" not in w.columns:
            missing.append("scan_freq_10s")
        if cog.contextual_awareness_score is None:
            missing.append("contextual_awareness_score")

        confidence = "medium"
        if len(missing) >= 2:
            confidence = "low"
        if cog.contextual_awareness_score is not None and cog.contextual_awareness_score >= 0.75 and confidence != "low":
            confidence = "high"

        status = "OK" if len(missing) == 0 else "DEGRADED"
        if len(missing) == 3:
            status = "ABSTAINED"

        summary = {
            "status": status,
            "player_id": int(player_id),
            "confidence": confidence,
            "missing": missing,
            "headline": self._headline(cog.contextual_awareness_score, cog.decision_speed_mean_s, pressure_diag),
            "limits": [
                "Scanning proxy is indirect (event timestamps / provided scan columns).",
                "Body orientation proxy requires tracking/video; only column-based signals are used.",
            ],
        }

        # -------------------------
        # Canonical artifacts (v22 templates)
        # -------------------------
        md_analysis, md_card = self._build_v22_markdowns(
            player_id=int(player_id),
            meta=meta,
            identity=identity,
            per90=per90,
            role_id=role_id,
            status=status,
            confidence=confidence,
            missing=missing,
            metric_map=metric_map,
            diagnostics=diagnostics,
        )

        return PlayerProfile(
            player_id=int(player_id),
            summary=summary,
            metrics=metrics,
            diagnostics=diagnostics,
            individual_analysis_markdown=md_analysis,
            scouting_card_markdown=md_card,
        )

    # ============================================================
    # v22 Markdown builders
    # ============================================================

    def _build_v22_markdowns(
        self,
        *,
        player_id: int,
        meta: Dict[str, Any],
        identity: Dict[str, Any],
        per90: Dict[str, Any],
        role_id: str,
        status: str,
        confidence: str,
        missing: List[str],
        metric_map: Dict[str, Any],
        diagnostics: Dict[str, Any],
    ) -> Tuple[str, str]:
        analysis_tpl = _load_template("player_analysis_v22.md")
        card_tpl = _load_template("scouting_card_v22.md")

        today = meta.get("analysis_date") or _dt.date.today().isoformat()
        analyst = meta.get("analyst") or ""
        season = meta.get("season") or ""
        club = meta.get("club") or ""
        league = meta.get("league") or ""
        player_name = identity.get("player_name") or ""

        # Numeric core (per90) — do not fabricate; keep blanks if absent
        def _v(k: str) -> str:
            v = per90.get(k)
            return "" if v is None else str(v)

        # Build commentary that is *truthful* re missing
        numeric_commentary = self._numeric_profile_commentary(per90=per90, status=status, missing=missing)

        # Decision tree strings (derived if possible)
        top_actions = self._infer_top_actions_from_columns()
        under_pressure_behavior = self._infer_pressure_behavior(metric_map, diagnostics)

        # Tactical map placeholders (video/tracking often required)
        best_zones = identity.get("best_zones") or ""
        weak_zones = identity.get("weak_zones") or ""
        box_contribution_type = identity.get("box_contribution_type") or ""
        production_geometry = identity.get("production_geometry") or ""

        # Biomech section
        body_orientation_notes = self._body_orientation_notes(metric_map=metric_map, status=status)

        # Psych section placeholders (manual / scouting)
        # Kept empty by default to preserve template discipline.
        role_clarity_need = identity.get("role_clarity_need") or ""
        freedom_tolerance = identity.get("freedom_tolerance") or ""
        post_error_response = identity.get("post_error_response") or ""
        confidence_perf = identity.get("confidence_performance_relation") or ""

        # Coaching notes (role-based defaults)
        rr = ROLE_REQUIREMENTS.get(role_id, ROLE_REQUIREMENTS.get("mezzala", RoleRequirements(role_id=role_id)))

        how_to_use = "\n".join([f"- {x}" for x in rr.usage_defaults])
        how_not_to_use = identity.get("how_not_to_use") or ""
        system_support = identity.get("system_support_needs") or ""

        # Risks
        tactical_risks = identity.get("tactical_risks") or self._risk_tactical_default(role_id, metric_map)
        physical_risks = identity.get("physical_risks") or ""
        psych_risks = identity.get("psychological_risks") or ""

        # Fit (optional; keep blank unless provided)
        team_fit = identity.get("team_fit_score") or ""
        league_fit = identity.get("league_fit_score") or ""
        coach_fit = identity.get("coach_fit_note") or ""

        # Executive summary: conservative; do not assert beyond confidence
        exec_summary = identity.get("executive_summary") or self._executive_summary_default(
            role_id=role_id,
            status=status,
            confidence=confidence,
            metric_map=metric_map,
            missing=missing,
        )

        analysis_ctx = {
            # meta
            "player_name": player_name,
            "club": club,
            "league": league,
            "season": season,
            "analyst": analyst,
            "analysis_date": today,
            "engine_version": self.ENGINE_VERSION,
            # identity
            "age": identity.get("age") or "",
            "height_weight": identity.get("height_weight") or "",
            "dominant_foot": identity.get("dominant_foot") or "",
            "primary_position": identity.get("primary_position") or "",
            "secondary_positions": identity.get("secondary_positions") or "",
            "career_phase": identity.get("career_phase") or "",
            "one_liner_definition": identity.get("one_liner_definition") or "",
            # role
            "primary_role": identity.get("primary_role") or role_id,
            "secondary_role": identity.get("secondary_role") or "",
            "bad_roles": identity.get("bad_roles") or "",
            "role_freedom": identity.get("role_freedom") or "",
            # numeric per90
            "dribble_success": _v("dribble_success_pct"),
            "dribble_pctile": _v("dribble_success_pctile"),
            "turnovers": _v("turnovers_90"),
            "turnovers_pctile": _v("turnovers_pctile"),
            "xg": _v("xg_90"),
            "xg_pctile": _v("xg_pctile"),
            "xa": _v("xa_90"),
            "xa_pctile": _v("xa_pctile"),
            "key_passes": _v("key_passes_90"),
            "key_passes_pctile": _v("key_passes_pctile"),
            "shots": _v("shots_90"),
            "shots_pctile": _v("shots_pctile"),
            "numeric_profile_commentary": numeric_commentary,
            # biomech
            "somatotype": identity.get("somatotype") or "",
            "explosiveness": identity.get("explosiveness") or "",
            "max_speed": identity.get("max_speed") or "",
            "repeated_sprint": identity.get("repeated_sprint") or "",
            "stamina": identity.get("stamina") or "",
            "injury_history": identity.get("injury_history") or "",
            "body_orientation_notes": body_orientation_notes,
            # decision tree
            "top_actions": top_actions,
            "under_pressure_behavior": under_pressure_behavior,
            # tactical map
            "best_zones": best_zones,
            "weak_zones": weak_zones,
            "box_contribution_type": box_contribution_type,
            "production_geometry": production_geometry,
            # psych
            "role_clarity_need": role_clarity_need,
            "freedom_tolerance": freedom_tolerance,
            "post_error_response": post_error_response,
            "confidence_performance_relation": confidence_perf,
            # coaching notes
            "how_to_use": how_to_use,
            "how_not_to_use": how_not_to_use,
            "system_support_needs": system_support,
            # risks
            "tactical_risks": tactical_risks,
            "physical_risks": physical_risks,
            "psychological_risks": psych_risks,
            # fit
            "team_fit_score": team_fit,
            "league_fit_score": league_fit,
            "coach_fit_note": coach_fit,
            # final
            "executive_summary": exec_summary,
        }

        md_analysis = _render_template(analysis_tpl, analysis_ctx) if analysis_tpl else self._fallback_analysis_text(analysis_ctx, status, confidence, missing)

        # Scouting Card context (derived from same info)
        one_sentence_verdict = identity.get("one_sentence_verdict") or self._one_sentence_verdict_default(
            role_id=role_id, status=status, confidence=confidence
        )

        card_ctx = {
            "player_name": player_name,
            "club_league_season": " | ".join([x for x in [club, league, season] if x]),
            "position_role": " / ".join([x for x in [identity.get("primary_position") or "", identity.get("primary_role") or role_id] if x]),
            "dominant_foot": identity.get("dominant_foot") or "",
            "age_height_weight": " / ".join([x for x in [str(identity.get("age") or ""), identity.get("height_weight") or ""] if x]),
            "one_sentence_verdict": one_sentence_verdict,
            "xg": _v("xg_90"),
            "xa": _v("xa_90"),
            "key_passes": _v("key_passes_90"),
            "shots": _v("shots_90"),
            "dribble_success": _v("dribble_success_pct"),
            "turnovers": _v("turnovers_