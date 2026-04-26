import smtplib, os, traceback
import yfinance as yf
import pandas as pd
import requests
from email.mime.text import MIMEText
from datetime import datetime
from io import StringIO

report = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}\n"
report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n\n"

def get_fii_dii():
    try:
        # NSE CSV - bypasses JSON API blocks
        url = "https://www.nseindia.com/reports/fii-dii"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        session = requests.Session()
        r = session.get(url, headers=headers, timeout=15)

        # Parse HTML table - NSE embeds data in script tag now
        if "fiiDiiData" not in r.text:
            return f"=== FII/DII ===\nNSE page changed. Manual check: https://www.nseindia.com/reports/fii-dii\n\n"

        # Extract JSON from page
        import re
        match = re.search(r'var fiiDiiData = (\[.*?\]);', r.text)
        if not match:
            return f"=== FII/DII ===\nCould not parse NSE data\n\n"

        data = json.loads(match.group(1))
        if not data:
            return f"=== FII/DII ===\nEmpty data\n\n"

        d = data[0]
        out = f"=== FII/DII + PRO - {d.get('date', 'N/A')} ===\n"

        fii_cash = float(d.get('fiiBuyValue', 0)) - float(d.get('fiiSellValue', 0))
        dii_cash = float(d.get('diiBuyValue', 0)) - float(d.get('diiSellValue', 0))
        pro_cash = float(d.get('proBuyValue', 0)) - float(d.get('proSellValue', 0))
        out += f"Cash: FII {fii_cash:+.0f}Cr | DII {dii_cash:+.0f}Cr | PRO {pro_cash:+.0f}Cr\n"

        fii_idx_fut = float(d.get('fiiIndexFutBuy', 0)) - float(d.get('fiiIndexFutSell', 0))
        dii_idx_fut = float(d.get('diiIndexFutBuy', 0)) - float(d.get('diiIndexFutSell', 0))
        pro_idx_fut = float(d.get('proIndexFutBuy', 0)) - float(d.get('proIndexFutSell', 0))
        out += f"Index Fut: FII {fii_idx_fut:+.0f}Cr | DII {dii_idx_fut:+.0f}Cr | PRO {pro_idx_fut:+.0f}Cr\n"

        fii_idx_opt = float(d.get('fiiIndexOptBuy', 0)) - float(d.get('fiiIndexOptSell', 0))
        dii_idx_opt = float(d.get('diiIndexOptBuy', 0)) - float(d.get('diiIndexOptSell', 0))
        pro_idx_opt = float(d.get('proIndexOptBuy', 0)) - float(d.get('proIndexOptSell', 0))
        out += f"Index Opt: FII {fii_idx_opt:+.0f}Cr | DII {dii_idx_opt:+.0f}Cr | PRO {pro_idx_opt:+.0f}Cr\n"

        total_fii = fii_cash + fii_idx_fut + fii_idx_opt
        total_dii = dii_cash + dii_idx_fut + dii_idx_opt
        total_pro = pro_cash + pro_idx_fut + pro_idx_opt

        def bias(val):
            if val > 500: return "Strong Bullish"
            if val > 100: return "Bullish"
            if val < -500: return "Strong Bearish"
            if val < -100: return "Bearish"
            return "Neutral"

        out += f"\nBias: FII {bias(total_fii)} ({total_fii:+.0f}Cr) | "
        out += f"DII {bias(total_dii)} ({total_dii:+.0f}Cr) | "
        out += f"PRO {bias(total_pro)} ({total_pro:+.0f}Cr)\n\n"
        return out
    except Exception as e:
        return f"=== FII/DII ===\nFailed: {str(e)[:200]}\nCheck: https://www.nseindia.com/reports/fii-dii\n\n"

def get_gift_nifty():
    try:
        # NSE IFSC website - official source
        url = "https://www.nseifsc.com/market-data/live-market-indices"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)

        # Parse GIFT Nifty from HTML
        import re
        match = re.search(r'GIFT Nifty.*?([\d,]+\.?\d*)', r.text)
        if match:
            price = float(match.group(1).replace(',', ''))
            out = f"=== GIFT NIFTY ===\n"
            out += f"LTP: {price:.2f}\n\n"
            return out
        return f"=== GIFT NIFTY ===\nNo data on NSE IFSC\n\n"
    except:
        try:
            # Fallback: Use Nifty 50 futures as proxy
            nifty = yf.Ticker("^NSEI")
            hist = nifty.history(period="2d")
            if len(hist) >= 2:
                ltp = hist['Close'].iloc[-1]
                pct = ((ltp - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                out = f"=== GIFT NIFTY ===\n"
                out += f"*Using Nifty50 proxy - Gift data blocked*\n"
                out += f"LTP: {ltp:.2f} ({pct:+.2f}%)\n\n"
                return out
        except: pass
        return f"=== GIFT NIFTY ===\nData unavailable\n\n"

try:
    stocks = [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","HINDUNILVR.NS","ITC.NS",
        "SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS","LT.NS","AXISBANK.NS","MARUTI.NS",
        "SUNPHARMA.NS","WIPRO.NS","TITAN.NS","BAJFINANCE.NS","ULTRACEMCO.NS","NESTLEIND.NS"
    ]

    sectors = {
        "BANK": "^NSEBANK", "IT": "^CNXIT", "AUTO": "^CNXAUTO",
        "FMCG": "^CNXFMCG", "PHARMA": "^CNXPHARMA", "METAL": "^CNXMETAL",
        "REALTY": "^CNXREALTY", "ENERGY": "^CNXENERGY"
    }

    data = yf.download(stocks, period="1mo", group_by='ticker', progress=False, threads=False)
    sector_data = yf.download(list(sectors.values()), period="1mo", group_by='ticker', progress=False, threads=False)

    ref_hist = data['RELIANCE.NS']
    ref_hist = ref_hist[ref_hist['Volume'] > 0].tail(5)
    trading_days = ref_hist.index

    report += f"=== DAILY TOP MOVERS - LAST 5 TRADING DAYS ===\n"
    report += f"Period: {trading_days[0].strftime('%d %b')} to {trading_days[-1].strftime('%d %b')}\n\n"

    for day in trading_days:
        day_str = day.strftime('%d %b, %A')
        daily_perf = []
        sector_perf = []

        for stock in stocks:
            try:
                h = data[stock]
                if day not in h.index: continue
                idx = h.index.get_loc(day)
                if idx == 0: continue
                today_close = h['Close'].iloc[idx]
                prev_close = h['Close'].iloc[idx-1]
                if pd.isna(today_close) or pd.isna(prev_close) or prev_close == 0: continue
                pct = ((today_close - prev_close) / prev_close) * 100
                vol = h['Volume'].iloc[idx]
                vol_avg = h['Volume'].iloc[max(0,idx-4):idx].mean()
                vol_surge = ((vol - vol_avg) / vol_avg * 100) if vol_avg > 0 else 0
                daily_perf.append({"symbol": stock.replace(".NS", ""), "pct": pct, "vol_surge": vol_surge})
            except: continue

        for name, ticker in sectors.items():
            try:
                h = sector_data[ticker]
                if day not in h.index: continue
                idx = h.index.get_loc(day)
                if idx == 0: continue
                today_close = h['Close'].iloc[idx]
                prev_close = h['Close'].iloc[idx-1]
                if pd.isna(today_close) or pd.isna(prev_close) or prev_close == 0: continue
                pct = ((today_close - prev_close) / prev_close) * 100
                sector_perf.append({"name": name, "pct": pct})
            except: continue

        report += f"--- {day_str} ---\n"
        if daily_perf:
            df = pd.DataFrame(daily_perf)
            gainers = ", ".join([f"{r['symbol']}({r['pct']:+.1f}%)" for _, r in df.nlargest(3, 'pct').iterrows()])
            losers = ", ".join([f"{r['symbol']}({r['pct']:+.1f}%)" for _, r in df.nsmallest(3, 'pct').iterrows()])
            vol_surge = ", ".join([f"{r['symbol']}({r['vol_surge']:+.0f}%)" for _, r in df.nlargest(3, 'vol_surge').iterrows()])
            report += f"Stocks: Gainers: {gainers} | Losers: {losers}\n"
            report += f"Vol Surge: {vol_surge}\n"
        if sector_perf:
            sec_df = pd.DataFrame(sector_perf)
            sec_gain = ", ".join([f"{r['name']}({r['pct']:+.1f}%)" for _, r in sec_df.nlargest(3, 'pct').iterrows()])
            sec_loss = ", ".join([f"{r['name']}({r['pct']:+.1f}%)" for _, r in sec_df.nsmallest(3, 'pct').iterrows()])
            report += f"Sectors: Gainers: {sec_gain} | Losers: {sec_loss}\n"
        report += f"\n"

    report += get_fii_dii()
    report += get_gift_nifty()

except Exception as e:
    report += f"\nERROR: {str(e)}\n"
    report += f"Traceback:\n{traceback.format_exc()}\n"

gmail_user = os.getenv('GMAIL_USER')
gmail_pass = os.getenv('GMAIL_PASS')
to_email = os.getenv('TO_EMAIL')

msg = MIMEText(report)
msg['Subject'] = f"NSE EOD Crux - {datetime.now().strftime('%d %b')}"
msg['From'] = gmail_user
msg['To'] = to_email

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(gmail_user, gmail_pass)
    smtp.send_message(msg)
print("Email sent")
