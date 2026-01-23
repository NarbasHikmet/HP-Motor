def get_agent_verdict(analysis, persona):
    # 1. Gerçek verileri analizden çekiyoruz
    metrics = analysis.get('metrics', {})
    ppda = metrics.get('PPDA', 0)
    xg = metrics.get('xG', 0)
    phase = analysis.get('metadata', {}).get('detected_phase', 'ACTION_GENERIC')
    
    # 2. TEKNİK DİREKTÖR (Dinamik Yorum)
    if persona == "Technical Director":
        if ppda > 12: # Eğer baskı zayıfsa
            return f"Ön alan baskımız (PPDA: {ppda:.1f}) çok yumuşak. Blokları daraltmazsak geçiş savunmasında (rest defense) patlarız."
        elif xg < 1.0: # Eğer üretim azsa
            return "Yapısal dominans var ama 3. bölgede verimsiziz. F4 fazında hızı artırıp şut zincirini (xG Chain) zorlamalıyız."
        else:
            return "Genel yapı stabil. Geçiş fazlarında tempoyu koru, blok mesafesini bozma."

    # 3. SCOUT (Dinamik Yorum)
    elif persona == "Scout":
        if "OFFENSIVE" in phase:
            return "Hücumda mekansal tarama (scanning) kapasitesi yüksek bir profil. xG katkısı dominans vaat ediyor."
        else:
            return f"Defansif aksiyonlarda (Duels) fiziksel sadakat yüksek. PPDA katkısı ({ppda:.1f}) elit seviyede."

    # 4. MAÇ ANALİSTİ (Dinamik Yorum)
    else:
        status = "Kritik" if ppda > 15 else "Optimal"
        return f"Savunma hattı {status}. Rakip geçişlerine karşı alan daraltma hızı {xg:.2f} xG üretimiyle sınırlı kalıyor."
