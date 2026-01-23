import streamlit as st
import pandas as pd
import numpy as np
import sys
import os
import re

# 1. YOL VE PAKET TANIMLAMA
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from hp_motor.pipelines.run_analysis import SovereignOrchestrator
    from hp_motor.agents.sovereign_agent import get_agent_verdict
except ImportError:
    st.error("Kritik Hata: 'src/hp_motor' yolları doğrulanamadı.")
    st.stop()

# --- YENİ: SEMANTİK SÖZLÜK (Gönderdiğin veriden türetildi) ---
TAG_RULES = {
    "PHASE_TRANSITION": ["gecis", "geçiş", "counter", "transition", "fast break"],
    "PHASE_DEFENSIVE": ["savunma", "defans", "defensive", "block", "baski", "baskı"],
    "PHASE_OFFENSIVE": ["hucum", "hücum", "offensive", "attack", "build up", "pozisyon"],
}

# --- ARAYÜZ ---
st.set_page_config(page_title="HP MOTOR v5.0", layout="wide")
st.title("🛡️ HP MOTOR v5.0 | SEMANTIC INTELLIGENCE")

@st.cache_resource
def load_orchestrator():
    return SovereignOrchestrator()

orchestrator = load_orchestrator()

# --- YAN MENÜ ---
uploaded_files = st.sidebar.file_uploader("Sinyalleri Yükle (Toplu)", accept_multiple_files=True)
persona = st.sidebar.selectbox("Persona", ["Match Analyst", "Scout", "Technical Director"])

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.expander(f"📄 İşleniyor: {uploaded_file.name}", expanded=True):
            file_name_lower = uploaded_file.name.lower()
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            
            # --- 1. SEMANTİK ANALİZ (Dosya isminden anlam çıkarma) ---
            detected_phase = "GENERIC_PHASE"
            for phase, keywords in TAG_RULES.items():
                if any(k in file_name_lower for k in keywords):
                    detected_phase = phase
                    break

            # --- 2. VERİ OKUMA ---
            try:
                if file_ext == '.csv':
                    try: df_raw = pd.read_csv(uploaded_file, sep=';')
                    except: 
                        uploaded_file.seek(0)
                        df_raw = pd.read_csv(uploaded_file, sep=',')
                elif file_ext in ['.xlsx', '.xls']:
                    df_raw = pd.read_excel(uploaded_file).reset_index()
                elif file_ext == '.mp4':
                    st.video(uploaded_file)
                    df_raw = pd.DataFrame([{"visual": "video_stream"}])
                else:
                    df_raw = pd.DataFrame([{"raw": "document"}])

                # --- 3. AKILLI ŞEMA NORMALİZASYONU ---
                # Artık sadece 0 koymuyoruz, bulduğumuz PHAS'i ve CODE'u enjekte ediyoruz
                REQUIRED_MAP = {
                    'start': 0.0, 'end': 0.0, 'pos_x': 50.0, 'pos_y': 50.0,
                    'code': detected_phase, # 'code' hatasını isme göre çözüyoruz
                    'event_type': 'semantic_signal',
                    'timestamp': 0.0
                }

                for col, val in REQUIRED_MAP.items():
                    if col not in df_raw.columns:
                        df_raw[col] = val

                # --- 4. ANALİZ ---
                with st.spinner("Sovereign Intelligence İşleniyor..."):
                    analysis = orchestrator.execute_full_analysis(df_raw)
                    verdict = get_agent_verdict(analysis, persona)
                
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.metric("Semantik Güç", f"{detected_phase}")
                    st.caption(f"Güven: %{int(analysis.get('confidence', {}).get('confidence', 0.85)*100)}")
                with c2:
                    st.warning(f"**Sovereign Verdict:** {verdict}")

            except Exception as e:
                st.error(f"Dosya analiz edilemedi: {e}")
else:
    st.info("Sinyal bekleniyor...")
