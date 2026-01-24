# ============================================================
# HP MOTOR — STREAMLIT APPLICATION
# Canonical, src-layout safe, CI & Android compatible
# ============================================================

import sys
from pathlib import Path

# ------------------------------------------------------------
# SRC-LAYOUT BOOTSTRAP (NO ASSUMPTIONS)
# ------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if SRC.exists():
    sys.path.insert(0, str(SRC))

# ------------------------------------------------------------
# STANDARD LIBS
# ------------------------------------------------------------
import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# HP MOTOR IMPORTS
# ------------------------------------------------------------
from hp_motor.pipelines.run_analysis import SovereignOrchestrator
from hp_motor.modules.individual_review import IndividualReviewEngine

# ============================================================
# STREAMLIT CONFIG
# ============================================================
st.set_page_config(
    page_title="HP Motor",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("HP Motor — Sovereign Analysis Engine")

# ============================================================
# FILE UPLOAD
# ============================================================
st.sidebar.header("Veri Girişi")

uploaded_file = st.sidebar.file_uploader(
    "CSV veri dosyası yükle",
    type=["csv"],
)

if uploaded_file is None:
    st.info("Analiz başlatmak için bir CSV dosyası yükle.")
    st.stop()

# ============================================================
# LOAD DATA
# ============================================================
try:
    df = pd.read_csv(uploaded_file)
except Exception as e:
    st.error(f"CSV okunamadı: {e}")
    st.stop()

st.success("Veri başarıyla yüklendi.")
st.caption(f"Satır: {len(df)} | Kolon: {len(df.columns)}")

# ============================================================
# CONTROL PANEL
# ============================================================
st.sidebar.divider()
st.sidebar.header("Analiz Ayarları")
phase = st.sidebar.selectbox("Phase", ["open_play", "set_piece", "transition"], index=0)
role = st.sidebar.selectbox("Rol", ["mezzala", "pivot", "winger_solver", "cb", "fb"], index=0)

# ============================================================
# MAIN ANALYSIS (SOVEREIGN PIPELINE)
# ============================================================
st.header("Sistemik Analiz (Sovereign)")

orchestrator = SovereignOrchestrator()

try:
    sovereign_output = orchestrator.run(df, phase=phase, role=role)
except Exception as e:
    st.error(f"Sistemik analiz çalıştırılamadı: {e}")
    st.stop()

status = sovereign_output.get("status", "UNKNOWN")
confidence = (sovereign_output.get("evidence_graph") or {}).get("overall_confidence", "unknown")
st.subheader(f"Durum: {status} | Güven: {confidence}")

with st.expander("Diagnostics (neden / sınırlar / kalite)", expanded=(status != "OK")):
    st.json(sovereign_output.get("diagnostics", {}))

with st.expander("Evidence Graph (hüküm değil: gerekçe)", expanded=True):
    st.json(sovereign_output.get("evidence_graph", {}))

st.subheader("Metrikler")
st.dataframe(pd.DataFrame(sovereign_output.get("metrics", [])), use_container_width=True)

st.subheader("Tablolar")
tables = sovereign_output.get("tables", {}) or {}
if not tables:
    st.info("Tablo üretilmedi.")
else:
    for k, v in tables.items():
        st.markdown(f"**{k}**")
        try:
            st.dataframe(v, use_container_width=True)
        except Exception:
            st.write(v)

st.subheader("Listeler / Bullet çıktılar")
lists_out = sovereign_output.get("lists", {}) or {}
if not lists_out:
    st.info("Liste üretilmedi.")
else:
    for k, v in lists_out.items():
        st.markdown(f"**{k}**")
        st.write(v)

st.subheader("Figürler")
figs = sovereign_output.get("figure_objects", {}) or {}
if not figs:
    st.info("Figür üretilmedi (x/y kolonu yoksa beklenir).")
else:
    for k, fig in figs.items():
        st.markdown(f"**{k}**")
        try:
            st.pyplot(fig, clear_figure=False, use_container_width=True)
        except Exception:
            st.write(fig)

# ============================================================
# INDIVIDUAL REVIEW + ROLE MISMATCH ALARM
# ============================================================
st.divider()
st.header("Bireysel İnceleme + Rol Uyumsuzluğu Alarmı (HP v22.x)")

if "player_id" not in df.columns:
    st.warning("Bu veri setinde 'player_id' sütunu yok. Bireysel inceleme için player_id zorunludur.")
    st.stop()

player_ids = sorted(df["player_id"].dropna().unique().tolist())
if len(player_ids) == 0:
    st.warning("player_id kolonunda geçerli değer yok.")
    st.stop()

selected_player = st.selectbox("Oyuncu Seç (player_id)", player_ids)

st.subheader("Rol Uyumsuzluğu Checklist Girdileri (EVET/HAYIR)")
st.caption("Bilinmiyorsa boş bırak: sistem konservatif (yarım risk) puanlar.")

def _ans(label: str, key: str) -> str:
    return st.selectbox(label, ["BILINMIYOR", "EVET", "HAYIR"], index=0, key=key)

alarm_answers = {
    "q1": _ans("1) Birincil rol saha planında net mi?", "q1"),
    "q2": _ans("2) Oyuncu çizgiye hapsediliyor mu?", "q2"),
    "q3": _ans("3) Oyuncu izole 1v2–1v3'e itiliyor mu?", "q3"),
    "q4": _ans("4) Top aldığı bölgeler verimli bölgeyle örtüşüyor mu?", "q4"),
    "q5": _ans("5) Aynı koridorda duvar/istasyon var mı?", "q5"),
    "q6": _ans("6) Overlap/underlap desteği planlı mı?", "q6"),
    "q7": _ans("7) 9 numara pinning yapıyor mu?", "q7"),
    "q8": _ans("8) Ters kanat arka direk koşusu var mı?", "q8"),
    "q9": _ans("9) İlk 20 dk hedefli 3+ temas aldı mı?", "q9"),
    "q10": _ans("10) Sürekli kapalı vücutla mı alıyor?", "q10"),
    "q11": _ans("11) Aldığı anlarda ikinci opsiyon var mı?", "q11"),
    "q12": _ans("12) Yük yönetimi planlı mı?", "q12"),
    "q13": _ans("13) Temas yoğunluğu profile göre ayarlı mı?", "q13"),
    "q14": _ans("14) Rol iletişimi/güven çerçevesi kuruldu mu?", "q14"),
}

st.subheader("Canlı Maç İçi Tetikleyiciler")
st.caption("2+ tetikleyici görülürse alarm seviyesi bir kademe yükselir.")
t0 = st.checkbox("10 dakikada 2+ kez 1v2/1v3'e zorlanıyor", value=False)
t1 = st.checkbox("Top kaybı sonrası geri koşu/itiraz artıyor", value=False)
t2 = st.checkbox("Her pozisyonda çizgiye sıkışma + geri pas zorunluluğu", value=False)
t3 = st.checkbox("Duvar yokluğu: ters tarafa şişirme / düşük kaliteli şut", value=False)
t4 = st.checkbox("Bek desteği yok; sürekli dur-kalk (yük artışı)", value=False)
alarm_live = [t0, t1, t2, t3, t4]

engine = IndividualReviewEngine()

try:
    profile = engine.build_player_profile(
        df=df,
        player_id=int(selected_player),
        role_id=role,
        alarm_answers=alarm_answers,  # type: ignore
        alarm_live_triggers=alarm_live,
        context={},  # v22 şablon alanları için opsiyonel meta
    )
except Exception as e:
    st.error(f"Bireysel analiz çalıştırılamadı: {e}")
    st.stop()

st.subheader("Bireysel Özet")
st.json(profile.summary)

with st.expander("Bireysel Oyuncu Analizi v22 (Template)", expanded=False):
    st.markdown(profile.player_analysis_markdown)

with st.expander("Scouting Card v22 (Template)", expanded=False):
    st.markdown(profile.scouting_card_markdown)

with st.expander("Rol Uyumsuzluğu Alarm Checklist (Markdown)", expanded=True):
    st.markdown(profile.role_mismatch_alarm_markdown)

with st.expander("Rol Uyumsuzluğu Alarm (Structured)", expanded=False):
    st.json(profile.role_mismatch_alarm)

with st.expander("Diagnostics", expanded=False):
    st.json(profile.diagnostics)

st.subheader("Detaylı Metrikler")
st.dataframe(pd.DataFrame(profile.metrics), use_container_width=True)

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption("HP Motor — Veri yoksa susar. Çelişki varsa uyarır. Bağlam yanlışsa alarm verir.")