import streamlit as st
import pandas as pd
from src.engine.valuation import ValuationEngine
from src.visual.plots import plot_pitch_tenebrism # Gelecek adımda eklenecek

# TEMA AYARLARI (Tesla & Tenebrism Mandate)
st.set_page_config(page_title="HP MOTOR v1.0", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFD700; }
    .stButton>button { background-color: #FFD700; color: black; }
    </style>
    """, unsafe_local_rules=True)

st.title("🛡️ HP MOTOR v1.0 | SOVEREIGN FOOTBALL OS")

# 1. INGESTION (Veri Girişi)
uploaded_file = st.sidebar.file_uploader("Veri Dosyasını Yükle (CSV/XLSX)", type=['csv', 'xlsx'])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    engine = ValuationEngine()
    
    # 2. ANALİZ
    df = engine.process_actions(df)
    df['hp_phase'] = df.apply(engine.get_phase, axis=1)
    
    # 3. PERSONA SEÇİMİ
    persona = st.sidebar.selectbox("Persona Görünümü", ["Analist", "Teknik Direktör", "Scout", "Sportif Direktör"])
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader(f"🏟️ Maç Panoraması - {persona} Gözüyle")
        # Buraya Tenebrism grafik fonksiyonu gelecek
        st.write(df.head(10)) # Geçici veri tablosu
        
    with col2:
        st.subheader("💡 Egemen Karar Çıktısı")
        if persona == "Analist":
            st.info("Kanıt Zinciri: SGA sapması +0.81. Model güveni %85.")
        elif persona == "Scout":
            st.warning("Rol Uyumu: Mezzala profilinde %92 eşleşme. Stres eşiği stabil.")
        else:
            st.success("Taktik Çözüm: F4 fazında enerji hattı aktif.")

else:
    st.write("Lütfen bir veri dosyası yükleyerek operasyonu başlatın.")
