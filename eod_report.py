import smtplib, os, requests
from email.mime.text import MIMEText
from datetime import datetime

# 1. Get NSE data
def get_nse_eod():
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
        "Referer": "https://www.nseindia.com/"
    }
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers) # Get cookies first
    r = session.get(url, headers=headers, timeout=10)
    data = r.json()

    nifty = data['data'][0]
    adv = data['advance']

    report = f"""
NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}
Time: {datetime.now().strftime('%I:%M %p')} IST

NIFTY 50: {nifty['last']} ({nifty['pChange']}%)
Open: {nifty['open']} | High: {nifty['dayHigh']} | Low: {nifty['dayLow']}

Market Breadth:
Advances: {adv['advances']} | Declines: {adv['declines']} | Unchanged: {adv['unchanged']}

Top Gainers:
"""
    for stock in data['data'][1:6]: # Top 5
        report += f"{stock['symbol']}: {stock['lastPrice']} ({stock['pChange']}%)\n"

    return report

# 2. Send email
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

# 3. Run
if __name__ == "__main__":
    try:
        print("Fetching NSE data...")
        report_body = get_nse_eod()
        print("Sending email...")
        send_mail(report_body)
    except Exception as e:
        print("ERROR:", str(e))
        exit(1)
