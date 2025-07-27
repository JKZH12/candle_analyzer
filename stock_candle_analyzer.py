import pandas as pd
import yfinance as yf
from flask import Flask, request, jsonify, render_template_string

"""
Stock Candle Analyzer
~~~~~~~~~~~~~~~~~~~~~
A *single‑file* demo that spins up a small Flask web‑app.  
Input a ticker like `700 HK` / `NVDA US` and a look‑back window *X*.  
The API returns counts of bullish / bearish candles, doji, and upper / lower‑shadow days.

Fixes in this revision
----------------------
*   **TypeError** ( "cannot convert the series to <class 'int'>" ) is caused by trying to feed a *pandas Series* to `int()`.  
    We now cast *inside* `classify()` so every metric is a plain Python `int` before JSON serialisation.
*   Added graceful handling for **empty / missing data**.
*   Added simple **health‑check** endpoint `GET /ping`.
*   Minor UI polish.

Run guide:
```
python -m venv venv && source venv/bin/activate   # Windows use venv\Scripts\activate
pip install flask pandas yfinance
python stock_candle_analyzer.py
```  
Browse → http://127.0.0.1:5000/
"""

app = Flask(__name__)

# ----------  Config  ---------- #
DOJI_TOLERANCE = 0.001   # 0.1 % of open price counts as doji
SHADOW_TOLERANCE = 0.0   # any non‑zero shadow counts
MAX_LOOKBACK_DAYS = 252  # ~1 year trading days for simple protection

# ----------  HTML (very small)  ---------- #
HTML_PAGE = """<!doctype html>
<html lang=\"en\"><meta charset=\"utf-8\">
<title>Stock Candle Analyzer</title>
<style>
 body{font-family:Arial,Helvetica,sans-serif;margin:40px;line-height:1.5;}
 label,input{margin-right:8px;font-size:1rem;}
 button{padding:2px 8px;}
 #output ul{margin-top:6px;}
</style>
<h2>Stock Candle Analyzer</h2>
<form id=queryForm>
  <label>Ticker:<input id=symbol placeholder=\"e.g. 700 HK\" required></label>
  <label>Days:<input id=days type=number min=1 value=20 required></label>
  <button>Run</button>
</form>
<div id=output></div>
<script>
const form=document.getElementById('queryForm');
form.addEventListener('submit',async e=>{
  e.preventDefault();
  const q=encodeURIComponent(document.getElementById('symbol').value.trim());
  const d=document.getElementById('days').value;
  const res=await fetch(`/api?symbol=${q}&days=${d}`);
  const data=await res.json();
  const out=document.getElementById('output');
  if(data.error){out.textContent=data.error;return;}
  out.innerHTML=`<h3>${data.symbol} (${data.ticker}) — last ${data.days} trading days</h3>
    <ul>
      <li>阳线 (Bullish): ${data.bullish}</li>
      <li>阴线 (Bearish): ${data.bearish}</li>
      <li>十字星 (Doji): ${data.doji}</li>
      <li>上影线: ${data.upper_shadow}</li>
      <li>下影线: ${data.lower_shadow}</li>
    </ul>`;
});
</script>"""

# ----------  Helpers  ---------- #

def to_yf_ticker(raw: str) -> str:
    """Convert "700 HK" → "0700.HK" for yfinance, "NVDA US" → "NVDA"."""
    parts = raw.upper().split()
    if len(parts) == 2:
        code, mkt = parts
        if mkt == "HK":
            return f"{code.zfill(4)}.HK"
        if mkt == "US":
            return code
    # already a valid ticker fall‑through
    return raw.upper()


def classify(df: pd.DataFrame):
    """Vectorised count of bullish/bearish/doji & shadow days — robust to pandas quirks.

    *Extract numpy arrays* to avoid pandas returning a 1‑element *Series* that trips
    `int()` casts (the root cause of your latest traceback).
    """

    import numpy as np

    o = df['Open'].to_numpy(float)
    c = df['Close'].to_numpy(float)
    h = df['High'].to_numpy(float)
    l = df['Low'].to_numpy(float)

    bullish = int(np.sum(c > o))
    bearish = int(np.sum(c < o))
    doji    = int(np.sum(np.abs(c - o) <= DOJI_TOLERANCE * o))

    upper_shadow = int(np.sum((h - np.maximum(o, c)) > SHADOW_TOLERANCE))
    lower_shadow = int(np.sum((np.minimum(o, c) - l) > SHADOW_TOLERANCE))

    return bullish, bearish, doji, upper_shadow, lower_shadow

# ----------  Routes  ---------- #
@app.route('/')
def home():
    return HTML_PAGE

@app.route('/ping')
def ping():
    return 'ok'

@app.route('/api')
def api():
    symbol = request.args.get('symbol', '').strip()
    days_raw = request.args.get('days', '20').strip()

    # --------  Input validation  -------- #
    if not symbol:
        return jsonify({'error': 'symbol is required'}), 400
    try:
        days = max(1, min(int(days_raw), MAX_LOOKBACK_DAYS))
    except ValueError:
        return jsonify({'error': 'days must be an integer'}), 400

    yf_ticker = to_yf_ticker(symbol)

    try:
        hist = yf.download(yf_ticker, period=f"{max(days * 2, 60)}d", interval='1d', progress=False)
    except Exception as e:
        return jsonify({'error': f'data fetch failed: {e}'}), 502

    hist = hist.dropna().tail(days)
    if hist.empty:
        return jsonify({'error': 'no data returned for this ticker'}), 404

    bullish, bearish, doji, upper, lower = classify(hist)
    return jsonify({
        'symbol': symbol,
        'ticker': yf_ticker,
        'days': len(hist),
        'bullish': bullish,
        'bearish': bearish,
        'doji': doji,
        'upper_shadow': upper,
        'lower_shadow': lower
    })

# ----------  Main  ---------- #
if __name__ == "__main__":
    import os
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

