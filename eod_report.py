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
        return f"=== {title} ===\nData failed: {str(e)[:150]}\n\n"

def get_report():
    report = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}\n"
    report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n"
    report += f"Data: Last 5 traded days\n\n"

    def indices():
        nifty = yf.Ticker("^NSEI")
        hist = nifty.history(period="1mo")
        hist = hist[hist['Volume'] > 0].tail(5)
        chg_5d = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        day_chg = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
        return f"=== NIFTY 50 ===\nLTP: {hist['Close'].iloc[-1]:.2f} | 1-Day: {day_chg:.2f}% | 5-Day: {chg_5d:.2f}%\nPeriod: {hist.index[0].strftime('%d %b')} to {hist.index[-1].strftime('%d %b')}\n\n"

    def sectors():
        sectors = {
            "BANK": "^NSEBANK", "IT": "^CNXIT", "AUTO": "^CNXAUTO",
            "FMCG": "^CNXFMCG", "PHARMA": "^CNXPHARMA", "METAL": "^CNXMETAL",
            "REALTY": "^CNXREALTY", "ENERGY": "^CNXENERGY", "FIN SERVICE": "^CNXFIN"
        }
        sector_perf = []
        for name, ticker in sectors.items():
            try:
                h = yf.Ticker(ticker).history(period="1mo")
                h = h[h['Volume'] > 0].tail(5)
                if len(h) == 5:
                    pct = ((h['Close'].iloc[-1] - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
                    sector_perf.append({"name": name, "pct": pct})
            except: continue

        sec_df = pd.DataFrame(sector_perf)
        out = f"=== SECTORS 5-DAY ===\nTop 5 Gainers:\n"
        for _, row in sec_df.nlargest(5, 'pct').iterrows():
            out += f"{row['name']}: {row['pct']:.2f}%\n"
        out += f"\nTop 5 Losers:\n"
        for _, row in sec_df.nsmallest(5, 'pct').iterrows():
            out += f"{row['name']}: {row['pct']:.2f}%\n\n"
        return out

    def stocks():
        stocks = [
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","HINDUNILVR.NS","ITC.NS",
            "SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS","LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS",
            "SUNPHARMA.NS","TITAN.NS","BAJFINANCE.NS","ULTRACEMCO.NS","WIPRO.NS","NESTLEIND.NS",
            "ADANIENT.NS","ADANIPORTS.NS","CIPLA.NS","COALINDIA.NS","DRREDDY.NS","HCLTECH.NS",
            "HINDALCO.NS","TATAMOTORS.NS","TATASTEEL.NS","TECHM.NS"
        ]
        data = yf.download(stocks, period="1mo", group_by='ticker', progress=False)
        stock_perf = []
        for stock in stocks:
            try:
                h = data[stock]
                h = h[h['Volume'] > 0].tail(5)
                if len(h) < 5: continue
                pct_5d = ((h['Close'].iloc[-1] - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
                vol_avg = h['Volume'].iloc[:-1].mean()
                vol_surge = ((h['Volume'].iloc[-1] - vol_avg) / vol_avg) * 100 if vol_avg > 0 else 0
                stock_perf.append({
                    "symbol": stock.replace(".NS", ""),
                    "pct": pct_5d,
                    "ltp": h['Close'].iloc[-1],
                    "vol_surge": vol_surge,
                    "vol": h['Volume'].iloc[-1]
                })
            except: continue

        df = pd.DataFrame(stock_perf)
        out = f"=== STOCKS 5-DAY ===\nTop 5 Gainers:\n"
        for _, row in df.nlargest(5, 'pct').iterrows():
            out += f"{row['symbol']}: {row['ltp']:.2f} ({row['pct']:.2f}%)\n"
        out += f"\nTop 5 Losers:\n"
        for _, row in df.nsmallest(5, 'pct').iterrows():
            out += f"{row['symbol']}: {row['ltp']:.2f} ({row['pct']:.2f}%)\n"
        out += f"\nTop 5 Volume Surge:\n"
        for _, row in df.nlargest(5, 'vol_surge').iterrows():
            out += f"{row['symbol']}: {row['vol_surge']:.0f}% ({row['vol']/100000:.1f}L)\n\n"
        return out

    report += safe_section("INDICES", indices)
    report += safe_section("SECTORS", sectors)
    report += safe_section("STOCKS", stocks)
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
        try:
            send_mail(f"Script crashed:\n\n{traceback.format_exc()}")
        except: pass
        exit(1)
