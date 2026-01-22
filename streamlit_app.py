import streamlit as st
import pandas as pd
from engine.orchestrator import MasterOrchestrator

st.set_page_config(page_title="HP Motor v1.0", layout="wide")

# Caravaggio UI Teması
st.markdown("""
    <style>
    .main { background-color: #050505; color: #ffffff; }
    .stMetric { background-color: #111111; padding: 15px; border-radius: 5px; border-left: 5px solid #FFD700; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ HP Motor v1.0 | Sovereign Intelligence")

uploaded_file = st.file_uploader("SportsBase / CSV Verisi Yükle", type=['csv'])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    
    engine = MasterOrchestrator()
    output = engine.run_analysis(df)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("📋 Veri Audit")
        st.metric("Veri Sağlığı", f"%{output['report']['health_score']*100:.1f}")
        st.write(f"Durum: **{output['report']['status']}**")

    with col2:
        st.header("📊 Kanıt Zinciri (Claims)")
        for claim in output['claims']:
            with st.expander(f"Hipotez: {claim['hypothesis']}"):
                st.write(f"**Kanıtlar:** {', '.join(claim['evidence_metrics'])}")
                st.warning(f"**Yanlışlama Testi:** {claim['falsification_test']}")
        
        st.subheader("İşlenmiş Veri Kesiti")
        st.dataframe(output['data'].head(10))
