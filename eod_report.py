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
        "SUNPHARMA.NS","WIPRO.NS","NESTLEIND.NS","CIPLA.NS","COALINDIA.NS","DRREDDY.NS",
        "HCLTECH.NS","HINDALCO.NS","TECHM.NS","TATAMOTORS.NS","TATASTEEL.NS"
    ]

    data = yf.download(stocks, period="1mo", group_by='ticker', progress=False, threads=False)

    # Get last 5 trading days
    nifty_hist = yf.Ticker("^NSEI").history(period="1mo")
    nifty_hist = nifty_hist[nifty_hist['Volume'] > 0].tail(5)
    trading_days = nifty_hist.index

    if len(trading_days) == 0:
        report += "ERROR: No trading days found\n"
    else:
        report += f"=== DAILY TOP MOVERS - LAST 5 TRADING DAYS ===\n\n"

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

                    daily_perf.append({
                        "symbol": stock.replace(".NS", ""),
                        "pct": pct,
                        "ltp": today_close
                    })
                except: continue

            if not daily_perf: continue
            df = pd.DataFrame(daily_perf)

            report += f"--- {day_str} ---\nTop 5 Gainers:\n"
            for _, row in df.nlargest(5, 'pct').iterrows():
                report += f"{row['symbol']}: {row['ltp']:.2f} ({row['pct']:.2f}%)\n"
            report += f"\nTop 5 Losers:\n"
            for _, row in df.nsmallest(5, 'pct').iterrows():
                report += f"{row['symbol']}: {row['ltp']:.2f} ({row['pct']:.2f}%)\n\n"

except Exception as e:
    report += f"\nERROR: {str(e)}\n"
    report += f"Traceback:\n{traceback.format_exc()}\n"

# Send email no matter what
gmail_user = os.getenv('GMAIL_USER')
gmail_pass = os.getenv('GMAIL_PASS')
to_email = os.getenv('TO_EMAIL')

msg = MIMEText(report)
msg['Subject'] = f"NSE Daily Movers - {datetime.now().strftime('%d %b')}"
msg['From'] = gmail_user
msg['To'] = to_email

try:
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.send_message(msg)
    print("Email sent")
except Exception as e:
    print(f"Email failed: {e}")
    exit(1)
