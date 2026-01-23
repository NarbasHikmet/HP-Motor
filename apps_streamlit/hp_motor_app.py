# --- AGENTIC INSIGHT (Copilot SDK Layer) ---
st.markdown("---")
st.subheader("🤖 Sovereign Agent Verdict")
from src.hp_motor.agents.sovereign_agent import SovereignAgent

agent = SovereignAgent()
with st.spinner("Ajan muhakeme ediyor..."):
    verdict = agent.generate_tactical_verdict(analysis, persona)

st.warning(f"**{persona} Modu:** {verdict}")
st.caption("Gücünü GitHub Copilot SDK ve HP-Engine'den alır.")
