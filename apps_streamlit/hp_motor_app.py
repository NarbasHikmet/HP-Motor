import streamlit as st
import pandas as pd
from src.hp_motor.pipelines.run_analysis import SovereignOrchestrator
from src.hp_motor.viz.table_factory import HPTableFactory
from src.hp_motor.core.cdl_models import EvidenceNode

# --- SOVEREIGN AESTHETICS ---
st.set_page_config(page_title="HP MOTOR v5.0", layout="wide")
st.markdown("<style>.main { background-color: #000000; color: #FFD700; }</style>", unsafe_allow_html=True)

st.title("🛡️ HP MOTOR v5.0")
st.caption("Felsefe: Saper Vedere | Egemen Zeka Aktif")

# --- INITIALIZATION ---
orchestrator = SovereignOrchestrator()
table_factory = HPTableFactory()

# --- SIDEBAR ---
uploaded_file = st.sidebar.file_uploader("Sinyal (CSV) Yükle", type=['csv'])
persona = st.sidebar.selectbox("Persona", ["Match Analyst", "Scout", "TD"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    
    # 1. EXECUTE ANALYSIS (The Orchestration)
    with st.spinner("Analiz Ediliyor..."):
        analysis = orchestrator.execute_full_analysis(df)
    
    # 2. DISPLAY RESULTS
    st.metric("Epistemik Güven", f"{analysis['confidence']['confidence']*100}%")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Kanıt Tablosu")
        node = EvidenceNode(
            metric_id="cog_speed",
            metric_name="Karar Hızı",
            value=round(analysis['cognitive_speed'].mean(), 2),
            sample_size=len(df),
            source="Event Data",
            confidence_score=analysis['confidence']['confidence'],
            uncertainty=1 - analysis['confidence']['confidence']
        )
        st.table(table_factory.create_evidence_table([node]))
    
    with col2:
        if persona == "Scout":
            st.subheader("⚠️ Risk Paneli")
            st.table(table_factory.create_risk_table("Oyuncu_1", len(analysis['trauma_loops'])))
else:
    st.info("Lütfen bir veri dosyası yükleyin.")
