import streamlit as st
import pandas as pd
import sys
import os

# --- YOLU BURADA SABİTLİYORUZ (HİÇBİR ŞEYİ TAŞIMA) ---
# Bu kısım, Python'a 'src' klasörünün içine bakmasını söyler.
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

# Artık 'src' içindeki 'hp_motor' doğrudan import edilebilir.
try:
    from hp_motor.pipelines.run_analysis import SovereignOrchestrator
    from hp_motor.agents.sovereign_agent import get_agent_verdict
except ImportError as e:
    st.error(f"Hala bulunamıyor! Hata: {e}")
    st.info(f"Sistem şu an buraya bakıyor: {src_path}")
    st.stop()

# --- ARAYÜZ ---
st.set_page_config(page_title="HP MOTOR v5.0", layout="wide")
st.title("🛡️ HP MOTOR v5.0")

@st.cache_resource
def load_orchestrator():
    return SovereignOrchestrator()

orchestrator = load_orchestrator()

# --- ANALİZ PANELİ ---
uploaded_file = st.sidebar.file_uploader("Atletico Madrid CSV Yükle", type=['csv'])
persona = st.sidebar.selectbox("Persona", ["Match Analyst", "Scout", "Technical Director"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    with st.spinner("Sovereign Intelligence İşleniyor..."):
        analysis = orchestrator.execute_full_analysis(df)
        verdict = get_agent_verdict(analysis, persona)
    
    st.success(f"Analiz Tamamlandı: {len(df)} Satır İşlendi")
    st.warning(f"**Ajan Hükmü:** {verdict}")
else:
    st.info("Sinyal bekleniyor... Lütfen CSV dosyasını yükleyin.")
