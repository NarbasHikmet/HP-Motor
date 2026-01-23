import streamlit as st
import pandas as pd
from src.hp_motor.pipelines.run_analysis import SovereignOrchestrator
from src.hp_motor.viz.table_factory import HPTableFactory
from src.hp_motor.viz.plot_factory import HPPlotFactory
from src.hp_motor.core.cdl_models import EvidenceNode
from src.hp_motor.agents.sovereign_agent import get_agent_verdict

# --- SOVEREIGN DESIGN ---
st.set_page_config(page_title="HP MOTOR v5.0", layout="wide")
st.markdown("<style>.main { background-color: #000000; color: #FFD700; }</style>", unsafe_allow_html=True)

st.title("🛡️ HP MOTOR v5.0 | SOVEREIGN AGENT")
st.caption("Felsefe: Saper Vedere | Güç: GitHub Copilot SDK")

# --- INITIALIZATION ---
orchestrator = SovereignOrchestrator()
table_factory = HPTableFactory()
plot_factory = HPPlotFactory()

# --- SIDEBAR ---
uploaded_file = st.sidebar.file_uploader("Sinyal (CSV) Yükle", type=['csv'])
persona = st.sidebar.selectbox("Persona Karar Yüzeyi", ["Match Analyst", "Scout", "Technical Director"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    
    with st.spinner("Sovereign Intelligence İşleniyor..."):
        analysis = orchestrator.execute_full_analysis(df)
        verdict = get_agent_verdict(analysis, persona)
    
    # --- DASHBOARD ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🏟️ Mekansal Analiz (Spatial Engine)")
        # Travma Grafiğini Çizdir
        fig = plot_factory.plot_trauma_zones(analysis['trauma_loops'])
        st.pyplot(fig)
        
        st.subheader("📊 Kanıt Tablosu")
        node = EvidenceNode(
            metric_id="cog_speed",
            metric_name="Bilişsel Hız (Jordet)",
            value=round(analysis['cognitive_speed'].mean(), 2) if not analysis['cognitive_speed'].empty else 0,
            sample_size=len(df),
            source="Event Data",
            confidence_score=analysis['confidence']['confidence'],
            uncertainty=1 - analysis['confidence']['confidence']
        )
        st.table(table_factory.create_evidence_table([node]))

    with col2:
        st.subheader("🤖 Agent Verdict")
        st.warning(f"**Hüküm:** {verdict}")
        
        st.metric("Epistemik Güven", f"{analysis['confidence']['confidence']*100}%")
        
        if persona == "Scout":
            st.subheader("⚠️ Risk Paneli")
            st.table(table_factory.create_risk_table("Oyuncu_1", len(analysis['trauma_loops'])))
else:
    st.info("Sinyal bekleniyor... Lütfen bir veri dosyası yükleyin.")
