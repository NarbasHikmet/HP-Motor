import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src.engine.valuation import ValuationEngine
from src.engine.ontology import HPOntology
from src.narrative.persona import PersonaEngine

# --- SOVEREIGN AESTHETIC MANDATE ---
st.set_page_config(page_title="HP MOTOR v1.0", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFD700; }
    [data-testid="stSidebar"] { background-color: #050505; border-right: 1px solid #FFD700; }
    h1, h2, h3 { color: #FFD700 !important; font-family: 'Courier New', Courier, monospace; }
    .stSelectbox label, .stFileUploader label { color: #FFD700 !important; }
    .stDataFrame { border: 1px solid #333; }
    </style>
""", unsafe_allow_html=True)

# --- INITIALIZATION ---
if 'engine' not in st.session_state:
    st.session_state.engine = ValuationEngine()
if 'ontology' not in st.session_state:
    st.session_state.ontology = HPOntology()

st.title("🛡️ HP MOTOR v1.0 | SOVEREIGN FOOTBALL OS")
st.caption("Felsefe: Saper Vedere | Estetik: Tenebrism | Güç: Tesla Edition")

# --- SIDEBAR: INGESTION & PERSONA ---
st.sidebar.header("📥 Ingestion & Control")
uploaded_file = st.sidebar.file_uploader("Veri Dosyasını (CSV/XLSX) Yükle", type=['csv', 'xlsx'])

persona_type = st.sidebar.selectbox(
    "🎭 Persona Seçimi", 
    ["Analist (Epistemik)", "Scout (Davranışsal)", "Teknik Direktör (Taktiksel)", "Sportif Direktör (Stratejik)"]
)

if uploaded_file:
    # Veri Yükleme (HP-CDL Ingestion)
    df = pd.read_csv(uploaded_file, sep=';') if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
    
    # 1. Analitik İşleme (Valuation Engine)
    processed_df = st.session_state.engine.process_match_data(df)
    
    # 2. Persona Görünümü (Narrative Engine)
    persona_engine = PersonaEngine(persona_type)
    narrative_output = persona_engine.generate_insight(processed_df)

    # --- MAIN DASHBOARD ---
    col1, col2 = st.columns([3, 1])

    with col1:
        st.subheader(f"🏟️ {persona_type} Katmanı: Enerji ve Aksiyon Akışı")
        # Tesla/Tenebrism Görselleştirme (Buraya plots.py fonksiyonu bağlanacak)
        st.write("Veri Aktif: Sinyaller işleniyor...")
        st.dataframe(processed_df.head(20), use_container_width=True)

    with col2:
        st.subheader("💡 Egemen Karar")
        st.markdown(f"**Durum:** `{narrative_output['status']}`")
        st.info(narrative_output['summary'])
        
        st.subheader("📉 Klinik Metrikler")
        st.metric("Model Güveni (Epistemic)", f"{narrative_output['confidence']}%")
        st.metric("SGA (Shot Goals Added)", processed_df['sga'].sum().round(2))

else:
    st.warning("Bekleniyor... Lütfen bir veri dosyası (Atletico Madrid - GS gibi) yükleyin.")
    st.info("Sistem, arka planda Sapolsky, Tesla ve Caravaggio prensiplerini aktive etmek için sinyal bekliyor.")
