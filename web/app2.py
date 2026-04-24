from flask import Flask, jsonify, render_template, request
import json
from pathlib import Path

app = Flask(__name__)
OUTPUT = Path(__file__).parent.parent / 'output'

# Dolaşımdaki hisse bilgilerini yükle
STOCKS_INFO = {}
stocks_info_path = OUTPUT / 'stocks_info.json'
if stocks_info_path.exists():
    with open(stocks_info_path, 'r', encoding='utf-8') as f:
        STOCKS_INFO = json.load(f)
    print(f"✅ {len(STOCKS_INFO)} hisse dolaşım bilgisi yüklendi")

def get_available_months():
    path = OUTPUT / 'cumulative_all.json'
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    months = set()
    for stock in data.values():
        for item in stock.get('Aylik_Veriler', []):
            months.add(item.get('ay'))
    return sorted(list(months))

@app.route('/')
def index():
    return render_template('dashboard2.html')

@app.route('/api/months')
def api_months():
    return jsonify(get_available_months())

@app.route('/api/buyers/<month>')
def api_buyers(month):
    path = OUTPUT / f'{month}_buyers.json'
    if not path.exists():
        return jsonify([])
    
    with open(path, 'r', encoding='utf-8') as f:
        buyers = json.load(f)
    
    for item in buyers:
        code = item['Hisse_Kodu']
        net_nominal = item['Net_Nominal_TL']
        free_float = STOCKS_INFO.get(code, 0)
        if free_float and free_float > 0 and net_nominal > 0:
            item['ratio'] = net_nominal / free_float
        else:
            item['ratio'] = None
    
    return jsonify(buyers)

@app.route('/api/sellers/<month>')
def api_sellers(month):
    path = OUTPUT / f'{month}_sellers.json'
    if not path.exists():
        return jsonify([])
    
    with open(path, 'r', encoding='utf-8') as f:
        sellers = json.load(f)
    
    for item in sellers:
        code = item['Hisse_Kodu']
        net_nominal = abs(item['Net_Nominal_TL'])
        free_float = STOCKS_INFO.get(code, 0)
        if free_float and free_float > 0 and net_nominal > 0:
            item['ratio'] = net_nominal / free_float
        else:
            item['ratio'] = None
    
    return jsonify(sellers)

@app.route('/api/ytd')
def api_ytd():
    """Yılbaşından beri (2026) en çok net alım yapan hisseler"""
    path = OUTPUT / 'ytd_buyers.json'
    if not path.exists():
        return jsonify([])
    
    with open(path, 'r', encoding='utf-8') as f:
        ytd = json.load(f)
    
    # Oranları ekle
    for item in ytd:
        code = item['Hisse_Kodu']
        total_net = item['Toplam_Net_Nominal_TL']
        free_float = STOCKS_INFO.get(code, 0)
        if free_float and free_float > 0 and total_net > 0:
            item['ytd_ratio'] = total_net / free_float
        else:
            item['ytd_ratio'] = None
    
    return jsonify(ytd)  # Tüm hisseleri göster (50+)

@app.route('/api/compare')
def api_compare():
    month1 = request.args.get('month1')
    month2 = request.args.get('month2')
    if not month1 or not month2:
        return jsonify([])
    
    path = OUTPUT / 'cumulative_all.json'
    if not path.exists():
        return jsonify([])
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    compare = []
    for code, stock in data.items():
        monthly = {}
        for item in stock.get('Aylik_Veriler', []):
            monthly[item['ay']] = item['Net_Nominal_TL']
        
        val1 = monthly.get(month1, 0)
        val2 = monthly.get(month2, 0)
        
        if val1 != 0 or val2 != 0:
            compare.append({
                'Hisse_Kodu': code,
                month1: val1,
                month2: val2,
                'fark': val2 - val1
            })
    
    compare.sort(key=lambda x: abs(x['fark']), reverse=True)
    return jsonify(compare[:50])

@app.route('/api/stock/<code>')
def api_stock(code):
    path = OUTPUT / 'cumulative_all.json'
    if not path.exists():
        return jsonify({'error': 'Veri yok'}), 404
    
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if code not in data:
        return jsonify({'error': 'Hisse bulunamadı'}), 404
    
    result = data[code]
    result['Aylik_Veriler'] = sorted(result['Aylik_Veriler'], key=lambda x: x['ay'])
    
    free_float = STOCKS_INFO.get(code, 0)
    result['free_float'] = free_float
    for item in result['Aylik_Veriler']:
        net_nominal = item.get('Net_Nominal_TL', 0)
        if free_float and free_float > 0 and net_nominal != 0:
            item['ratio'] = net_nominal / free_float
        else:
            item['ratio'] = None
    
    return jsonify(result)

@app.route('/stock/<code>')
def stock_page(code):
    return render_template('stock_detail.html', code=code.upper())

if __name__ == '__main__':
    app.run(debug=True, port=5001)