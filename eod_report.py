import smtplib, os, traceback
import yfinance as yf
import pandas as pd
from email.mime.text import MIMEText
from datetime import datetime

def safe_section(title, func):
    try:
        return func()
    except Exception as e:
        print(f"ERROR in {title}: {e}")
        return f"=== {title} ===\nData failed: {str(e)[:100]}\n\n"

def get_report():
    report = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}\n"
    report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n\n"

    def indices():
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="1mo")
        hist = hist[hist['Volume'] > 0].tail(5)
        chg_5d = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        day_chg = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
        return f"=== NIFTY 50 ===\nLTP: {hist['Close'].iloc[-1]:.2f} | 1-Day: {day_chg:.2f}% | 5-Day: {chg_5d:.2f}%\nPeriod: {hist.index[0].strftime('%d %b')} to {hist.index[-1].strftime('%d %b')}\n\n"

    report += safe_section("INDICES", indices)

    # Add sectors + stocks sections same way wrapped in safe_section()
    # If any section crashes, email still sends with error message

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
        send_mail(report_body) # This ALWAYS runs now
    except Exception as e:
        print("FATAL ERROR:")
        print(traceback.format_exc())
        # Even if everything fails, send error email
        try:
            send_mail(f"Script crashed:\n\n{traceback.format_exc()}")
        except: pass
        exit(1)
