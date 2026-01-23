def get_agent_verdict(analysis, persona):
    metrics = analysis.get('metrics', {})
    ppda = metrics.get('PPDA', 12.0)
    xg = metrics.get('xG', 0.5)
    phase = analysis.get('metadata', {}).get('phase', 'ACTION_GENERIC')
    
    # 1. Teknik Direktör (TD)
    if persona == "Technical Director":
        if ppda > 14:
            return f"Baskı hattımız kırık (PPDA: {ppda:.1f}). Bloklar arası mesafe çok fazla, rest-defense risk altında."
        elif "OFFENSIVE" in phase:
            return "Hücum yerleşimi genişliği optimal ancak F4 bitiricilik bölgesinde tarama (scanning) zayıf."
        else:
            return "Geçiş oyununda tempo kaybı var, blokları daralt."

    # 2. Scout
    elif persona == "Scout":
        if xg > 1.2:
            return "Oyuncunun xG Chain katkısı dominant. Mekansal travma döngüsünü kırma potansiyeli yüksek."
        else:
            return f"Defansif ikili mücadele profili stabil. PPDA ({ppda:.1f}) katkısı gelişim bekliyor."

    # 3. Maç Analisti
    else:
        return f"Yapısal dominans mevcut. PPDA: {ppda:.1f} ve xG: {xg:.2f} verileriyle taktiksel stabilite %{int(analysis['confidence']*100)}."
