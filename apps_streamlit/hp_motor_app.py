import streamlit as st
from src.engine.ingestion import HP_Ingestion
from src.engine.epistemic import EpistemicGuardrail

# --- ESTETİK ANAYASA ---
st.set_page_config(page_title="HP MOTOR v1.0", layout="wide")
st.markdown("<style>body { background-color: #000; color: #FFD700; }</style>", unsafe_allow_html=True)

def main():
    st.title("🛡️ HP MOTOR | SOVEREIGN OS")
    
    # 1. Ingestion (v1.0)
    ingest = HP_Ingestion()
    uploaded_file = st.sidebar.file_uploader("Sinyal Girişi", type=['csv'])

    if uploaded_file:
        df = ingest.load_and_standardize(uploaded_file)
        
        # 2. Epistemik Denetim (v1.5)
        guard = EpistemicGuardrail()
        trust = guard.assess_confidence(df)
        
        st.sidebar.metric("Epistemik Güven", f"{trust['score']*100}%", delta=trust['status'])
        
        # 3. Persona Görünümü (v2.0)
        persona = st.selectbox("Gözlemci Modu", ["Analist", "Scout", "TD", "SD"])
        # ... Analiz çıktıları
