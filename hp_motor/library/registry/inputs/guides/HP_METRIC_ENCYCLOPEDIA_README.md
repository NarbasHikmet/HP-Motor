# HP Metric Encyclopedia v2.0

**Comprehensive Football Metrics Encyclopedia for HP Motor Analytics**  
Created: 2026-01-30  
Author: Hikmet Pınarbaş - HP Football Analytics  
Base Data: Manchester City 2-0 Galatasaray (28/01/2026, UEFA Champions League)

---

## 📊 Overview

Bu ansiklopedi, **164 SportsBase metriğini** HP Motor analiz sistemine entegre etmek üzere tasarlanmış kapsamlı bir veri referans sistemidir.

### Temel Özellikler

✅ **3 Seviye Tanım** (Yüzeysel → Orta → Akademik)  
✅ **Matematiksel Formülasyon** (değişkenler, kısıtlar, hesaplama mantığı)  
✅ **4 Boyutlu İlişki Ağı** (Hierarşik, Kausal, Taktiksel, Hesaplama)  
✅ **HP Motor Ontoloji Mapping** (hangi analiz ünitelerini tetikler)  
✅ **27-Chart Görselleştirme Taksonomisi** (grafik önerileri, renk şemaları)  
✅ **Gerçek Maç Verisi** (Galatasaray örnek değerleri)  
✅ **Kodlanabilir Format** (JSON, YAML, Excel)

---

## 📁 Dosya Yapısı

### 1. `hp_metric_encyclopedia_v2.json` (Ana Referans)
- **Format**: JSON
- **Kullanım**: Kodlanabilir, makine dostu, API-ready
- **İçerik**: Tüm metriklerin eksiksiz yapısı
- **Boyut**: ~450KB

### 2. `HP_Metric_Encyclopedia_v2_Enhanced.xlsx` (İnsan-Dostu)
- **Format**: Excel (6 sheet)
- **Kullanım**: Görsel inceleme, manuel düzenleme
- **Sheetler**:
  1. **Main_Metrics**: Temel bilgiler, 3 seviye tanım, örnek değerler
  2. **Formulations**: Matematiksel formüller, değişkenler, kısıtlar
  3. **Relationships**: Hierarşi, kausal bağlar, taktiksel ilişkiler
  4. **HP_Ontology**: Registry modül mapping, analiz ünite tetikleme
  5. **Visualization**: Grafik taksonomisi, normalizasyon ipuçları
  6. **Sources**: API endpoint, akademik referanslar, alternatif sağlayıcılar

### 3. `hp_metric_encyclopedia_v2.yaml` (Config-Friendly)
- **Format**: YAML
- **Kullanım**: Konfigürasyon dosyaları, deployment
- **İçerik**: Kompakt metrik tanımları

---

## 🧩 Veri Modeli

Her metrik şu katmanları içerir:

```json
{
  "id": "SB_0001",
  "name": "Index",
  
  "properties": {
    "unit": "Maç başına ortalama",
    "phase_id": "1_Organize_Hucum",
    "role": "intent",
    "role_pattern": {
      "nature": "action_initiation",
      "causal_weight": "high"
    }
  },
  
  "definitions": {
    "basic": "Maç performans indeksi",
    "medium": "Ağırlıklı aksiyon toplamı / 90 dakika",
    "academic": "I = Σ(actions_weighted) / 90 * normalization_factor"
  },
  
  "formulation": {
    "mathematical": "I = Σ(actions_weighted) / 90 * normalization_factor",
    "computational": "sum(weighted_actions) / minutes_played * 90",
    "variables": ["weighted_actions", "minutes_played", "normalization_factor"],
    "constraints": ["minutes_played > 0", "normalization_factor ∈ [0.8, 1.2]"]
  },
  
  "relationships": {
    "hierarchical": {
      "parent": null,
      "children": ["Gol", "Pozisyonlar", "Paslar"],
      "level": 0
    },
    "causal": {
      "influences": [
        {"metric": "Topla oynama, %", "direction": "positive", "strength": 0.85}
      ],
      "influenced_by": [
        {"metric": "Paslar", "direction": "positive", "strength": 0.90}
      ]
    },
    "tactical": {
      "belongs_to_patterns": ["possession-based", "build-up-quality"],
      "synergy_with": ["Paslar adresi bulanlar, %", "Progressive passes"]
    },
    "computational": {
      "derived_from": ["Tüm Hareketler", "Actions successful"],
      "contributes_to": ["Team Performance Score"]
    }
  },
  
  "ontology": {
    "hp_phase": "1_Organize_Hucum",
    "registry_modules": ["build_up", "progression", "chance_creation"],
    "triggers_analysis": [0, 1, 2, 4],
    "reasoning_depth": "deep"
  },
  
  "visualization": {
    "recommended_charts": ["pass_network", "progressive_actions", "xG_flow"],
    "primary_axis": "x",
    "normalization_hints": "per_90",
    "color_scheme": "sequential",
    "aggregation_level": ["match", "player", "team", "season"]
  },
  
  "sources": {
    "primary": "SportsBase API",
    "academic_refs": ["https://support.hudl.com/..."],
    "api_endpoint": "/api/v1/metrics/Index",
    "alternative_providers": ["FBref", "Wyscout", "StatsBomb"]
  },
  
  "example_data": {
    "match": "Manchester City 2-0 Galatasaray (28/01/2026)",
    "galatasaray_value": 202.0,
    "context": "UEFA Champions League"
  }
}
```

---

## 🎯 Kullanım Senaryoları

### 1. HP Motor'a Entegrasyon
```python
import json

# Ansiklopediyi yükle
with open('hp_metric_encyclopedia_v2.json', 'r', encoding='utf-8') as f:
    encyclopedia = json.load(f)

# Belirli bir metriği bul
metric = next(m for m in encyclopedia['metrics'] if m['name'] == 'Progressive passes')

# HP Motor analiz ünitelerini tetikle
analysis_units = metric['ontology']['triggers_analysis']  # [1, 2, 7]

# Görselleştirme önerilerini al
chart_types = metric['visualization']['recommended_charts']  # ['pass_network', ...]
```

### 2. Metrik İlişkilerini Keşfet
```python
# Kausal etki zinciri
influences = metric['relationships']['causal']['influences']
# [{"metric": "Final third entries", "direction": "positive", "strength": 0.90}, ...]

# Taktiksel pattern matching
patterns = metric['relationships']['tactical']['belongs_to_patterns']
# ["vertical-play", "progression", "penetration"]
```

### 3. Formül Bazlı Hesaplama
```python
# Matematiksel formül
formula = metric['formulation']['mathematical']
# "PP = Σ(passes) | where (distance_to_goal_after - distance_to_goal_before) ≥ 10m"

# Değişkenler
variables = metric['formulation']['variables']
# ["goal_progression", "target_zone", "pass_distance"]
```

---

## 📈 İstatistikler

| Kategori | Değer |
|----------|-------|
| **Toplam Metrik** | 164 |
| **Enhanced (Detaylı Formül)** | 10 kritik metrik |
| **Analiz Fazı** | 5 (Organize Hücum, Hücum Geçişi, Duran Top, Savunma, vb.) |
| **Role Tipi** | 5 (intent, skill, success, reward, risk) |
| **HP Motor Ünite** | 12 (0-11) |
| **Grafik Tipi** | 27 (pass_network, xG_flow, press_map, vb.) |

### Faz Dağılımı
- **Organize Hücum**: 126 metrik (77%)
- **Duran Top Hücumu**: 15 metrik (9%)
- **Organize Savunma**: 12 metrik (7%)
- **Savunma Geçişi**: 8 metrik (5%)
- **Hücum Geçişi**: 3 metrik (2%)

### Role Dağılımı
- **intent** (niyet): 78 metrik
- **skill** (beceri): 48 metrik
- **reward** (ödül): 16 metrik
- **success** (başarı): 16 metrik
- **risk** (risk): 6 metrik

---

## 🔧 Geliştirme Notları

### Tamamlananlar ✅
- [x] SportsBase 164 metrik tasnifi
- [x] 3 seviye tanım katmanı
- [x] 10 kritik metrik için detaylı formülasyon
- [x] İlişki ağı mimarisi (4 boyutlu)
- [x] HP Motor ontoloji mapping
- [x] Görselleştirme taksonomisi
- [x] Gerçek maç verisi entegrasyonu
- [x] JSON/YAML/Excel export

### Gelecek Adımlar 🚀
- [ ] Kalan 154 metrik için formül detaylandırma
- [ ] xG, xA, xT gibi advanced metriklerin eklenmesi
- [ ] Squawka, Twelve, WhoScored metrik mapping
- [ ] Video event synchronization şeması
- [ ] Registry modül tetikleme algoritması
- [ ] Grafik render engine entegrasyonu
- [ ] Real-time data pipeline mimarisi

---

## 🎓 Akademik Referanslar

Metrik tanımlarında aşağıdaki kaynaklar kullanılmıştır:

- **Wyscout Data Glossary**: https://dataglossary.wyscout.com/
- **StatsBomb Glossary**: https://stats-portal.statsbomb.com/glossary
- **Opta/Stats Perform Definitions**: https://theanalyst.com/articles/opta-football-stats-definitions
- **Hudl Event Data**: https://support.hudl.com/s/article/event-data-glossary-team-metrics
- **FIFA Training Centre**: https://www.fifatrainingcentre.com/

---

## 📞 İletişim & Destek

**Yaratıcı**: Hikmet Pınarbaş  
**Proje**: HP Motor v24.0  
**E-posta**: hpnarbas@gmail.com  
**Platform**: HP Football Analytics

---

## 📜 Lisans & Kullanım

Bu ansiklopedi HP Motor ekosistemi için geliştirilmiştir. SportsBase API verilerini temel alır ve akademik/ticari kullanım için uygun yapıda tasarlanmıştır.

**Son Güncelleme**: 30 Ocak 2026  
**Versiyon**: 2.0.0
