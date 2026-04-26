def get_report():
    report = f"NSE EOD Report - {datetime.now().strftime('%d %b %Y, %A')}\n"
    report += f"Generated: {datetime.now().strftime('%I:%M %p')} IST\n"
    report += f"Data: Last 5 traded days\n\n"

    # 1. INDICES - Fetch 1 month to guarantee 5 trading days
    print("Fetching indices...")
    nifty = yf.Ticker("^NSEI")
    hist = nifty.history(period="1mo") # 1 month = ~22 trading days
    hist = hist[hist['Volume'] > 0] # Remove holidays/zero volume days
    last5 = hist.tail(5) # Now guaranteed 5 actual trading sessions

    if len(last5) < 5:
        raise Exception(f"Only {len(last5)} trading days found in last month")

    chg_5d = ((last5['Close'].iloc[-1] - last5['Close'].iloc[0]) / last5['Close'].iloc[0]) * 100
    day_chg = ((last5['Close'].iloc[-1] - last5['Close'].iloc[-2]) / last5['Close'].iloc[-2]) * 100

    report += f"=== NIFTY 50 ===\n"
    report += f"LTP: {last5['Close'].iloc[-1]:.2f} | 1-Day: {day_chg:.2f}% | 5-Day: {chg_5d:.2f}%\n"
    report += f"Period: {last5.index[0].strftime('%d %b')} to {last5.index[-1].strftime('%d %b')}\n\n"

    # 2. SECTORS - Same fix
    print("Fetching sectors...")
    sectors = {
        "NIFTY BANK": "^NSEBANK", "NIFTY IT": "^CNXIT", "NIFTY AUTO": "^CNXAUTO",
        "NIFTY FMCG": "^CNXFMCG", "NIFTY PHARMA": "^CNXPHARMA", "NIFTY METAL": "^CNXMETAL",
        "NIFTY REALTY": "^CNXREALTY", "NIFTY ENERGY": "^CNXENERGY", "NIFTY FIN SERVICE": "^CNXFIN"
    }

    sector_perf = []
    for name, ticker in sectors.items():
        try:
            h = yf.Ticker(ticker).history(period="1mo")
            h = h[h['Volume'] > 0].tail(5) # Only trading days
            if len(h) == 5:
                pct = ((h['Close'].iloc[-1] - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
                sector_perf.append({"name": name.replace("NIFTY ", ""), "pct": pct})
        except: continue

    # Rest of code stays same...
