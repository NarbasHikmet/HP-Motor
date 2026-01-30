HP-Motor Termux Bootstrap (SAFE, event-only, NO-GUESSING)
========================================================

Bu paket Termux'ta *sıfırdan* çalıştırmak için tasarlanmıştır.
- Gereken minimum: python
- Opsiyonel: matplotlib (tempo.png için)

KURULUM (Termux içinde)
-----------------------
1) Termux'u aç
2) Depo güncelle:
   pkg update -y && pkg upgrade -y

3) Depolama izni (isteğe bağlı ama tavsiye):
   termux-setup-storage

4) Gerekli paketler:
   pkg install -y python zip unzip

5) (Opsiyonel) Matplotlib istiyorsan (zor olabilir):
   pip install --upgrade pip
   pip install matplotlib

ÇALIŞTIRMA
----------
Bu zip'i telefona indirip aç:
- Önerilen yer: /sdcard/Download/

Termux'ta:
  cd ~
  mkdir -p hp_motor && cd hp_motor
  cp /sdcard/Download/hp_motor_termux_bootstrap.zip .
  unzip hp_motor_termux_bootstrap.zip

Maç paketi klasörünü oluştur:
  mkdir -p MATCH_PACK/out
  cp /sdcard/Download/events.csv MATCH_PACK/events.csv
  # (opsiyonel) alias_map.json ve context_vector.json kopyala

Koş:
  python STEP12_PHASE_TAGGER_MVP.py --match-pack MATCH_PACK
  python STEP13_TEMPO_MOMENTS.py --match-pack MATCH_PACK
  python STEP14_BRIEF_V2_RENDER.py --match-pack MATCH_PACK

Çıktılar:
  MATCH_PACK/out/

ÖNEMLİ: Bu paket hiç bir şey silmez. rm -rf gibi komutlar içermez.
