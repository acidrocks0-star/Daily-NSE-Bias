import smtplib, os
from email.mime.text import MIMEText
from datetime import datetime

print("=== Starting EOD Report Test ===")
print("Time:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

gmail_user = os.getenv('GMAIL_USER')
gmail_pass = os.getenv('GMAIL_PASS') 
to_email = os.getenv('TO_EMAIL')

print("GMAIL_USER set:", bool(gmail_user))
print("GMAIL_PASS set:", bool(gmail_pass))
print("TO_EMAIL set:", bool(to_email))
print("Sending to:", to_email)

if not all([gmail_user, gmail_pass, to_email]):
    print("ERROR: One or more secrets missing!")
    exit(1)

msg = MIMEText("Test email from GitHub Actions.\n\nIf you got this, your workflow works!")
msg['Subject'] = 'GitHub Actions EOD Test'
msg['From'] = gmail_user
msg['To'] = to_email

try:
    print("Connecting to Gmail...")
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        print("Logging in...")
        smtp.login(gmail_user, gmail_pass)
        print("Login successful. Sending mail...")
        smtp.send_message(msg)
        print("Mail sent successfully")
except Exception as e:
    print("ERROR sending mail:", str(e))
    exit(1)

print("=== Script completed ===")
