import pandas as pd
import json
from pathlib import Path

# Excel dosyasını oku
file_path = Path('data/raw/Fiili_Dolasim_Raporu_MKK-22-04-2026.xlsx')
df = pd.read_excel(file_path, sheet_name='Worksheet', header=2)

# Borsa Kodu ve Fiili Dolaşımdaki Pay Adedi sütunlarını al
stocks_info = {}
for _, row in df.iterrows():
    code = row.get('Borsa Kodu')
    free_float = row.get('Fiili Dolaşımdaki Pay Adedi')
    
    if pd.notna(code) and pd.notna(free_float):
        # Hisse kodunu temizle (nokta varsa kaldır)
        code = str(code).strip().replace('.E', '')
        stocks_info[code] = int(free_float)

# JSON olarak kaydet
output_path = Path('output/stocks_info.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(stocks_info, f, ensure_ascii=False, indent=2)

print(f"✅ {len(stocks_info)} hisse için dolaşım bilgisi kaydedildi: {output_path}")
print("\nİlk 10 hisse:")
for i, (code, value) in enumerate(list(stocks_info.items())[:10]):
    print(f"   {code}: {value:,}")