import smtplib, os, traceback
import yfinance as yf
import pandas as pd
import requests
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from io import StringIO

report = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}\n"
report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n\n"

def get_gift_nifty():
    try:
        url = "https://priceapi.moneycontrol.com/pricefeed/nse/equitycash/GIFNIFTY"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        d = r.json()['data']
        ltp = float(d['pricecurrent'])
        pct = float(d['pricepercentchange'])
        out = f"=== GIFT NIFTY ===\n"
        out += f"LTP: {ltp:.2f} ({pct:+.2f}%)\n\n"
        return out
    except Exception as e:
        return f"=== GIFT NIFTY ===\nData unavailable: {str(e)[:100]}\n\n"

def get_top_delivery_stocks():
    try:
        # NSE posts bhavcopy after 6:30 PM. Try today, fallback to yesterday.
        for days_back in [0, 1, 2]:
            date_obj = datetime.now() - timedelta(days=days_back)
            # Skip weekends
            if date_obj.weekday() >= 5:
                continue
            date_str = date_obj.strftime('%d%m%Y')
            url = f"https://archives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
            headers = {"User-Agent": "Mozilla/5.0"}
            r = requests.get(url, headers=headers, timeout=15)

            if r.status_code == 200 and len(r.text) > 1000:
                df = pd.read_csv(StringIO(r.text))
                df = df[df['SERIES'] == 'EQ']
                df['DELIV_PER'] = pd.to_numeric(df['DELIV_PER'], errors='coerce')
                df = df.dropna(subset=['DELIV_PER'])
                top3 = df.nlargest(3, 'DELIV_PER')[['SYMBOL', 'DELIV_PER', 'CLOSE_PRICE']]

                out = f"=== TOP 3 HIGH DELIVERY - {date_obj.strftime('%d %b')} ===\n"
                for _, row in top3.iterrows():
                    out += f"{row['SYMBOL']}: {row['DELIV_PER']:.1f}% @ {row['CLOSE_PRICE']:.2f}\n"
                out += "\n"
                return out

        return f"=== DELIVERY DATA ===\nBhavcopy not available for last 3 days\n\n"
    except Exception as e:
        return f"=== DELIVERY DATA ===\nFailed: {str(e)[:150]}\n\n"

def get_fii_dii():
    # NSE blocks GitHub Actions. Providing direct link instead.
    return f"=== FII/DII + PRO ===\nCheck manually: https://www.nseindia.com/reports/fii-dii\nReason: NSE blocks cloud IPs\n\n"

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

    report += get_top_delivery_stocks()
    report += get_gift_nifty()
    report += get_fii_dii()

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
