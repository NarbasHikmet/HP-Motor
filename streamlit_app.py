import streamlit as st
import pandas as pd
from engine.orchestrator import MasterOrchestrator

st.set_page_config(page_title="HP Motor v3", layout="wide")

st.title("🛡️ HP Motor v3 | Komuta Merkezi")
st.sidebar.markdown("### Sistem Durumu: **Aktif**")

uploaded_file = st.file_uploader("SportsBase CSV Dosyasını Yükle (Atletico / Monaco)", type=['csv'])

if uploaded_file:
    # Veri Okuma (SportsBase standardı ';' ayracı)
    df = pd.read_csv(uploaded_file, sep=';')
    
    # Engine Pipeline Çalıştır
    orchestrator = MasterOrchestrator()
    output = orchestrator.run_pipeline(df)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.header("📋 Veri Denetimi")
        st.metric("Veri Kapsamı", f"%{output['report']['coverage']*100:.1f}")
        status_color = "green" if output['report']['status'] == "HEALTHY" else "orange"
        st.markdown(f"SOT Durumu: :{status_color}[**{output['report']['status']}**]")
        
        if output['report']['issues']:
            for issue in output['report']['issues']:
                st.warning(issue)

    with col2:
        if output['success']:
            st.header("📊 İstihbarat Kesiti")
            st.json(output['results'])
            st.subheader("İşlenmiş Veri (Canonical Coords)")
            # 0.0 değerlerinin korunduğunu doğrulamak için tablo
            st.dataframe(output['data'][['code', 'action', 'x_std', 'y_std']].head(15))
