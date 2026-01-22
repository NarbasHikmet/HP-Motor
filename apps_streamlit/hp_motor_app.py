import streamlit as st
import pandas as pd
import numpy as np

# --- HP MOTOR v5.0 SOVEREIGN IMPORTS ---
# Artık kök dizindeki engine/ değil, src/hp_motor/ altındaki yeni yapıya bakıyoruz.
from src.hp_motor.core.cdl_models import EvidenceNode
from src.hp_motor.engine.compute.cognitive import CognitiveEngine
from src.hp_motor.engine.compute.temporal import TemporalEngine
from src.hp_motor.engine.compute.behavioral import BehavioralEngine
from src.hp_motor.reasoning.uncertainty import UncertaintyEngine
from src.hp_motor.viz.table_factory import HPTableFactory

# --- SOVEREIGN AESTHETICS (Tenebrism & Tesla) ---
st.set_page_config(page_title="HP MOTOR v5.0", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFD700; }
    .stSidebar { background-color: #050505; color: #FFD700; border-right: 1px solid #333; }
    h1, h2, h3 { color: #FFD700 !important; font-family: 'Courier New', Courier, monospace; }
    .stMetric { background-color: #111; border: 1px solid #FFD700; padding: 10px; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ HP MOTOR v5.0 | SOVEREIGN FOOTBALL OS")
st.caption("Felsefe: Saper Vedere | Estetik: Tenebrism | Güç: Tesla Edition")

# --- INITIALIZATION ---
cog_engine = CognitiveEngine()
temp_engine = TemporalEngine()
beh_engine = BehavioralEngine()
unc_engine = UncertaintyEngine()
table_factory = HPTableFactory()

# --- SIDEBAR: INGESTION & PERSONA ---
st.sidebar.header("📥 Sinyal Girişi")
uploaded_file = st.sidebar.file_uploader("Veri Dosyasını (CSV) Yükle", type=['csv'])

persona = st.sidebar.selectbox(
    "🎭 Persona Karar Yüzeyi", 
    ["Match Analyst", "Scout", "Technical Director", "Sporting Director"]
)

if uploaded_file:
    # 1. Ingestion (HP-CDL Gate)
    df = pd.read_csv(uploaded_file, sep=';')
    
    # 2. Reasoning (Epistemik Güven Denetimi)
    audit = unc_engine.calculate_confidence(df)
    st.sidebar.metric("Epistemik Güven", f"{audit['confidence']*100}%", delta=audit['status'])

    # 3. Compute (Analitik Motorlar)
    with st.spinner("Sovereign Intelligence İşleniyor..."):
        momentum = temp_engine.detect_regime_shifts(df)
        trauma_loops = beh_engine.analyze_trauma_loops(df)
        cog_speed = cog_engine.analyze_decision_speed(df)

    # --- MAIN DISPLAY (Persona Specific) ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"🏟️ {persona} Görünümü")
        # Burada Tesla estetiğiyle grafikler gelecek
        st.write("Aksiyon Akışı ve Momentum Analizi Aktif.")
        st.dataframe(df.head(20))

    with col2:
        st.subheader("💡 Egemen Karar")
        
        # Evidence Table (Kanıt Tablosu)
        # Örnek Evidence Node oluşturma
        nodes = [
            EvidenceNode(
                metric_id="cog_speed", 
                metric_name="Karar Hızı (Jordet)", 
                value=round(cog_speed.mean(), 2),
                sample_size=len(df),
                source="Event Data",
                confidence_score=audit['confidence'],
                uncertainty=1-audit['confidence']
            )
        ]
        
        evidence_table = table_factory.create_evidence_table(nodes)
        st.table(evidence_table)

        # Risk Paneli
        if persona == "Scout":
            st.subheader("⚠️ Davranışsal Risk")
            risk_table = table_factory.create_risk_table("Oyuncu_ID", len(trauma_loops))
            st.table(risk_table)
            st.caption("Sapolsky/Mate Travma Döngüsü Analizi")

else:
    st.info("Sinyal bekleniyor... Lütfen bir dosya yükleyin.")

