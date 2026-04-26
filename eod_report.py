import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, time
import pytz
import json
import smtplib
from email.mime.text import MIMEText
import os
import requests

# ========== CONFIG ==========
SECTORS = {
    'AUTO': ['MARUTI.NS', 'M&M.NS', 'TATAMOTORS.NS', 'BAJAJ-AUTO.NS', 'EICHERMOT.NS'],
    'BANK': ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'KOTAKBANK.NS', 'AXISBANK.NS'],
    'IT': ['TCS.NS', 'INFY.NS', 'HCLTECH.NS', 'WIPRO.NS', 'TECHM.NS'],
    'PHARMA': ['SUNPHARMA.NS', 'DRREDDY.NS', 'CIPLA.NS', 'DIVISLAB.NS', 'LUPIN.NS'],
    'FMCG': ['HINDUNILVR.NS', 'ITC.NS', 'NESTLEIND.NS', 'BRITANNIA.NS', 'DABUR.NS'],
    'METAL': ['TATASTEEL.NS', 'JSWSTEEL.NS', 'HINDALCO.NS', 'COALINDIA.NS', 'VEDL.NS'],
    'ENERGY': ['RELIANCE.NS', 'ONGC.NS', 'NTPC.NS', 'POWERGRID.NS', 'BPCL.NS'],
    'REALTY': ['DLF.NS', 'GODREJPROP.NS', 'OBEROIRLTY.NS', 'PHOENIXLTD.NS', 'PRESTIGE.NS']
}
NIFTY = '^NSEI'
HISTORY_FILE = 'eod_history.json'
# ============================

def get_fii_dii():
    try:
        url = 'https://www.nseindia.com/api/fiidiiTradeReact'
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        fii = float(data['fii'][0]['buyValue']) - float(data['fii'][0]['sellValue'])
        dii = float(data['dii'][0]['buyValue']) - float(data['dii'][0]['sellValue'])
        return fii/100, dii/100
    except:
        return 0, 0

def get_sector_data():
    data = {}
    for sector, stocks in SECTORS.items():
        df = yf.download(stocks, period='5d', interval='1d', progress=False)['Close']
        if df.empty: continue
        ret = df.pct_change().iloc[-1] * 100
        vol_ratio = df.iloc[-1] / df.iloc[-2]
        data[sector] = {
            'return': round(ret.mean(), 2),
            'breadth': round((ret > 0).sum() / len(ret) * 100, 0),
            'volume': round(vol_ratio.mean(), 2)
        }
    return data

def get_adv_dec():
    nifty_stocks = pd.read_html('https://en.wikipedia.org/wiki/NIFTY_50')[1]['Symbol'].tolist()
    nifty_stocks = [s + '.NS' for s in nifty_stocks]
    df = yf.download(nifty_stocks, period='2d', interval='1d', progress=False)['Close']
    ret = df.pct_change().iloc[-1]
    return (ret > 0).sum(), (ret < 0).sum()

def build_email(today_data, history):
    ist = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist).strftime('%d-%b-%Y')

    dates = sorted(history.keys())[-5:]
    header = 'Date | ' + ' | '.join([d[5:] for d in dates])
    rows = []
    for rank in range(1, 6):
        row = f'Rank {rank} | '
        row += ' | '.join([history[d]['top5'][rank-1] if rank <= len(history[d]['top5']) else '-' for d in dates])
        rows.append(row)

    fii, dii = today_data['fii'], today_data['dii']
    if fii > 1000 and dii < -1000: label = 'Strong Institutional Buy'
    elif fii < -1000 and dii > 1000: label = 'DII Rescue, FII Exit'
    elif fii > 0 and dii > 0: label = 'Broad Based Buy'
    elif fii < 0 and dii < 0: label = 'Distribution'
    else: label = 'Mixed Flow'

    sectors_sorted = sorted(today_data['sectors'].items(), key=lambda x: x[1]['return'], reverse=True)
    top5 = [s[0] for s in sectors_sorted[:5]]

    body = f"""EOD REPORT | SmartMoney: {label}

=== TOP 5 SECTORS BY DAY ===
{header}
{'-'*len(header)}
{chr(10).join(rows)}

=== TODAY'S SNAPSHOT ===
FII: {fii:+.0f} Cr | DII: {dii:+.0f} Cr | A/D: {today_data['adv']}/{today_data['dec']}

=== SECTOR DETAILS ===
{'Sector':<8} {'Ret%':<6} {'Breadth%':<9} {'Vol x'}
{'-'*35}
"""
    for sec, val in sectors_sorted:
        body += f"{sec:<8} {val['return']:>5.2f} {val['breadth']:>8.0f} {val['volume']:>5.2f}\n"

    return body, top5

def main():
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    # Comment next line for testing before 8 PM IST
    if not (now_ist.time() >= time(20,0) and now_ist.weekday() < 5): exit()

    try:
        with open(HISTORY_FILE) as f: history = json.load(f)
    except: history = {}

    fii, dii = get_fii_dii()
    sectors = get_sector_data()
    adv, dec = get_adv_dec()
    today_data = {'fii': fii, 'dii': dii, 'sectors': sectors, 'adv': adv, 'dec': dec}

    body, top5 = build_email(today_data, history)
    today_str = now_ist.strftime('%Y-%m-%d')
    history[today_str] = {'top5': top5}

    if len(history) > 5:
        for k in sorted(history.keys())[:-5]: del history[k]

    with open(HISTORY_FILE, 'w') as f: json.dump(history, f)

    msg = MIMEText(body)
    msg['Subject'] = f"EOD REPORT | SmartMoney {datetime.now(ist).strftime('%d-%b')}"
    msg['From'] = os.environ['GMAIL_USER']
    msg['To'] = os.environ['TO_EMAIL']

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
        s.login(os.environ['GMAIL_USER'], os.environ['GMAIL_PASS'])
        s.send_message(msg)

if __name__ == '__main__':
    main()
