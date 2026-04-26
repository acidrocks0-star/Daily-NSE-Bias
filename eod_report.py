import smtplib, os, traceback
import yfinance as yf
import pandas as pd
import requests
from email.mime.text import MIMEText
from datetime import datetime
from io import StringIO

report = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}\n"
report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n\n"

def get_fii_dii():
    try:
        # NSE FII/DII data - Cash + F&O
        url = "https://www.nseindia.com/api/fiidiiTradeReact"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Referer": "https://www.nseindia.com/reports/fii-dii"
        }
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        r = session.get(url, headers=headers, timeout=10)
        data = r.json()

        out = f"=== FII/DII + PRO - {data[0]['date']} ===\n"

        # Cash Market
        fii_cash = float(data[0]['fiiBuyValue']) - float(data[0]['fiiSellValue'])
        dii_cash = float(data[0]['diiBuyValue']) - float(data[0]['diiSellValue'])
        pro_cash = float(data[0]['proBuyValue']) - float(data[0]['proSellValue'])

        out += f"Cash: FII {fii_cash:+.0f}Cr | DII {dii_cash:+.0f}Cr | PRO {pro_cash:+.0f}Cr\n"

        # F&O - Index Futures
        fii_idx_fut = float(data[0]['fiiIndexFutBuy']) - float(data[0]['fiiIndexFutSell'])
        dii_idx_fut = float(data[0]['diiIndexFutBuy']) - float(data[0]['diiIndexFutSell'])
        pro_idx_fut = float(data[0]['proIndexFutBuy']) - float(data[0]['proIndexFutSell'])

        out += f"Index Fut: FII {fii_idx_fut:+.0f}Cr | DII {dii_idx_fut:+.0f}Cr | PRO {pro_idx_fut:+.0f}Cr\n"

        # F&O - Index Options Net
        fii_idx_opt = float(data[0]['fiiIndexOptBuy']) - float(data[0]['fiiIndexOptSell'])
        dii_idx_opt = float(data[0]['diiIndexOptBuy']) - float(data[0]['diiIndexOptSell'])
        pro_idx_opt = float(data[0]['proIndexOptBuy']) - float(data[0]['proIndexOptSell'])

        out += f"Index Opt: FII {fii_idx_opt:+.0f}Cr | DII {dii_idx_opt:+.0f}Cr | PRO {pro_idx_opt:+.0f}Cr\n"

        # Bias calculation
        total_fii = fii_cash + fii_idx_fut + fii_idx_opt
        total_dii = dii_cash + dii_idx_fut + dii_idx_opt
        total_pro = pro_cash + pro_idx_fut + pro_idx_opt

        def bias(val):
            if val > 500: return "Strong Bullish"
            if val > 100: return "Bullish"
            if val < -500: return "Strong Bearish"
            if val < -100: return "Bearish"
            return "Neutral"

        out += f"\nBias: FII {bias(total_fii)} ({total_fii:+.0f}Cr) | "
        out += f"DII {bias(total_dii)} ({total_dii:+.0f}Cr) | "
        out += f"PRO {bias(total_pro)} ({total_pro:+.0f}Cr)\n\n"
        return out
    except Exception as e:
        return f"=== FII/DII ===\nData failed: {str(e)[:100]}\n\n"

def get_gift_nifty():
    try:
        # Investing.com Gift Nifty
        url = "https://api.investing.com/api/financialdata/1175151/historical/chart/?interval=PT1M&pointscount=1"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
        price = data['data'][0][1]
        change = data['data'][0][2]
        out = f"=== GIFT NIFTY ===\n"
        out += f"LTP: {price:.2f} ({change:+.2f}%)\n\n"
        return out
    except:
        try:
            # Fallback: NSE India Gift Nifty
            url = "https://www.nseindia.com/api/equity-stockIndices?index=GIFT NIFTY"
            headers = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}
            session = requests.Session()
            session.get("https://www.nseindia.com", headers=headers, timeout=5)
            r = session.get(url, headers=headers, timeout=10)
            data = r.json()
            last = data['data'][0]['last']
            pchange = data['data'][0]['pChange']
            out = f"=== GIFT NIFTY ===\n"
            out += f"LTP: {last} ({pchange:+.2f}%)\n\n"
            return out
        except Exception as e:
            return f"=== GIFT NIFTY ===\nData failed: {str(e)[:100]}\n\n"

try:
    stocks = [
        "RELIANCE.NS","TCS.NS","HDFCBANK.NS","ICICIBANK.NS","INFY.NS","HINDUNILVR.NS","ITC.NS",
        "SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS","LT.NS","AXISBANK.NS","MARUTI.NS",
        "SUNPHARMA.NS","WIPRO.NS","TITAN.NS","BAJFINANCE.NS","ULTRACEMCO.NS","NESTLEIND.NS"
    ]

    sectors = {
        "BANK": "^NSEBANK", "IT": "^CNXIT", "AUTO": "^CNXAUTO",
        "FMCG": "^CNXFMCG", "PHARMA": "^CNXPHARMA", "METAL": "^CNXMETAL",
        "REALTY": "^CNXREALTY", "ENERGY": "^CNXENERGY"
    }

    data = yf.download(stocks, period="1mo", group_by='ticker', progress=False, threads=False)
    sector_data = yf.download(list(sectors.values()), period="1mo", group_by='ticker', progress=False, threads=False)

    ref_hist = data['RELIANCE.NS']
    ref_hist = ref_hist[ref_hist['Volume'] > 0].tail(5)
    trading_days = ref_hist.index

    report += f"=== DAILY TOP MOVERS - LAST 5 TRADING DAYS ===\n"
    report += f"Period: {trading_days[0].strftime('%d %b')} to {trading_days[-1].strftime('%d %b')}\n\n"

    for day in trading_days:
        day_str = day.strftime('%d %b, %A')
        daily_perf = []
        sector_perf = []

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
                vol = h['Volume'].iloc[idx]
                vol_avg = h['Volume'].iloc[max(0,idx-4):idx].mean()
                vol_surge = ((vol - vol_avg) / vol_avg * 100) if vol_avg > 0 else 0
                daily_perf.append({"symbol": stock.replace(".NS", ""), "pct": pct, "vol_surge": vol_surge})
            except: continue

        for name, ticker in sectors.items():
            try:
                h = sector_data[ticker]
                if day not in h.index: continue
                idx = h.index.get_loc(day)
                if idx == 0: continue
                today_close = h['Close'].iloc[idx]
                prev_close = h['Close'].iloc[idx-1]
                if pd.isna(today_close) or pd.isna(prev_close) or prev_close == 0: continue
                pct = ((today_close - prev_close) / prev_close) * 100
                sector_perf.append({"name": name, "pct": pct})
            except: continue

        report += f"--- {day_str} ---\n"
        if daily_perf:
            df = pd.DataFrame(daily_perf)
            report += f"Stocks: Gainers: {', '.join([f'{r['symbol']}({r['pct']:+.1f}%)' for _, r in df.nlargest(3, 'pct').iterrows()])} | "
            report += f"Losers: {', '.join([f'{r['symbol']}({r['pct']:+.1f}%)' for _, r in df.nsmallest(3, 'pct').iterrows()])}\n"
            report += f"Vol Surge: {', '.join([f'{r['symbol']}({r['vol_surge']:+.0f}%)' for _, r in df.nlargest(3, 'vol_surge').iterrows()])}\n"
        if sector_perf:
            sec_df = pd.DataFrame(sector_perf)
            report += f"Sectors: Gainers: {', '.join([f'{r['name']}({r['pct']:+.1f}%)' for _, r in sec_df.nlargest(3, 'pct').iterrows()])} | "
            report += f"Losers: {', '.join([f'{r['name']}({r['pct']:+.1f}%)' for _, r in sec_df.nsmallest(3, 'pct').iterrows()])}\n"
        report += f"\n"

    # Add FII/DII + Gift Nifty - 1 day only
    report += get_fii_dii()
    report += get_gift_nifty()

except Exception as e:
    report += f"\nERROR: {str(e)}\n"
    report += f"Traceback:\n{traceback.format_exc()}\n"

# Send email
gmail_user = os.getenv('GMAIL_USER')
gmail_pass = os.getenv('GMAIL_PASS')
to_email = os.getenv('TO_EMAIL')

msg = MIMEText(report)
msg['Subject'] = f"NSE EOD Crux - {datetime.now().strftime('%d %b')}"
msg['From'] = gmail_user
msg['To'] = to_email

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(gmail_user, gmail_pass)
    smtp.send_message(msg)
print("Email sent")
