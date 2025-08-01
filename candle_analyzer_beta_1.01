import pandas as pd
import yfinance as yf
from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# ----------  Configurations  ----------
PERIODS = [5, 10, 20, 30, 60]
UPPER_SHADOW_RATIO = 0.5    # 上影线长度 ≥ 总线长的 50%
LOWER_SHADOW_RATIO = 0.5    # 下影线长度 ≥ 总线长的 50%
DOJI_RATIO = 0.8            # 上 + 下影线 ≥ 总线长的 80%

# ----------  Helpers  ----------
def to_yf_ticker(raw: str) -> str:
    """Convert user input like '700 HK', 'NVDA US', '603501 CH' to yfinance ticker."""
    parts = raw.strip().upper().split()
    if len(parts) == 2:
        code, mkt = parts
        if mkt == "HK":
            return f"{code.zfill(4)}.HK"
        if mkt == "US":
            return code
        if mkt == "CH":
            # A股：以6开头的上海证券交易所(.SS)，其余视为深圳(.SZ)
            suffix = ".SS" if code.startswith('6') else ".SZ"
            return f"{code}{suffix}"
    return raw.upper()


def classify(df: pd.DataFrame) -> dict:
    """按定义统计各类蜡烛：阳线/阴线/十字星/上影线/下影线"""
    import numpy as np
    o = df['Open'].to_numpy(float)
    c = df['Close'].to_numpy(float)
    h = df['High'].to_numpy(float)
    l = df['Low'].to_numpy(float)
    total = h - l
    upper_len = h - np.maximum(o, c)
    lower_len = np.minimum(o, c) - l

    bullish = int(np.sum(c > o))
    bearish = int(np.sum(c < o))
    doji = int(np.sum((upper_len + lower_len) / total >= DOJI_RATIO))
    upper_shadow = int(np.sum((upper_len / total) >= UPPER_SHADOW_RATIO))
    lower_shadow = int(np.sum((lower_len / total) >= LOWER_SHADOW_RATIO))

    return {
        'bullish': bullish,
        'bearish': bearish,
        'doji': doji,
        'upper_shadow': upper_shadow,
        'lower_shadow': lower_shadow,
    }

# ----------  HTML Template  ----------
HTML_PAGE = """<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\">
<title>Stock Candle Analyzer</title>
<style>
  /* Animation for gradient text */
  @keyframes gradient-text {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
  }

  /* Modern iOS-like styling */
  body { background-color: #f2f2f7; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; padding: 20px; }
  .container { max-width: 700px; margin: auto; }
  .card { background: #fff; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); padding: 30px; }

  /* Animated gradient title */
  h2 {
    margin: 0 0 20px;
    font-size: 32px;
    text-align: center;
    background: linear-gradient(-45deg, #ff3b30, #007aff, #34c759, #ff3b30);
    background-size: 400% 400%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: gradient-text 5s ease infinite;
  }

  form { display: flex; gap: 10px; margin-bottom: 20px; }
  input { flex: 1; padding: 12px 16px; font-size: 16px; border: 1px solid #ccc; border-radius: 12px; }
  button { padding: 12px 20px; font-size: 16px; border: none; background: #007aff; color: #fff; border-radius: 12px; cursor: pointer; transition: background 0.2s; }
  button:hover { background: #005bb5; }
  .output { margin-top: 20px; }
  table { width: 100%; border-collapse: collapse; }
  thead { background: #f2f2f7; }
  th, td { padding: 14px 12px; font-size: 16px; color: #333; }
  th { text-align: left; font-weight: 600; }
  tr + tr { border-top: 1px solid #e0e0e0; }
  .bar-container { display: flex; align-items: center; width: 100%; }
  .bar { height: 12px; border-radius: 6px; margin-right: 8px; flex-shrink: 0; }
  .bull { background: linear-gradient(90deg, #ff3b30, #ff6b6b); }
  .bear { background: linear-gradient(90deg, #34c759, #85e89d); }
  .value { white-space: nowrap; font-weight: 500; margin-left: auto; }
</style>
</head><body>
<div class=\"container\">
  <div class=\"card\">
    <h2>Stock Candle Analyzer</h2>
    <form id=\"form\">
      <input id=\"symbol\" placeholder=\"Enter ticker (e.g. 700 HK / 603501 CH / NVDA US)\" required>
      <button type=\"submit\">Analyze</button>
    </form>
    <div class=\"output\" id=\"output\"></div>
  </div>
</div>
<script>
  document.getElementById('form').addEventListener('submit', async e => {
    e.preventDefault();
    const symbol = document.getElementById('symbol').value.trim();
    const res = await fetch(`/api?symbol=${encodeURIComponent(symbol)}`);
    const data = await res.json();
    const out = document.getElementById('output');
    if (data.error) {
      out.innerHTML = `<p style=\"color:#ff3b30; text-align:center;\">${data.error}</p>`;
      return;
    }
    let html = `<table><thead><tr><th>Period (days)</th><th>Bullish/Bearish</th></tr></thead><tbody>`;
    data.periods.forEach(p => {
      const r = data.results[p];
      const bullPct = (r.bullish / p * 100).toFixed(0);
      const barClass = bullPct > 50 ? 'bull' : 'bear';
      html += `<tr><td>${p}</td>`;
      html += `<td><div class=\"bar-container\"><div class=\"bar ${barClass}\" style=\"width:${bullPct}%;\"></div><span class=\"value\">${bullPct}%</span></div></td></tr>`;
    });
    html += `</tbody></table>`;
    out.innerHTML = html;
  });
</script>"""

# ----------  Routes  ----------
@app.route('/')
def home():
    return render_template_string(HTML_PAGE)

@app.route('/api')
def api():
    symbol = request.args.get('symbol', '').strip()
    if not symbol:
        return jsonify({'error': 'symbol is required'}), 400
    yf_ticker = to_yf_ticker(symbol)
    max_days = max(PERIODS)
    try:
        hist = yf.download(yf_ticker, period=f"{max_days*2}d", interval='1d', progress=False)
    except Exception as e:
        return jsonify({'error': f'data fetch failed: {e}'}), 502
    hist = hist.dropna()
    results = {}
    for p in PERIODS:
        df = hist.tail(p)
        if len(df) < p:
            results[p] = {'bullish': 0, 'bearish': 0, 'doji': 0, 'upper_shadow': 0, 'lower_shadow': 0}
        else:
            results[p] = classify(df)
    return jsonify({
        'symbol': symbol,
        'ticker': yf_ticker,
        'periods': PERIODS,
        'results': results
    })

# ----------  Main Entrypoint  ----------
if __name__ == '__main__':
    import os
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
