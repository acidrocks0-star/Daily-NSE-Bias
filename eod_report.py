import smtplib, os, traceback
from email.mime.text import MIMEText
from datetime import datetime

def get_nse_eod():
    try:
        from nsepython import nse_eq, nse_get_top_gainers
        print("Trying NSE Python...")
        all_indices = nse_eq("all")
        nifty_50 = all_indices[all_indices['indexName'] == 'NIFTY 50'].iloc[0]
        gainers = nse_get_top_gainers().head(5)

        report = f"""NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}
Source: NSE

NIFTY 50: {nifty_50['last']} ({round(nifty_50['percentChange'], 2)}%)
Open: {nifty_50['open']} | High: {nifty_50['high']} | Low: {nifty_50['low']}

Top 5 Gainers:
"""
        for idx, row in gainers.iterrows():
            report += f"{row['symbol']}: {row['ltp']} ({row['netPrice']}%)\n"
        return report

    except Exception as nse_error:
        print(f"NSE failed: {nse_error}")
        print("Falling back to Yahoo Finance...")

        import yfinance as yf
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="2d")
        today = hist.iloc[-1]
        prev = hist.iloc[-2]
        change = ((today['Close'] - prev['Close']) / prev['Close']) * 100

        report = f"""NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}
Source: Yahoo Finance (NSE fallback)

NIFTY 50: {today['Close']:.2f} ({change:.2f}%)
Open: {today['Open']:.2f} | High: {today['High']:.2f} | Low: {today['Low']:.2f}
Prev Close: {prev['Close']:.2f}
"""
        return report

def send_mail(body):
    gmail_user = os.getenv('GMAIL_USER')
    gmail_pass = os.getenv('GMAIL_PASS')
    to_email = os.getenv('TO_EMAIL')

    msg = MIMEText(body)
    msg['Subject'] = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y')}"
    msg['From'] = gmail_user
    msg['To'] = to_email

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.send_message(msg)
    print("EOD Report sent successfully to", to_email)

if __name__ == "__main__":
    try:
        report_body = get_nse_eod()
        print("Report:\n", report_body)
        send_mail(report_body)
    except Exception as e:
        print("FATAL ERROR:")
        print(traceback.format_exc())
        exit(1)
