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
    report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n\n"

    def indices():
        # Use NIFTYBEES for volume data since ^NSEI has no volume
        nifty = yf.Ticker("NIFTYBEES.NS")
        hist = nifty.history(period="1mo")
        hist = hist[hist['Volume'] > 0].tail(5)

        out = f"=== NIFTY 50 - LAST 5 TRADING DAYS ===\n"
        out += f"Date | Close* | Chg% | Volume\n"
        out += f"-----------|----------|--------|--------\n"

        for i in range(len(hist)):
            date = hist.index[i].strftime('%d %b')
            close = hist['Close'].iloc[i] * 100 # NIFTYBEES is 1/100th of Nifty
            vol = hist['Volume'].iloc[i] / 100000 # Lakhs
            if i == 0:
                chg = 0
            else:
                chg = ((close - hist['Close'].iloc[i-1]*100) / (hist['Close'].iloc[i-1]*100) * 100
            out += f"{date} | {close:8.2f} | {chg:6.2f}% | {vol:5.1f}L\n"

        chg_5d = ((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0]) * 100
        out += f"\n*Price via NIFTYBEES ETF x100\n"
        out += f"5-Day Return: {chg_5d:.2f}%\n"
        out += f"Period: {hist.index[0].strftime('%d %b')} to {hist.index[-1].strftime('%d %b')}\n\n"
        return out

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
        gainers = sec_df[sec_df['pct'] > 0].nlargest(5, 'pct')
        losers = sec_df[sec_df['pct'] <= 0].nsmallest(5, 'pct')

        out = f"=== SECTORS 5-DAY ===\nTop Gainers:\n"
        for _, row in gainers.iterrows():
            out += f"{row['name']}: {row['pct']:.2f}%\n"
        out += f"\nTop Losers:\n"
        for _, row in losers.iterrows():
            out += f"{row['name']}: {row['pct']:.2f}%\n\n"
        return out

    def stocks():
        stocks = [
            "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","HINDUNILVR.NS","ITC.NS",
            "SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS","LT.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS",
            "SUNPHARMA.NS","TITAN.NS","BAJFINANCE.NS","ULTRACEMCO.NS","WIPRO.NS","NESTLEIND.NS",
            "CIPLA.NS","COALINDIA.NS","DRREDDY.NS","HCLTECH.NS","HINDALCO.NS","TECHM.NS"
        ]
        data = yf.download(stocks, period="1mo", group_by='ticker', progress=False)

        # First calculate 5-day returns to find top movers
        stock_perf = []
        stock_hist = {}
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
                    "vol_surge": vol_surge,
                    "hist": h
                })
                stock_hist[stock.replace(".NS", "")] = h
            except: continue

        df = pd.DataFrame(stock_perf)
        top_gainers = df.nlargest(5, 'pct')
        top_losers = df.nsmallest(5, 'pct')

        out = f"=== TOP 5 GAINERS - 5 DAY BREAKDOWN ===\n"
        for _, row in top_gainers.iterrows():
            h = stock_hist[row['symbol']]
            out += f"\n{row['symbol']}: {row['pct']:.2f}% in 5 days\n"
            out += f"Date | Close | Chg% | Vol(L)\n"
            out += f"-----|-------|------|--------\n"
            for i in range(len(h)):
                d = h.index[i].strftime('%d %b')
                c = h['Close'].iloc[i]
                v = h['Volume'].iloc[i] / 100000
                chg = 0 if i == 0 else ((c - h['Close'].iloc[i-1]) / h['Close'].iloc[i-1]) * 100
                out += f"{d} | {c:7.2f} | {chg:5.2f}% | {v:6.1f}\n"

        out += f"\n=== TOP 5 LOSERS - 5 DAY BREAKDOWN ===\n"
        for _, row in top_losers.iterrows():
            h = stock_hist[row['symbol']]
            out += f"\n{row['symbol']}: {row['pct']:.2f}% in 5 days\n"
            out += f"Date | Close | Chg% | Vol(L)\n"
            out += f"-----|-------|------|--------\n"
            for i in range(len(h)):
                d = h.index[i].strftime('%d %b')
                c = h['Close'].iloc[i]
                v = h['Volume'].iloc[i] / 100000
                chg = 0 if i == 0 else ((c - h['Close'].iloc[i-1]) / h['Close'].iloc[i-1]) * 100
                out += f"{d} | {c:7.2f} | {chg:5.2f}% | {v:6.1f}\n"

        out += f"\n=== TOP 5 VOLUME SURGE ===\n"
        for _, row in df.nlargest(5, 'vol_surge').iterrows():
            out += f"{row['symbol']}: {row['vol_surge']:.0f}% surge\n"
        out += "\n"
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
