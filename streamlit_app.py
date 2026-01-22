import streamlit as st
import pandas as pd
from engine.signal_processor import SignalProcessor
from engine.claim_engine import ClaimEngine

st.set_page_config(page_title="HP Motor | Sovereign Intelligence", layout="wide")

# Chiaroscuro CSS
st.markdown("<style>.main { background-color: #050505; color: #ffffff; }</style>", unsafe_allow_html=True)

st.title("🛡️ HP Motor v1.0")

uploaded_file = st.file_uploader("Veri Kaynağını (CSV/ZIP) Yükle", type=['csv', 'zip'])

if uploaded_file:
    df = pd.read_csv(uploaded_file, sep=';')
    
    # 1. Sinyal İşleme
    sp = SignalProcessor()
    signals = sp.ingest(df, provider="SportsBase")
    
    # 2. Analiz ve Hipotez (Örnek)
    ce = ClaimEngine()
    report = ce.generate_tactical_claim(
        "Atletico Madrid Phase 5 (Set-Piece) Dominansı Mevcut.",
        {"set_piece_xg": 0.45},
        "set_piece_xg > 0.1"
    )
    
    # UI: Altın Oran Yerleşimi
    col_main, col_side = st.columns([618, 382])
    
    with col_main:
        st.subheader("🏟️ Saper Vedere (Anatomik Gözlem)")
        st.dataframe(df.head(15)) # İleride Da Vinci saha çizimi gelecek

    with col_side:
        st.subheader("💡 Chiaroscuro Analysis")
        for c in report['claims']:
            with st.expander(f"İddia: {c['text']}", expanded=True):
                st.write(f"**Güven Skoru:** %{c['confidence']['score']*100}")
                st.error(f"**Yanlışlama Testi:** {c['falsification']['tests'][0]['name']}")
