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
        # NSE CSV - more stable than JSON API
        url = "https://www.nseindia.com/api/reports?archieves=[{%22name%22:%22FII_DII%22,%22type%22:%22daily%22,%22category%22:%22capitalMarket%22,%22section%22:%22equity%22}]"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Referer": "https://www.nseindia.com/reports/fii-dii"
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        r = session.get(url, headers=headers, timeout=15)

        if r.status_code!= 200:
            return f"=== FII/DII ===\nNSE blocked request: {r.status_code}\n\n"

        data = r.json()
        if not data:
            return f"=== FII/DII ===\nEmpty response from NSE\n\n"

        d = data[0]
        out = f"=== FII/DII + PRO - {d.get('date', 'N/A')} ===\n"

        # Try multiple key variations NSE uses
        fii_cash = float(d.get('fiiCashBuyValue', d.get('fii_buy_value', 0))) - float(d.get('fiiCashSellValue', d.get('fii_sell_value', 0)))
        dii_cash = float(d.get('diiCashBuyValue', d.get('dii_buy_value', 0))) - float(d.get('diiCashSellValue', d.get('dii_sell_value', 0)))
        pro_cash = float(d.get('proCashBuyValue', d.get('pro_buy_value', 0))) - float(d.get('proCashSellValue', d.get('pro_sell_value', 0)))
        out += f"Cash: FII {fii_cash:+.0f}Cr | DII {dii_cash:+.0f}Cr | PRO {pro_cash:+.0f}Cr\n"

        fii_idx_fut = float(d.get('fiiIndexFutBuyValue', d.get('fii_index_fut_buy', 0))) - float(d.get('fiiIndexFutSellValue', d.get('fii_index_fut_sell', 0)))
        dii_idx_fut = float(d.get('diiIndexFutBuyValue', d.get('dii_index_fut_buy', 0))) - float(d.get('diiIndexFutSellValue', d.get('dii_index_fut_sell', 0)))
        pro_idx_fut = float(d.get('proIndexFutBuyValue', d.get('pro_index_fut_buy', 0))) - float(d.get('proIndexFutSellValue', d.get('pro_index_fut_sell', 0)))
        out += f"Index Fut: FII {fii_idx_fut:+.0f}Cr | DII {dii_idx_fut:+.0f}Cr | PRO {pro_idx_fut:+.0f}Cr\n"

        fii_idx_opt = float(d.get('fiiIndexOptBuyValue', d.get('fii_index_opt_buy', 0))) - float(d.get('fiiIndexOptSellValue', d.get('fii_index_opt_sell', 0)))
        dii_idx_opt = float(d.get('diiIndexOptBuyValue', d.get('dii_index_opt_buy', 0))) - float(d.get('diiIndexOptSellValue', d.get('dii_index_opt_sell', 0)))
        pro_idx_opt = float(d.get('proIndexOptBuyValue', d.get('pro_index_opt_buy', 0))) - float(d.get('proIndexOptSellValue', d.get('pro_index_opt_sell', 0)))
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
        return f"=== FII/DII ===\nData failed: {str(e)[:200]}\n\n"

def get_gift_nifty():
    try:
        # Use Yahoo Finance for Gift Nifty - ticker GIFTNIFTY.NS
        gift = yf.Ticker("GIFTNIFTY.NS")
        hist = gift.history(period="2d")
        if len(hist) >= 2:
            ltp = hist['Close'].iloc[-1]
            prev = hist['Close'].iloc[-2]
            pct = ((ltp - prev) / prev) * 100
            out = f"=== GIFT NIFTY ===\n"
            out += f"LTP: {ltp:.2f} ({pct:+.2f}%)\n\n"
            return out
        return f"=== GIFT NIFTY ===\nNo data\n\n"
    except Exception as e:
        return f"=== GIFT NIFTY ===\nData failed: {str(e)[:150]}\n\n"

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
