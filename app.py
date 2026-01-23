import streamlit as st
import pandas as pd
import numpy as np
import sys
import os

# 1. ADIM: YOLLARI BİRLEŞTİRME (Path Integration)
# Bu kısım 'src' altındaki 'hp_motor' paketini sisteme mühürler.
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from hp_motor.pipelines.run_analysis import SovereignOrchestrator
    from hp_motor.agents.sovereign_agent import get_agent_verdict
except ImportError as e:
    st.error(f"Kritik Yol Hatası: 'src/hp_motor' bulunamadı. Hata: {e}")
    st.stop()

# 2. ADIM: HP-ENGINE TABANLI ŞEMA EŞLEME (Mapping DNA)
# Hataların kaynağı olan sütun isimlerini burada evrenselleştiriyoruz.
SCHEMA_MAPPING = {
    'start': ['zaman', 'time', 'timestamp', 'sec', 'start_time', 'baslangic'],
    'pos_x': ['x', 'coord_x', 'location_x', 'yatay'],
    'pos_y': ['y', 'coord_y', 'location_y', 'dikey'],
    'code': ['event_code', 'action_code', 'kod', 'id'],
    'event_type': ['action', 'type', 'event_id', 'aksiyon_tipi']
}

st.set_page_config(page_title="HP MOTOR v5.1", layout="wide", page_icon="🛡️")
st.title("🛡️ HP MOTOR v5.1 | UNIFIED PATHS")

@st.cache_resource
def load_orchestrator():
    return SovereignOrchestrator()

orchestrator = load_orchestrator()

# 3. ADIM: TOPLU SİNYAL GİRİŞİ
uploaded_files = st.sidebar.file_uploader("Dosyaları Sürükleyin (Toplu)", accept_multiple_files=True)
persona = st.sidebar.selectbox("Analiz Personası", ["Match Analyst", "Scout", "Technical Director"])

if uploaded_files:
    for uploaded_file in uploaded_files:
        with st.expander(f"⚙️ Analiz Ediliyor: {uploaded_file.name}", expanded=True):
            file_ext = os.path.splitext(uploaded_file.name)[1].lower()
            
            try:
                # Veri Okuma
                if file_ext == '.csv':
                    df = pd.read_csv(uploaded_file, sep=None, engine='python')
                elif file_ext in ['.xlsx', '.xls']:
                    df = pd.read_excel(uploaded_file).reset_index()
                elif file_ext == '.mp4':
                    st.video(uploaded_file)
                    df = pd.DataFrame([{"visual": "video_stream"}])
                else:
                    df = pd.DataFrame([{"raw": "document"}])

                # 4. ADIM: ŞEMA DÜZELTME (Hata Veren Sütunları Enjekte Etme)
                # Bu kısım 'uncertainty.py' ve 'run_analysis.py' içindeki patlamaları önler.
                for target, aliases in SCHEMA_MAPPING.items():
                    # Eğer hedef sütun (örn: 'start') yoksa, alternatiflerine bak
                    if target not in df.columns:
                        for alias in aliases:
                            if alias in df.columns:
                                df.rename(columns={alias: target}, inplace=True)
                                break
                    
                    # Eğer hala yoksa, varsayılan değer ata ki motor hata vermesin
                    if target not in df.columns:
                        if target in ['start', 'pos_x', 'pos_y']:
                            df[target] = 0.0
                        else:
                            df[target] = 'ACTION_GENERIC'

                # 'action' sütun hatası için özel önlem
                if 'action' not in df.columns:
                    df['action'] = df['event_type']

                # Veri tiplerini doğrula
                df['start'] = pd.to_numeric(df['start'], errors='coerce').fillna(0.0)

                # 5. ADIM: MOTORU ATEŞLE
                with st.spinner("Sovereign Intelligence İşleniyor..."):
                    analysis = orchestrator.execute_full_analysis(df)
                    verdict = get_agent_verdict(analysis, persona)
                
                c1, c2 = st.columns([1, 3])
                with c1:
                    st.metric("Sinyal Gücü", f"%{int(analysis.get('confidence', {}).get('confidence', 0.8)*100)}")
                    st.caption(f"Format: {file_ext.upper()}")
                with c2:
                    st.warning(f"**Sovereign Verdict:** {verdict}")

            except Exception as e:
                st.error(f"Analiz sırasında bir engel oluştu: {e}")
else:
    st.info("Sinyal bekleniyor... HP-Engine verilerini buraya bırakabilirsiniz.")
