import streamlit as st
from src.engine.validator import SOTValidator
from src.engine.processor import HPProcessor
from src.engine.analyst import HPAnalyst

# ... (Başlangıç ayarları ve CSS aynı kalıyor) ...

if uploaded_file:
    # 1. VALIDATE & PROCESS
    report, clean_df = SOTValidator().clean_and_normalize(df)
    processed_df = HPProcessor().apply_lens_and_logic(clean_df)
    
    # 2. ANALYZE (Popperian Claims)
    # Sistem artık otomatik olarak SGA üzerinden hipotez kuruyor
    analyst = HPAnalyst()
    if processed_df['sga_hp'].sum() > 0:
        claim = analyst.generate_evidence_chain(
            "Forvet hattı 'Pozisyon Üstü' bitiricilik (SGA) sergiliyor.",
            "sga_hp < 0 ise hipotez yanlışlanır.",
            {"sga": processed_df['sga_hp'].sum()}
        )
    
    # 3. UI (Altın Oran %61.8 - %38.2)
    col_main, col_side = st.columns([618, 382])
    with col_main:
        st.subheader("🏟️ Saper Vedere (Anatomik Gözlem)")
        st.dataframe(processed_df[['action', 'phase_hp', 'sga_hp', 'prog_score_hp']].head(20))
    with col_side:
        st.subheader("💡 Chiaroscuro Analysis")
        # İddia paneli burada otomatik güncellenir
