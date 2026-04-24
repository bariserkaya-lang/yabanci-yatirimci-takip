from flask import Flask, jsonify, render_template
import json
from pathlib import Path

app = Flask(__name__)
OUTPUT = Path(__file__).parent.parent / 'output'

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/buyers')
def buyers():
    return jsonify(json.load(open(OUTPUT / '2026-03_buyers.json', encoding='utf-8')))

@app.route('/api/sellers')
def sellers():
    return jsonify(json.load(open(OUTPUT / '2026-03_sellers.json', encoding='utf-8')))

@app.route('/api/ytd')
def ytd():
    return jsonify(json.load(open(OUTPUT / 'ytd_buyers.json', encoding='utf-8')))

@app.route('/api/stock/<code>')
def stock(code):
    data = json.load(open(OUTPUT / 'cumulative_all.json', encoding='utf-8'))
    if code in data:
        return jsonify(data[code])
    return jsonify({'error': 'yok'})

app.run(debug=True, port=5000)