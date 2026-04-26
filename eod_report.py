import smtplib, os, traceback
import yfinance as yf
import pandas as pd
from email.mime.text import MIMEText
from datetime import datetime

report = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}\n"
report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n\n"

try:
    stocks = [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS",
        "HINDUNILVR.NS","ITC.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS"
    ]
    report += f"DEBUG: Downloading {len(stocks)} stocks...\n"

    data = yf.download(stocks, period="1mo", group_by='ticker', progress=False, threads=False)

    if data.empty:
        report += "ERROR: yf.download returned empty dataframe. Yahoo blocked request.\n"
    else:
        report += f"DEBUG: Download success. Data shape: {data.shape}\n"

    nifty_hist = yf.Ticker("^NSEI").history(period="1mo")
    nifty_hist = nifty_hist[nifty_hist['Volume'] > 0].tail(5)
    trading_days = nifty_hist.index

    report += f"DEBUG: Found {len(trading_days)} trading days\n"
    report += f"DEBUG: Dates: {[d.strftime('%d %b') for d in trading_days]}\n\n"

    if len(trading_days) == 0:
        report += "ERROR: No trading days found in last month\n"
    else:
        report += f"=== DAILY TOP MOVERS - LAST 5 TRADING DAYS ===\n\n"

        for day in trading_days:
            day_str = day.strftime('%d %b, %A')
            daily_perf = []
            stocks_found = 0

            for stock in stocks:
                try:
                    h = data[stock]
                    if day in h.index:
                        stocks_found += 1
                        idx = h.index.get_loc(day)
                        if idx > 0:
                            today_close = h['Close'].iloc[idx]
                            prev_close = h['Close'].iloc[idx-1]
                            if not pd.isna(today_close) and not pd.isna(prev_close) and prev_close!= 0:
                                pct = ((today_close - prev_close) / prev_close) * 100
                                daily_perf.append({
                                    "symbol": stock.replace(".NS", ""),
                                    "pct": pct,
                                    "ltp": today_close
                                })
                except Exception as e:
                    continue

            report += f"--- {day_str} --- Found data for {stocks_found}/{len(stocks)} stocks\n"

            if not daily_perf:
                report += "No valid price data for this day\n\n"
                continue

            df = pd.DataFrame(daily_perf)
            report += f"Top 5 Gainers:\n"
            for _, row in df.nlargest(5, 'pct').iterrows():
                report += f"{row['symbol']}: {row['ltp']:.2f} ({row['pct']:.2f}%)\n"
            report += f"\nTop 5 Losers:\n"
            for _, row in df.nsmallest(5, 'pct').iterrows():
                report += f"{row['symbol']}: {row['ltp']:.2f} ({row['pct']:.2f}%)\n\n"

except Exception as e:
    report += f"\nFATAL ERROR: {str(e)}\n"
    report += f"Traceback:\n{traceback.format_exc()}\n"

# Send email
gmail_user = os.getenv('GMAIL_USER')
gmail_pass = os.getenv('GMAIL_PASS')
to_email = os.getenv('TO_EMAIL')

msg = MIMEText(report)
msg['Subject'] = f"NSE Debug - {datetime.now().strftime('%d %b')}"
msg['From'] = gmail_user
msg['To'] = to_email

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(gmail_user, gmail_pass)
    smtp.send_message(msg)
print("Email sent")
