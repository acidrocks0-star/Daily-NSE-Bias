import smtplib, os, traceback, requests
import yfinance as yf
import pandas as pd
from email.mime.text import MIMEText
from datetime import datetime, timedelta

def get_report():
    report = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}\n"
    report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n"
    report += f"Data: Last 5 traded days\n\n"

    # 1. INDICES 5-DAY
    print("Fetching indices...")
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period="10d") # Get last 10 calendar days to ensure 5 trading days
    last5 = hist.tail(5)
    chg_5d = ((last5['Close'].iloc[-1] - last5['Close'].iloc[0]) / last5['Close'].iloc[0]) * 100
    day_chg = ((last5['Close'].iloc[-1] - last5['Close'].iloc[-2]) / last5['Close'].iloc[-2]) * 100

    report += f"=== NIFTY 50 ===\n"
    report += f"LTP: {last5['Close'].iloc[-1]:.2f} | 1-Day: {day_chg:.2f}% | 5-Day: {chg_5d:.2f}%\n\n"

    # 2. SECTORAL INDICES - Top 5 Gainers/Losers 5-day
    print("Fetching sectors...")
    sectors = {
        "NIFTY BANK": "^NSEBANK", "NIFTY IT": "^CNXIT", "NIFTY AUTO": "^CNXAUTO",
        "NIFTY FMCG": "^CNXFMCG", "NIFTY PHARMA": "^CNXPHARMA", "NIFTY METAL": "^CNXMETAL",
        "NIFTY REALTY": "^CNXREALTY", "NIFTY ENERGY": "^CNXENERGY", "NIFTY FIN SERVICE": "^CNXFIN"
    }

    sector_perf = []
    for name, ticker in sectors.items():
        try:
            h = yf.Ticker(ticker).history(period="10d").tail(5)
            pct = ((h['Close'].iloc[-1] - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
            sector_perf.append({"name": name.replace("NIFTY ", ""), "pct": pct})
        except: continue

    sec_df = pd.DataFrame(sector_perf)
    report += f"=== SECTORS 5-DAY ===\nTop 5 Gainers:\n"
    for _, row in sec_df.nlargest(5, 'pct').iterrows():
        report += f"{row['name']}: {row['pct']:.2f}%\n"
    report += f"\nTop 5 Losers:\n"
    for _, row in sec_df.nsmallest(5, 'pct').iterrows():
        report += f"{row['name']}: {row['pct']:.2f}%\n\n"

    # 3. NIFTY 500 STOCKS - Gainers/Losers/Volume Surge
    print("Fetching Nifty 500 data...")
    # Using a smaller list for GitHub Actions speed. Full 500 takes too long.
    nifty500 = [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICIBANK.NS","INFY.NS","HINDUNILVR.NS","ITC.NS",
        "SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS","LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS",
        "SUNPHARMA.NS","TITAN.NS","BAJFINANCE.NS","ULTRACEMCO.NS","WIPRO.NS","NESTLEIND.NS",
        "ADANIENT.NS","ADANIPORTS.NS","APOLLOHOSP.NS","BAJAJ-AUTO.NS","BPCL.NS","BRITANNIA.NS",
        "CIPLA.NS","COALINDIA.NS","DIVISLAB.NS","DRREDDY.NS","EICHERMOT.NS","GRASIM.NS","HCLTECH.NS",
        "HDFCLIFE.NS","HEROMOTOCO.NS","HINDALCO.NS","INDUSINDBK.NS","JSWSTEEL.NS","M&M.NS",
        "NTPC.NS","ONGC.NS","POWERGRID.NS","SBILIFE.NS","TATACONSUM.NS","TATAMOTORS.NS",
        "TATASTEEL.NS","TECHM.NS","UPL.NS","VEDL.NS","BAJAJFINSV.NS"
    ]

    data = yf.download(nifty500, period="10d", group_by='ticker', progress=False)
    stock_perf = []

    for stock in nifty500:
        try:
            h = data[stock].tail(5)
            if len(h) < 5: continue
            pct_5d = ((h['Close'].iloc[-1] - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
            vol_avg = h['Volume'].iloc[:-1].mean() # Avg of first 4 days
            vol_today = h['Volume'].iloc[-1]
            vol_surge = ((vol_today - vol_avg) / vol_avg) * 100 if vol_avg > 0 else 0

            stock_perf.append({
                "symbol": stock.replace(".NS", ""),
                "pct": pct_5d,
                "ltp": h['Close'].iloc[-1],
                "vol_surge": vol_surge,
                "vol": vol_today
            })
        except: continue

    df = pd.DataFrame(stock_perf)

    report += f"=== STOCKS 5-DAY ===\nTop 5 Gainers:\n"
    for _, row in df.nlargest(5, 'pct').iterrows():
        report += f"{row['symbol']}: {row['ltp']:.2f} ({row['pct']:.2f}%)\n"

    report += f"\nTop 5 Losers:\n"
    for _, row in df.nsmallest(5, 'pct').iterrows():
        report += f"{row['symbol']}: {row['ltp']:.2f} ({row['pct']:.2f}%)\n"

    report += f"\nTop 5 Volume Surge:\n"
    for _, row in df.nlargest(5, 'vol_surge').iterrows():
        report += f"{row['symbol']}: {row['vol_surge']:.0f}% ({row['vol']/100000:.1f}L)\n\n"

    # 4. HIGH DELIVERY - Use BSE public API
    print("Fetching BSE delivery...")
    try:
        url = "https://api.bseindia.com/BseIndiaAPI/api/HighLowDeliverableQty/w"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        del_data = r.json()['Table'][:5]

        report += f"=== TOP 5 HIGH DELIVERY BSE ===\n"
        for stock in del_data:
            report += f"{stock['scripname']}: {stock['delivPer']}% deliv\n"
    except Exception as e:
        report += f"=== HIGH DELIVERY ===\nBSE data failed: {str(e)[:50]}\n"

    return report

def send_mail(body):
    gmail_user = os.getenv('GMAIL_USER')
    gmail_pass = os.getenv('GMAIL_PASS')
    to_email = os.getenv('TO_EMAIL')

    msg = MIMEText(body)
    msg['Subject'] = f"NSE EOD Crux - {datetime.now().strftime('%d %b')}"
    msg['From'] = gmail_user
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.send_message(msg)
    print("Report sent successfully")

if __name__ == "__main__":
    try:
        report_body = get_report()
        print(report_body)
        send_mail(report_body)
    except Exception as e:
        print("FATAL ERROR:")
        print(traceback.format_exc())
        exit(1)
