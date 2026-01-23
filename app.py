import streamlit as st
import pandas as pd
# Karmaşık yollar bitti, doğrudan hp_motor'u görüyoruz
from hp_motor.pipelines.run_analysis import SovereignOrchestrator
from hp_motor.agents.sovereign_agent import get_agent_verdict

st.set_page_config(page_title="HP MOTOR v5.0", layout="wide")
st.title("🛡️ HP MOTOR v5.0")

orchestrator = SovereignOrchestrator()

uploaded_file = st.sidebar.file_uploader("Sinyal (CSV) Yükle", type=['csv'])
persona = st.sidebar.selectbox("Persona", ["Match Analyst", "Scout", "Technical Director"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    analysis = orchestrator.execute_full_analysis(df)
    verdict = get_agent_verdict(analysis, persona)
    
    st.success(f"Analiz Tamamlandı: {len(df)} Satır İşlendi")
    st.warning(f"**Ajan Hükmü:** {verdict}")
else:
    st.info("Sinyal bekleniyor...")
