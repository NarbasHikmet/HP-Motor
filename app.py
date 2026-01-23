import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

# 1. ADIM: YOL VE PAKET TANIMLAMA
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from hp_motor.pipelines.run_analysis import SovereignOrchestrator
    from hp_motor.agents.sovereign_agent import get_agent_verdict
except ImportError:
    st.error("Kritik Hata: 'src/hp_motor' yolları doğrulanamadı. Klasör ismini kontrol edin.")
    st.stop()

# --- ARAYÜZ AYARLARI ---
st.set_page_config(page_title="HP MOTOR v5.0", layout="wide")
st.title("🛡️ HP MOTOR v5.0 | BULK INTELLIGENCE")

@st.cache_resource
def load_orchestrator():
    return SovereignOrchestrator()

orchestrator = load_orchestrator()

# --- HP MOTOR ALTIN ŞEMA (Zorunlu Kolonlar) ---
REQUIRED_COLS = ['start', 'end', 'pos_x', 'pos_y', 'event_type', 'team_name', 'player_name', 'timestamp']

# --- YAN MENÜ ---
uploaded_files = st.sidebar.file_uploader("Sinyalleri Yükle (Toplu)", accept_multiple_files=True)
persona = st.sidebar.selectbox("Analiz Personası", ["Match Analyst", "Scout", "Technical Director"])

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.expander(f"📄 Dosya İşleniyor: {uploaded_file.name}", expanded=True):
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            df_raw = None

            # --- 1. VERİ OKUMA ---
            try:
                if file_ext == '.csv':
                    try: df_raw = pd.read_csv(uploaded_file, sep=';')
                    except: 
                        uploaded_file.seek(0)
                        df_raw = pd.read_csv(uploaded_file, sep=',')
                elif file_ext in ['.xlsx', '.xls']:
                    df_raw = pd.read_excel(uploaded_file)
                elif file_ext == '.mp4':
                    st.video(uploaded_file)
                    df_raw = pd.DataFrame([{"visual_signal": "video_frame"}])
                else:
                    df_raw = pd.DataFrame([{"signal": "document_data"}])

                # --- 2. ZORUNLU ŞEMA ENJEKSİYONU (KeyError: 'start' Çözümü) ---
                # Motorun hata vermemesi için eksik tüm kolonları değerleriyle birlikte zorla ekliyoruz
                for col in REQUIRED_COLS:
                    if col not in df_raw.columns:
                        if col in ['start', 'end', 'timestamp']:
                            df_raw[col] = 0.0  # Zaman bazlı olanlara sayısal 0
                        elif col in ['pos_x', 'pos_y']:
                            df_raw[col] = 0.0  # Koordinatlara 0
                        else:
                            df_raw[col] = "N/A" # Metin bazlılara N/A

                # Veriyi motorun beklediği veri tipine (float) zorluyoruz
                df_raw['start'] = df_raw['start'].astype(float)

                # --- 3. ANALİZ MOTORU ---
                with st.spinner("Analiz ediliyor..."):
                    # Motorun içindeki pipelines/run_analysis.py artık 'start'ı bulacak
                    analysis = orchestrator.execute_full_analysis(df_raw)
                    verdict = get_agent_verdict(analysis, persona)
                
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.metric("Sinyal Gücü", f"{int(analysis.get('confidence', {}).get('confidence', 0)*100)}%")
                with c2:
                    st.warning(f"**Sovereign Verdict:** {verdict}")

            except Exception as e:
                st.error(f"Bu dosya işlenirken bir hata oluştu: {e}")
else:
    st.info("Sinyal bekleniyor... Lütfen dosyaları yükleyin.")
