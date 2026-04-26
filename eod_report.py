import smtplib, os, traceback
import yfinance as yf
import pandas as pd
from email.mime.text import MIMEText
from datetime import datetime

report = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}\n"
report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n\n"

try:
    stocks = [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","HINDUNILVR.NS","ITC.NS",
        "SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS","LT.NS","AXISBANK.NS","MARUTI.NS",
        "SUNPHARMA.NS","WIPRO.NS","TITAN.NS","BAJFINANCE.NS","ULTRACEMCO.NS","NESTLEIND.NS"
    ]

    sectors = {
        "BANK": "^NSEBANK", "IT": "^CNXIT", "AUTO": "^CNXAUTO",
        "FMCG": "^CNXFMCG", "PHARMA": "^CNXPHARMA", "METAL": "^CNXMETAL",
        "REALTY": "^CNXREALTY", "ENERGY": "^CNXENERGY", "FIN SERVICE": "^CNXFIN"
    }

    data = yf.download(stocks, period="1mo", group_by='ticker', progress=False, threads=False)
    ref_hist = data['RELIANCE.NS']
    ref_hist = ref_hist[ref_hist['Volume'] > 0].tail(5)
    trading_days = ref_hist.index

    report += f"=== DAILY TOP MOVERS - LAST 5 TRADING DAYS ===\n"
    report += f"Period: {trading_days[0].strftime('%d %b')} to {trading_days[-1].strftime('%d %b')}\n\n"

    for day in trading_days:
        day_str = day.strftime('%d %b, %A')
        daily_perf = []

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

                # Volume surge vs 4-day avg
                vol_avg = h['Volume'].iloc[max(0,idx-4):idx].mean()
                vol_surge = ((vol - vol_avg) / vol_avg * 100) if vol_avg > 0 else 0

                daily_perf.append({
                    "symbol": stock.replace(".NS", ""),
                    "pct": pct,
                    "ltp": today_close,
                    "vol": vol,
                    "vol_surge": vol_surge
                })
            except: continue

        if not daily_perf: continue
        df = pd.DataFrame(daily_perf)

        report += f"--- {day_str} ---\n"
        report += f"Top 3 Gainers: "
        report += ", ".join([f"{r['symbol']}({r['pct']:+.1f}%)" for _, r in df.nlargest(3, 'pct').iterrows()])
        report += f"\nTop 3 Losers: "
        report += ", ".join([f"{r['symbol']}({r['pct']:+.1f}%)" for _, r in df.nsmallest(3, 'pct').iterrows()])
        report += f"\nTop 3 Vol Surge: "
        report += ", ".join([f"{r['symbol']}({r['vol_surge']:+.0f}%)" for _, r in df.nlargest(3, 'vol_surge').iterrows()])
        report += f"\n\n"

    # 5-DAY SECTOR SUMMARY
    report += f"=== SECTORS - 5 DAY CUMULATIVE ===\n"
    sector_perf = []
    for name, ticker in sectors.items():
        try:
            h = yf.Ticker(ticker).history(period="1mo")
            h = h[h['Volume'] > 0].tail(5)
            if len(h) == 5:
                pct = ((h['Close'].iloc[-1] - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
                sector_perf.append({"name": name, "pct": pct})
        except: continue

    if sector_perf:
        sec_df = pd.DataFrame(sector_perf)
        report += f"Gainers: "
        report += ", ".join([f"{r['name']}({r['pct']:+.1f}%)" for _, r in sec_df[sec_df['pct'] > 0].nlargest(3, 'pct').iterrows()])
        report += f"\nLosers: "
        report += ", ".join([f"{r['name']}({r['pct']:+.1f}%)" for _, r in sec_df[sec_df['pct'] <= 0].nsmallest(3, 'pct').iterrows()])
        report += f"\n\n"

    # 5-DAY STOCK SUMMARY
    all_5day = []
    for stock in stocks:
        try:
            h = data[stock]
            h = h[h['Volume'] > 0].tail(5)
            if len(h) == 5:
                pct_5d = ((h['Close'].iloc[-1] - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
                all_5day.append({"symbol": stock.replace(".NS", ""), "pct": pct_5d})
        except: continue

    if all_5day:
        df5 = pd.DataFrame(all_5day)
        report += f"=== STOCKS - 5 DAY CUMULATIVE ===\n"
        report += f"Top Gainers: "
        report += ", ".join([f"{r['symbol']}({r['pct']:+.1f}%)" for _, r in df5.nlargest(3, 'pct').iterrows()])
        report += f"\nTop Losers: "
        report += ", ".join([f"{r['symbol']}({r['pct']:+.1f}%)" for _, r in df5.nsmallest(3, 'pct').iterrows()])
        report += f"\n"

except Exception as e:
    report += f"\nERROR: {str(e)}\n"
    report += f"Traceback:\n{traceback.format_exc()}\n"

# Send email
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
