import streamlit as st
import pandas as pd
import numpy as np
import sys
import os
from io import BytesIO, StringIO

# 1) Path bootstrap (root/app.py -> ./src)
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, "src")
if src_path not in sys.path:
    sys.path.append(src_path)

try:
    from hp_motor.pipelines.run_analysis import SovereignOrchestrator
    from hp_motor.agents.sovereign_agent import get_agent_verdict
except ImportError as e:
    st.error(f"Kritik Hata: 'src' klasörü altındaki modüller okunamıyor. Hata: {e}")
    st.stop()

st.set_page_config(page_title="HP MOTOR v6.0", layout="wide", page_icon="🛡️")
st.title("🛡️ HP MOTOR v6.0 | ARCHITECT")

@st.cache_resource
def load_orchestrator():
    return SovereignOrchestrator()

orchestrator = load_orchestrator()

# ----------------------------
# Helpers
# ----------------------------
def detect_phase(filename: str) -> str:
    fname = (filename or "").lower()
    if any(k in fname for k in ["pozisyon", "hucum", "hücum", "attack", "offensive"]):
        return "PHASE_OFFENSIVE"
    if any(k in fname for k in ["savunma", "defans", "defensive", "block"]):
        return "PHASE_DEFENSIVE"
    if any(k in fname for k in ["gecis", "geçiş", "transition", "counter"]):
        return "PHASE_TRANSITION"
    return "ACTION_GENERIC"

def canonicalize_xy_inplace(df: pd.DataFrame) -> pd.DataFrame:
    # 0..100 -> 105x68 heuristic
    if df is None or df.empty:
        return df
    if "x" in df.columns and "y" in df.columns:
        try:
            x = pd.to_numeric(df["x"], errors="coerce")
            y = pd.to_numeric(df["y"], errors="coerce")
            if x.notna().any() and y.notna().any():
                xmax = float(np.nanmax(x.values))
                ymax = float(np.nanmax(y.values))
                xmin = float(np.nanmin(x.values))
                ymin = float(np.nanmin(y.values))
                if xmin >= 0 and ymin >= 0 and xmax <= 100.5 and ymax <= 100.5:
                    df["x"] = (x / 100.0) * 105.0
                    df["y"] = (y / 100.0) * 68.0
        except Exception:
            pass
    return df

def confidence_from_evidence(out: dict) -> float:
    eg = (out or {}).get("evidence_graph") or {}
    level = str(eg.get("overall_confidence", "medium")).lower()
    return {"low": 0.35, "medium": 0.65, "high": 0.85}.get(level, 0.55)

def adapt_for_agent_verdict(out: dict, phase: str) -> dict:
    metrics_list = out.get("metrics", []) or []
    m = {}
    for row in metrics_list:
        mid = row.get("metric_id")
        val = row.get("value")
        if mid is not None:
            m[mid] = val

    legacy_metrics = {
        "PPDA": float(m.get("ppda", 12.0)) if m.get("ppda") is not None else 12.0,
        "xG": 0.0,  # v1.0: yok
    }

    return {
        "metrics": legacy_metrics,
        "metadata": {"phase": phase},
        "confidence": confidence_from_evidence(out),
    }

# ----------------------------
# Robust file reading
# ----------------------------
def _read_bytes(uploaded_file) -> bytes:
    # Streamlit UploadedFile supports getvalue()
    return uploaded_file.getvalue()

def read_uploaded_artifact(uploaded_file):
    """
    Returns:
      kind: 'dataframe' | 'text' | 'video' | 'blocked'
      payload: pd.DataFrame or str or bytes
      meta: dict
    """
    name = uploaded_file.name
    ext = os.path.splitext(name)[1].lower()
    meta = {"filename": name, "ext": ext}

    try:
        if ext == ".mp4":
            return "video", uploaded_file, meta

        b = _read_bytes(uploaded_file)

        # CSV
        if ext == ".csv":
            df = pd.read_csv(BytesIO(b), sep=None, engine="python")
            return "dataframe", df, meta

        # XLSX / XLS
        if ext in [".xlsx", ".xls"]:
            df = pd.read_excel(BytesIO(b)).reset_index(drop=True)
            return "dataframe", df, meta

        # XML (pandas.read_xml requires lxml in most cases)
        if ext == ".xml":
            # Try read_xml → DataFrame
            try:
                df = pd.read_xml(BytesIO(b))
                return "dataframe", df, meta
            except Exception as e1:
                # Fallback: treat as text if parsing fails
                txt = b.decode("utf-8", errors="replace")
                meta["warning"] = f"XML parsed as text (read_xml failed): {e1}"
                return "text", txt, meta

        # HTML: read first table; if none → text
        if ext in [".html", ".htm"]:
            html = b.decode("utf-8", errors="replace")
            try:
                tables = pd.read_html(StringIO(html))
                if tables:
                    return "dataframe", tables[0], meta
                return "text", html, meta
            except Exception as e2:
                meta["warning"] = f"HTML tables not parsed: {e2}"
                return "text", html, meta

        # TXT: plain text
        if ext == ".txt":
            txt = b.decode("utf-8", errors="replace")
            return "text", txt, meta

        # DOCX: extract text (requires python-docx)
        if ext == ".docx":
            try:
                import docx  # python-docx
                doc = docx.Document(BytesIO(b))
                txt = "\n".join([p.text for p in doc.paragraphs if p.text is not None])
                return "text", txt, meta
            except Exception as e3:
                return "blocked", None, {**meta, "error": f"DOCX read failed: {e3}"}

        # PDF: extract text (requires pypdf)
        if ext == ".pdf":
            try:
                from pypdf import PdfReader
                reader = PdfReader(BytesIO(b))
                pages = []
                for p in reader.pages:
                    pages.append(p.extract_text() or "")
                txt = "\n\n".join(pages).strip()
                if not txt:
                    meta["warning"] = "PDF text extraction returned empty (scanned PDF olabilir)."
                return "text", txt, meta
            except Exception as e4:
                return "blocked", None, {**meta, "error": f"PDF read failed: {e4}"}

        # Unknown
        return "blocked", None, {**meta, "error": f"Unsupported file extension: {ext}"}

    except Exception as e:
        return "blocked", None, {**meta, "error": str(e)}

def text_to_signal_df(text: str) -> pd.DataFrame:
    """
    v1: Text’i sistemin ingest pipeline’ına sokmak için minimal bir DF üretir.
    İleride: NLP/LLM extractor ile event/metric extraction yapılır.
    """
    return pd.DataFrame([{"raw_text": text}])

# ----------------------------
# Sidebar
# ----------------------------
st.sidebar.header("📥 Veri Girişi")

uploaded_files = st.sidebar.file_uploader(
    "Sinyalleri Bırakın (CSV, XML, XLSX, HTML, TXT, PDF, DOCX, MP4)",
    accept_multiple_files=True,
    # IMPORTANT: include all extensions you want to show
    type=["csv", "xml", "xlsx", "xls", "html", "htm", "txt", "pdf", "docx", "mp4"],
)

persona = st.sidebar.selectbox("Analiz Personası", ["Match Analyst", "Scout", "Technical Director"])
role = st.sidebar.text_input("Rol (player_role_fit)", value="Mezzala")
analysis_object_id = st.sidebar.selectbox("Analysis Object", ["player_role_fit"], index=0)

show_figures = st.sidebar.checkbox("Grafikleri Göster", value=True)
show_tables = st.sidebar.checkbox("Tabloları Göster", value=True)
show_lists = st.sidebar.checkbox("Listeleri Göster", value=True)

# ----------------------------
# Main
# ----------------------------
if not uploaded_files:
    st.info("Sinyal bekleniyor... Saper Vedere.")
    st.stop()

for uploaded_file in uploaded_files:
    with st.expander(f"⚙️ Analiz: {uploaded_file.name}", expanded=True):
        phase = detect_phase(uploaded_file.name)

        kind, payload, meta = read_uploaded_artifact(uploaded_file)

        # Render video
        if kind == "video":
            st.video(payload)
            st.info(f"Faz: {phase} | Video sinyali alındı. (v1.0: video pipeline bağlı değil)")
            continue

        # Blocked
        if kind == "blocked":
            st.error("Dosya tanınmadı / okunamadı.")
            st.write(meta)
            continue

        # Dataframe or text
        if kind == "dataframe":
            df = payload
            df = canonicalize_xy_inplace(df)
            st.write("Veri Önizleme", df.head(10))

            # entity picker (if available)
            entity_id = "entity"
            if "player_id" in df.columns:
                candidates = [str(x) for x in df["player_id"].dropna().unique().tolist()]
                if candidates:
                    entity_id = st.selectbox("player_id", candidates, index=0)

            with st.spinner("Sovereign Intelligence işleniyor..."):
                out = orchestrator.execute(
                    analysis_object_id=analysis_object_id,
                    raw_df=df,
                    entity_id=str(entity_id),
                    role=role,
                    phase=phase,
                )

        else:  # text
            txt = payload
            if meta.get("warning"):
                st.warning(meta["warning"])
            st.write("Metin Önizleme", (txt[:1500] + " ...") if len(txt) > 1500 else txt)

            # Minimal ingestion: convert to DF
            df = text_to_signal_df(txt)

            with st.spinner("Sovereign Intelligence işleniyor..."):
                out = orchestrator.execute(
                    analysis_object_id=analysis_object_id,
                    raw_df=df,
                    entity_id="entity",
                    role=role,
                    phase=phase,
                )

        # Handle output
        if out.get("status") != "OK":
            st.error("Analiz OK dönmedi.")
            st.write(out)
            continue

        adapted = adapt_for_agent_verdict(out, phase)
        verdict = get_agent_verdict(adapted, persona)

        c1, c2, c3 = st.columns([1, 1, 3])
        with c1:
            conf = confidence_from_evidence(out)
            st.metric("Güven", f"%{int(conf*100)}")
        with c2:
            st.info(f"Faz: {phase}")
            miss = out.get("missing_metrics", [])
            if miss:
                st.warning(f"Missing: {', '.join(miss[:6])}" + ("..." if len(miss) > 6 else ""))
        with c3:
            st.warning(f"**Sovereign Verdict:** {verdict}")

        if show_tables:
            st.subheader("📋 Tables")
            tables = out.get("tables", {}) or {}
            if not tables:
                st.info("Tablo üretilmedi.")
            else:
                for tname, rows in tables.items():
                    st.markdown(f"### {tname}")
                    st.dataframe(pd.DataFrame(rows), use_container_width=True)

        if show_lists:
            st.subheader("🧾 Lists")
            lists = out.get("lists", {}) or {}
            if not lists:
                st.info("Liste üretilmedi.")
            else:
                for lname, items in lists.items():
                    st.markdown(f"### {lname}")
                    st.write(items)

        if show_figures:
            st.subheader("📈 Figures")
            figs = out.get("figure_objects", {}) or {}
            if not figs:
                st.info("Grafik üretilmedi.")
            else:
                for pid, fig in figs.items():
                    st.markdown(f"### {pid}")
                    st.pyplot(fig, clear_figure=False)