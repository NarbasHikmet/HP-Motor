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

# ============================================================
# MAIN ANALYSIS (SOVEREIGN PIPELINE)
# ============================================================
st.header("Sistemik Analiz")

orchestrator = SovereignOrchestrator()

try:
    sovereign_output = orchestrator.run(df)
except Exception as e:
    st.error(f"Sistemik analiz çalıştırılamadı: {e}")
    st.stop()

st.subheader("Sovereign Verdict")
st.json(sovereign_output)

# ============================================================
# INDIVIDUAL REVIEW MODULE
# ============================================================
st.divider()
st.header("Bireysel İnceleme (Individual Review)")

if "player_id" not in df.columns:
    st.warning(
        "Bu veri setinde 'player_id' sütunu yok.\n\n"
        "Bireysel inceleme için player_id zorunludur."
    )
    st.stop()

player_ids = sorted(df["player_id"].dropna().unique().tolist())

selected_player = st.selectbox(
    "Oyuncu Seç (player_id)",
    player_ids,
)

individual_engine = IndividualReviewEngine()

try:
    profile = individual_engine.build_player_profile(
        df=df,
        player_id=int(selected_player),
    )
except Exception as e:
    st.error(f"Bireysel analiz çalıştırılamadı: {e}")
    st.stop()

# ------------------------------------------------------------
# OUTPUT
# ------------------------------------------------------------
st.subheader("Özet (Summary)")
st.json(profile.summary)

st.subheader("Detaylı Metrikler")
metrics_df = pd.DataFrame(profile.metrics)
st.dataframe(metrics_df, use_container_width=True)

# ============================================================
# FOOTER
# ============================================================
st.divider()
st.caption(
    "HP Motor — Veri yoksa susar. "
    "Çelişki varsa uyarır. "
    "Geometri bozuksa alarm verir."
)