import streamlit as st
import pandas as pd
import sys
import os

# 1. ADIM: Sistemin mevcut klasörü tanımasını sağlıyoruz
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# 2. ADIM: Importlar (Bu aşamada hp_motor artık bir modül olarak tanınır)
from hp_motor.pipelines.run_analysis import SovereignOrchestrator
from hp_motor.agents.sovereign_agent import get_agent_verdict

# 3. ADIM: Arayüz Ayarları (Sadece bir kez yazılmalı)
st.set_page_config(page_title="HP MOTOR v5.0", layout="wide")
st.markdown("<style>.main { background-color: #000000; color: #FFD700; }</style>", unsafe_allow_html=True)

st.title("🛡️ HP MOTOR v5.0")
st.caption("Felsefe: Saper Vedere | Güç: Sovereign Intelligence")

# 4. ADIM: Motoru Ateşle
@st.cache_resource
def load_orchestrator():
    return SovereignOrchestrator()

orchestrator = load_orchestrator()

# 5. ADIM: Yan Menü ve Veri Yükleme
uploaded_file = st.sidebar.file_uploader("Sinyal (CSV) Yükle", type=['csv'])
persona = st.sidebar.selectbox("Persona", ["Match Analyst", "Scout", "Technical Director"])

if uploaded_file:
    # Veriyi oku (Ayraç ; ise ona göre ayarla)
    df = pd.read_csv(uploaded_file, sep=';')

    with st.spinner("Analiz ediliyor..."):
        analysis = orchestrator.execute_full_analysis(df)
        verdict = get_agent_verdict(analysis, persona)

    st.success(f"Analiz Tamamlandı: {len(df)} Satır İşlendi")
    st.warning(f"**Ajan Hükmü:** {verdict}")
else:
    st.info("Sinyal bekleniyor... Lütfen Atletico Madrid CSV dosyasını yükleyin.")
