import streamlit as st
import pandas as pd
# DOĞRU İMPORTLAR: Artık her şey src.hp_motor altında
from src.hp_motor.pipelines.run_analysis import SovereignOrchestrator
from src.hp_motor.viz.table_factory import HPTableFactory
from src.hp_motor.core.cdl_models import EvidenceNode
from src.hp_motor.agents.sovereign_agent import get_agent_verdict

# --- TENEBRISM TASARIM ---
st.set_page_config(page_title="HP MOTOR v5.0", layout="wide")
st.markdown("<style>.main { background-color: #000000; color: #FFD700; }</style>", unsafe_allow_html=True)

st.title("🛡️ HP MOTOR v5.0 | SOVEREIGN AGENT")
st.caption("Felsefe: Saper Vedere | Güç: GitHub Copilot SDK")

orchestrator = SovereignOrchestrator()
table_factory = HPTableFactory()

# --- SIDEBAR ---
uploaded_file = st.sidebar.file_uploader("CSV Yükle", type=['csv'])
persona = st.sidebar.selectbox("Persona", ["Match Analyst", "Scout", "Technical Director"])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    
    with st.spinner("Muhakeme Ediliyor..."):
        analysis = orchestrator.execute_full_analysis(df)
        verdict = get_agent_verdict(analysis, persona)
    
    st.metric("Epistemik Güven", f"{analysis['confidence']['confidence']*100}%")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"🏟️ {persona} Görünümü")
        node = EvidenceNode(
            metric_id="cog_speed",
            metric_name="Bilişsel Hız",
            value=round(analysis['cognitive_speed'].mean(), 2) if not analysis['cognitive_speed'].empty else 0,
            sample_size=len(df),
            source="Event Data",
            confidence_score=analysis['confidence']['confidence'],
            uncertainty=1 - analysis['confidence']['confidence']
        )
        st.table(table_factory.create_evidence_table([node]))
    
    with col2:
        st.subheader("🤖 Sovereign Verdict")
        st.warning(f"**Karar:** {verdict}")
else:
    st.info("Sinyal bekleniyor...")
