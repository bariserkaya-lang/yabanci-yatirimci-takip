import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path
import re

def parse_bist_excel(file_path):
    print(f"📂 Okunuyor: {file_path}")
    df_raw = pd.read_excel(file_path, sheet_name='TURKCE', header=None)
    
    # YILDIZ PAZAR satırını bul
    start_row = None
    for idx, row in df_raw.iterrows():
        if 'YILDIZ PAZAR' in str(row.values):
            # Hisse verileri bu satırdan 4 satır sonra başlıyor (başlık satırları)
            start_row = idx + 4
            break
    
    if start_row is None:
        print(f"⚠️ Uyarı: YILDIZ PAZAR bulunamadı, dosya atlanıyor: {file_path}")
        return pd.DataFrame()
    
    print(f"📍 Veri satır başı: {start_row}")
    
    hisseler = []
    for idx in range(start_row, len(df_raw)):
        row = df_raw.iloc[idx]
        
        # TOPLAM satırına gelince dur
        if 'TOPLAM' in str(row[0]) or pd.isna(row[0]):
            break
        
        # Hisse kodu kontrolü (.E ile biten)
        if pd.notna(row[0]) and '.E' in str(row[0]):
            hisse_kodu = str(row[0]).replace('.E', '')
            
            # Sayısal değerleri güvenli şekilde al
            try:
                alis_nominal = float(row[2]) if pd.notna(row[2]) else 0
                alis_tutar_tl = float(row[3]) if pd.notna(row[3]) else 0
                alis_tutar_usd = float(row[4]) if pd.notna(row[4]) else 0
                satis_nominal = float(row[5]) if pd.notna(row[5]) else 0
                satis_tutar_tl = float(row[6]) if pd.notna(row[6]) else 0
                satis_tutar_usd = float(row[7]) if pd.notna(row[7]) else 0
            except (ValueError, TypeError):
                print(f"   ⚠️ Sayısal dönüşüm hatası: {hisse_kodu}")
                continue
            
            hisse = {
                'Hisse_Kodu': hisse_kodu,
                'Hisse_Adi': row[1] if pd.notna(row[1]) else hisse_kodu,
                'Ay': '',
                'Alis_Nominal_TL': alis_nominal,
                'Alis_Tutar_TL': alis_tutar_tl,
                'Alis_Tutar_USD': alis_tutar_usd,
                'Satis_Nominal_TL': satis_nominal,
                'Satis_Tutar_TL': satis_tutar_tl,
                'Satis_Tutar_USD': satis_tutar_usd,
                'Net_Nominal_TL': alis_nominal - satis_nominal,
                'Net_Tutar_TL': alis_tutar_tl - satis_tutar_tl,
                'Net_Tutar_USD': alis_tutar_usd - satis_tutar_usd
            }
            hisseler.append(hisse)
    
    df = pd.DataFrame(hisseler)
    print(f"✅ {len(df)} hisse işlendi")
    return df

def ay_adini_bul(dosya_adi):
    """Dosya adından ay bilgisini çıkarır (yabanci202603.xls -> 2026-03)"""
    match = re.search(r'(\d{4})(\d{2})', dosya_adi)
    if match:
        return f"{match.group(1)}-{match.group(2)}"
    return datetime.now().strftime('%Y-%m')

def tum_aylari_isle(raw_dir, output_dir):
    """Tüm Excel dosyalarını işler ve birleştirir"""
    excel_files = list(raw_dir.glob('*.xls')) + list(raw_dir.glob('*.xlsx'))
    
    if not excel_files:
        print("❌ HATA: Excel dosyası bulunamadı!")
        return None
    
    tum_veriler = []
    
    for excel_file in sorted(excel_files):
        ay = ay_adini_bul(excel_file.name)
        print(f"\n📅 İşleniyor: {ay} - {excel_file.name}")
        df = parse_bist_excel(excel_file)
        if not df.empty:
            df['Ay'] = ay
            tum_veriler.append(df)
    
    if not tum_veriler:
        print("❌ HATA: Hiç veri işlenemedi!")
        return None
    
    birlesik_df = pd.concat(tum_veriler, ignore_index=True)
    print(f"\n✅ Toplam {len(birlesik_df)} satır veri işlendi")
    return birlesik_df

def en_cok_alanlar_ve_satanlar(df, n=20):
    """Verilen aya ait en çok alan/satanlar"""
    alanlar = df.sort_values('Net_Nominal_TL', ascending=False).head(n)
    satanlar = df.sort_values('Net_Nominal_TL', ascending=True).head(n)
    return {
        'en_cok_alanlar': alanlar.to_dict('records'),
        'en_cok_satanlar': satanlar.to_dict('records'),
        'toplam_net_alim_tl': df['Net_Nominal_TL'].sum(),
        'islem_goren_hisse_sayisi': len(df)
    }

def kumulatif_hesapla(birlesik_df):
    """Tüm zamanların kümülatif net pozisyonlarını hesaplar"""
    kumulatif = {}
    
    for _, row in birlesik_df.iterrows():
        kod = row['Hisse_Kodu']
        if kod not in kumulatif:
            kumulatif[kod] = {
                'Hisse_Kodu': kod,
                'Hisse_Adi': row['Hisse_Adi'],
                'Toplam_Net_Nominal_TL': 0,
                'Toplam_Net_Tutar_USD': 0,
                'Aylik_Veriler': []
            }
        kumulatif[kod]['Toplam_Net_Nominal_TL'] += row['Net_Nominal_TL']
        kumulatif[kod]['Toplam_Net_Tutar_USD'] += row['Net_Tutar_USD']
        kumulatif[kod]['Aylik_Veriler'].append({
            'ay': row['Ay'],
            'Net_Nominal_TL': row['Net_Nominal_TL'],
            'Net_Tutar_USD': row['Net_Tutar_USD']
        })
    
    return kumulatif

def main():
    print("=" * 60)
    print("📊 YABANCI YATIRIMCI VERİ İŞLEYİCİ (Tüm Aylar)")
    print("=" * 60)
    
    raw_dir = Path('data/raw')
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    # Tüm ayları işle
    birlesik_df = tum_aylari_isle(raw_dir, output_dir)
    
    if birlesik_df is None or birlesik_df.empty:
        return
    
    # Her ay için ayrı raporlar oluştur
    aylar = sorted(birlesik_df['Ay'].unique())
    for ay in aylar:
        ay_df = birlesik_df[birlesik_df['Ay'] == ay]
        rapor = en_cok_alanlar_ve_satanlar(ay_df)
        
        # JSON olarak kaydet
        with open(output_dir / f'{ay}_buyers.json', 'w', encoding='utf-8') as f:
            json.dump(rapor['en_cok_alanlar'][:10], f, ensure_ascii=False, indent=2)
        
        with open(output_dir / f'{ay}_sellers.json', 'w', encoding='utf-8') as f:
            json.dump(rapor['en_cok_satanlar'][:10], f, ensure_ascii=False, indent=2)
        
        print(f"\n📅 {ay} RAPORU:")
        print(f"   Toplam Net: {rapor['toplam_net_alim_tl']:,.0f} TL")
        if rapor['en_cok_alanlar']:
            print(f"   En çok alan: {rapor['en_cok_alanlar'][0]['Hisse_Kodu']} (+{rapor['en_cok_alanlar'][0]['Net_Nominal_TL']:,.0f} TL)")
        if rapor['en_cok_satanlar']:
            print(f"   En çok satan: {rapor['en_cok_satanlar'][0]['Hisse_Kodu']} ({rapor['en_cok_satanlar'][0]['Net_Nominal_TL']:,.0f} TL)")
    
    # Kümülatif hesapla
    kumulatif = kumulatif_hesapla(birlesik_df)
    
    # Kümülatif sıralama
    kumulatif_list = list(kumulatif.values())
    kumulatif_sorted = sorted(kumulatif_list, key=lambda x: x['Toplam_Net_Nominal_TL'], reverse=True)
    
    with open(output_dir / 'cumulative_all.json', 'w', encoding='utf-8') as f:
        json.dump(kumulatif, f, ensure_ascii=False, indent=2)
    
    with open(output_dir / 'ytd_buyers.json', 'w', encoding='utf-8') as f:
        json.dump(kumulatif_sorted[:200], f, ensure_ascii=False, indent=2)
    
    # Özet tablo
    print("\n" + "=" * 60)
    print(f"📈 TÜM ZAMANLAR KÜMÜLATİF RAPOR ({aylar[0]} - {aylar[-1]})")
    print("=" * 60)
    print("\n🏆 EN ÇOK NET ALIM (KÜMÜLATİF):")
    for i, hisse in enumerate(kumulatif_sorted[:5], 1):
        print(f"   {i}. {hisse['Hisse_Kodu']}: +{hisse['Toplam_Net_Nominal_TL']:,.0f} TL")
    
    negatifler = [h for h in kumulatif_sorted if h['Toplam_Net_Nominal_TL'] < 0][:5]
    if negatifler:
        print("\n⚠️ EN ÇOK NET SATIM (KÜMÜLATİF):")
        for i, hisse in enumerate(negatifler, 1):
            print(f"   {i}. {hisse['Hisse_Kodu']}: {hisse['Toplam_Net_Nominal_TL']:,.0f} TL")
    
    print(f"\n✅ İşlem tamamlandı! Çıktılar '{output_dir}' klasöründe.")

if __name__ == "__main__":
    main()