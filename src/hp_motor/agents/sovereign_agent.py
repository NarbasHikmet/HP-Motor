def get_agent_verdict(analysis, persona):
    """
    HP-Engine DNA'sını kullanarak dosyaya ve role göre 
    dinamik 'Sovereign Verdict' üretir.
    """
    # 1. Dosyadan gelen fazı ve güven oranını yakala
    phase = analysis.get('metadata', {}).get('detected_phase', 'ACTION_GENERIC')
    confidence = analysis.get('confidence', {}).get('confidence', 0.85)
    
    # 2. Teknik Direktör (Technical Director) Mantığı
    if persona == "Technical Director":
        if "OFFENSIVE" in phase:
            return "Hücum yerleşiminde genişlik iyi ancak final paslarında 'Scanning' (tarama) eksik. 3. bölgeye geçişte hızı artır."
        elif "DEFENSIVE" in phase:
            return "Bloklar arası mesafe açılıyor. Kompakt yapıyı koru, PPDA değerini düşürmek için ön alan baskısını yoğunlaştır."
        elif "TRANSITION" in phase:
            return "Geçiş oyununda tempo kaybı var. Re-press (şok baskı) süresini 6 saniyenin altına çek, savunma emniyetini (rest defense) bırakma."
        else:
            return "Genel yapı stabil, ancak geçiş fazlarında blokları daraltmamız gerekiyor."

    # 3. Scout Mantığı
    elif persona == "Scout":
        if "OFFENSIVE" in phase:
            return "Oyuncu bitiricilik (xG Chain) zincirinde dominant, ancak progresif pas alma kalitesinde dalgalanma var."
        else:
            return "Defansif ikili mücadelelerde (Duels) fiziksel üstünlük sağlıyor, elit seviye PPDA katkısı var."

    # 4. Maç Analisti (Match Analyst) Mantığı
    else:
        if "OFFENSIVE" in phase:
            return f"Yapısal dominans %{int(confidence*100)} seviyesinde. F4 fazında hız düşük, Field Tilt verileri hücumu destekliyor."
        else:
            return "Savunma hattı derinde (Low Block). Rakip geçişlerine karşı alan daraltma başarılı."

    return "Veri okundu, stratejik hüküm bekleniyor..."
