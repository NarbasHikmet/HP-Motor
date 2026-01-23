import streamlit as st
import pandas as pd
import sys
import os
import io

# 1. ADIM: YOL TANIMLAMA
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

# HP Motor Modüllerini Import Etme
try:
    from hp_motor.pipelines.run_analysis import SovereignOrchestrator
    from hp_motor.agents.sovereign_agent import get_agent_verdict
except ImportError:
    st.error("Kritik Hata: 'src/hp_motor' yolu doğrulanamadı.")
    st.stop()

# --- ARAYÜZ AYARLARI ---
st.set_page_config(page_title="HP MOTOR v5.0", layout="wide", page_icon="🛡️")
st.markdown("""
    <style>
    .main { background-color: #000000; color: #FFD700; }
    .stAlert { background-color: #1a1a1a; border: 1px solid #FFD700; color: #FFD700; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ HP MOTOR v5.0 | BULK INTELLIGENCE")
st.caption("Evrensel Format Desteği: CSV, PDF, XLSX, XML, HTML, MP4 | Çoklu Dosya Modu Aktif")

@st.cache_resource
def load_orchestrator():
    return SovereignOrchestrator()

orchestrator = load_orchestrator()

# --- YAN MENÜ: ÇOKLU DOSYA YÜKLEYİCİ ---
st.sidebar.header("📥 Toplu Sinyal Girişi")

# 'accept_multiple_files=True' ile 20+ dosya seçimini açıyoruz
uploaded_files = st.sidebar.file_uploader(
    "Dosyaları Seçin veya Sürükleyin", 
    type=None, 
    accept_multiple_files=True
)

persona = st.sidebar.selectbox("Analiz Personası", ["Match Analyst", "Scout", "Technical Director"])

if uploaded_files:
    st.info(f"Toplam {len(uploaded_files)} dosya kuyruğa alındı.")
    
    # Her bir dosya için döngü başlatıyoruz
    for uploaded_file in uploaded_files:
        with st.expander(f"📄 Analiz Ediliyor: {uploaded_file.name}", expanded=True):
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            df_for_analysis = None

            # --- FORMAT İŞLEME ---
            if file_ext in ['.csv', '.xlsx', '.xls']:
                try:
                    if file_ext == '.csv':
                        try:
                            df_for_analysis = pd.read_csv(uploaded_file, sep=';')
                        except:
                            uploaded_file.seek(0)
                            df_for_analysis = pd.read_csv(uploaded_file, sep=',')
                    else:
                        df_for_analysis = pd.read_excel(uploaded_file)
                    st.success("Tabular veri başarıyla okundu.")
                except Exception as e:
                    st.error(f"Veri okuma hatası: {e}")

            elif file_ext == '.mp4':
                st.video(uploaded_file)
                df_for_analysis = pd.DataFrame([{"source": "video_stream", "name": uploaded_file.name}])

            elif file_ext in ['.pdf', '.html', '.xml']:
                st.write(f"Zengin metin belgesi tespit edildi ({file_ext})")
                df_for_analysis = pd.DataFrame([{"source": "document", "name": uploaded_file.name}])

            # --- MOTORU ATEŞLE ---
            if df_for_analysis is not None:
                with st.spinner(f"{uploaded_file.name} için zeka işleniyor..."):
                    analysis = orchestrator.execute_full_analysis(df_for_analysis)
                    verdict = get_agent_verdict(analysis, persona)
                
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.metric("Veri Güveni", f"{analysis.get('confidence', {}).get('confidence', 0)*100}%")
                with c2:
                    st.warning(f"**Sovereign Verdict:** {verdict}")
else:
    st.info("Sinyal bekleniyor... Lütfen analiz edilecek dosyaları yan menüden topluca yükleyin.")
