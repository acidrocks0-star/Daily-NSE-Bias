import smtplib, os
from email.mime.text import MIMEText
from datetime import datetime
from nsepython import nse_eq

def get_nse_eod():
    print("Fetching Nifty 50 data...")
    nifty_data = nse_eq("NIFTY 50")

    print("Fetching all indices...")
    all_indices = nse_eq("all")
    nifty_50 = all_indices[all_indices['indexName'] == 'NIFTY 50'].iloc[0]

    # Get top gainers from Nifty 50 stocks
    print("Fetching top gainers...")
    from nsepython import nse_get_top_gainers
    gainers = nse_get_top_gainers()
    top_5 = gainers.head(5)

    report = f"""NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}
Time: {datetime.now().strftime('%I:%M %p')} IST

NIFTY 50: {nifty_50['last']} ({round(nifty_50['percentChange'], 2)}%)
Open: {nifty_50['open']} | High: {nifty_50['high']} | Low: {nifty_50['low']}
Previous Close: {nifty_50['previousClose']}

Top 5 Gainers Today:
"""
    for idx, row in top_5.iterrows():
        report += f"{row['symbol']}: {row['ltp']} ({row['netPrice']}%)\n"

    return report

def send_mail(body):
    gmail_user = os.getenv('GMAIL_USER')
    gmail_pass = os.getenv('GMAIL_PASS')
    to_email = os.getenv('TO_EMAIL')

    if not all([gmail_user, gmail_pass, to_email]):
        raise Exception("Missing email secrets")

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
        print("Report generated:\n", report_body)
        send_mail(report_body)
    except Exception as e:
        print("ERROR:", str(e))
        exit(1)
