import os
import datetime
import zoneinfo
import pandas as pd
import requests
import yfinance as yf

# --- CONFIGURAZIONE ---
TOKEN_TELEGRAM = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_TELEGRAM = os.getenv("TELEGRAM_CHAT_ID")
SOGLIA_PERDITA = -5.0  

def get_market_state():
    """Rileva lo stato del mercato di New York."""
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    ora_ny = datetime.datetime.now(tz_ny)

    if ora_ny.weekday() >= 5:
        return "CLOSED"

    ora_corrente = ora_ny.time()
    
    # Sessioni operative (orari NY)
    inizio_pre = datetime.time(4, 0, 0)
    apertura_reg = datetime.time(9, 30, 0)
    chiusura_reg = datetime.time(16, 0, 0)

    if inizio_pre <= ora_corrente < apertura_reg:
        return "PRE_MARKET"
    
    if apertura_reg <= ora_corrente <= chiusura_reg:
        return "REGULAR"
    
    return "CLOSED"

def ottieni_componenti_locali():
    """Restituisce i principali colossi dello S&P 500 salvati localmente nel codice."""
    # Lista pre-mappata delle aziende a più alta capitalizzazione per evitare errori di rete
    ticker_nomi = {
        "MSFT": "Microsoft Corporation",
        "AAPL": "Apple Inc.",
        "NVDA": "NVIDIA Corporation",
        "AMZN": "Amazon.com, Inc.",
        "META": "Meta Platforms, Inc.",
        "GOOGL": "Alphabet Inc. (Class A)",
        "GOOG": "Alphabet Inc. (Class C)",
        "BRK-B": "Berkshire Hathaway Inc.",
        "LLY": "Eli Lilly and Company",
        "AVGO": "Broadcom Inc.",
        "JPM": "JPMorgan Chase & Co.",
        "TSLA": "Tesla, Inc.",
        "UNH": "UnitedHealth Group Inc.",
        "V": "Visa Inc.",
        "XOM": "Exxon Mobil Corporation",
        "MA": "Mastercard Incorporated",
        "HD": "The Home Depot, Inc.",
        "PG": "Procter & Gamble Company",
        "COST": "Costco Wholesale Corporation",
        "JNJ": "Johnson & Johnson",
        "AMD": "Advanced Micro Devices, Inc.",
        "NFLX": "Netflix, Inc.",
        "MRK": "Merck & Co., Inc.",
        "ORCL": "Oracle Corporation",
        "BAC": "Bank of America Corporation",
        "CVX": "Chevron Corporation",
        "CRM": "Salesforce, Inc.",
        "WMT": "Walmart Inc.",
        "PEP": "PepsiCo, Inc.",
        "KO": "The Coca-Cola Company",
        "ADBE": "Adobe Inc.",
        "TMO": "Thermo Fisher Scientific Inc.",
        "CSCO": "Cisco Systems, Inc.",
        "QCOM": "QUALCOMM Incorporated",
        "WFC": "Wells Fargo & Company",
        "ACN": "Accenture plc",
        "INTC": "Intel Corporation",
        "LIN": "Linde plc",
        "ABV": "AbbVie Inc.",
        "MCD": "McDonald's Corporation",
        "GE": "General Electric Company",
        "DIS": "The Walt Disney Company",
        "CMCSA": "Comcast Corporation",
        "VZ": "Verizon Communications Inc.",
        "INTU": "Intuit Inc.",
        "NOW": "ServiceNow, Inc.",
        "TXN": "Texas Instruments Incorporated",
        "AMAT": "Applied Materials, Inc.",
        "BKNG": "Booking Holdings Inc.",
        "AXP": "American Express Company"
    }
    return list(ticker_nomi.keys()), ticker_nomi

def monitora_mercato():
    stato_mercato = get_market_state()
    
    if stato_mercato == "CLOSED":
        tz_ny = zoneinfo.ZoneInfo("America/New_York")
        ora_ny = datetime.datetime.now(tz_ny).strftime("%H:%M")
        print(f"Scansione saltata. Il mercato USA (incluso Pre-market) è CHIUSO. Orario attuale NY: {ora_ny}")
        return

    print(f"Rilevata sessione: {stato_mercato}. Avvio scansione...")
    tickers, ticker_nomi = ottieni_componenti_locali()

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

    print(f"Download dati per {len(tickers)} mega-cap...")
    dati_mercato = yf.download(
        tickers, 
        period="2d", 
        group_by="ticker", 
        threads=True, 
        progress=False, 
        prepost=True,
        session=session  
    )

    if dati_mercato.empty:
        print("ERRORE: Yahoo Finance ha restituito un DataFrame vuoto.")
        return

    all_data = []
    # Gestione compatibile sia per ticker singoli che per multi-index
    colonne_disponibili = dati_mercato.columns.levels[0] if isinstance(dati_mercato.columns, pd.MultiIndex) else [dati_mercato.columns[0]]

    for t in tickers:
        try:
            if t not in colonne_disponibili:
                continue
                
            ticker_data = dati_mercato[t]
            if len(ticker_data) >= 2:
                prezzo_ieri = ticker_data["Close"].iloc[-2]
                prezzo_attuale = ticker_data["Close"].iloc[-1] 
                
                if pd.isna(prezzo_ieri) or pd.isna(prezzo_attuale) or prezzo_ieri == 0:
                    continue
                    
                variazione = ((prezzo_attuale - prezzo_ieri) / prezzo_ieri) * 100

                all_data.append({
                    "ticker": t,
                    "nome": ticker_nomi.get(t, t),
                    "variazione": variazione,
                    "prezzo": prezzo_attuale,
                })
        except Exception as e:
            continue

    df_risultati = pd.DataFrame(all_data)
    if df_risultati.empty:
        print("Nessun dato valido estratto dai ticker.")
        return

    df_filtrato = df_risultati[df_risultati["variazione"] <= SOGLIA_PERDITA]

    if df_filtrato.empty:
        print(f"Nessun titolo perde più del {abs(SOGLIA_PERDITA)}%. Invio notifica di vuoto...")
        invia_report_vuoto(stato_mercato)
        return

    titoli_da_controllare = df_filtrato["ticker"].tolist()
    mcap_list = []
    for t in titoli_da_controllare:
        try:
            ticker_info = yf.Ticker(t, session=session)
            mcap = ticker_info.info.get("marketCap", 0)
        except Exception:
            mcap = 0
        mcap_list.append(mcap)

    df_filtrato = df_filtrato.copy()
    df_filtrato["market_cap"] = mcap_list

    df_final = df_filtrato.sort_values(by=["market_cap", "variazione"], ascending=[False, True])
    invia_report_telegram(df_final, stato_mercato)

def formatta_market_cap(valore):
    if valore >= 1e12: return f"${valore / 1e12:.1f}T"
    elif valore >= 1e9: return f"${valore / 1e9:.1f}B"
    elif valore >= 1e6: return f"${valore / 1e6:.1f}M"
    return "N/D"

def invia_report_vuoto(stato_mercato):
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    orario = datetime.datetime.now(tz_ny).strftime("%H:%M")
    tipo_alert = "PRE-MARKET" if stato_mercato == "PRE_MARKET" else "MARKET"
    
    messaggio = f"🚨 *{tipo_alert} MONITOR ({orario} NY)* 🚨\n"
    messaggio += f"Filtro: Top 50 S&P 500 in calo oltre il {abs(SOGLIA_PERDITA)}%\n"
    messaggio += "___________________________________\n\n"
    messaggio += "ℹ️ *Nessun titolo identificato*\n"
    
    invia_a_telegram(messaggio)

def invia_report_telegram(df, stato_mercato):
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    orario = datetime.datetime.now(tz_ny).strftime("%H:%M")
    tipo_alert = "PRE-MARKET DUMP" if stato_mercato == "PRE_MARKET" else "MARKET DUMP"
    
    messaggio = f"🚨 *{tipo_alert} ALERT ({orario} NY)* 🚨\n"
    messaggio += f"Titoli in calo oltre il {abs(SOGLIA_PERDITA)}% ordinati per Market Cap:\n"
    messaggio += "___________________________________\n\n"

    for _, row in df.iterrows():
        cap_formattata = formatta_market_cap(row["market_cap"])
        messaggio += f"🔹 *{row['ticker']}* | {row['nome']}\n"
        messaggio += f"📉 *Variazione:* `{row['variazione']:.2f}%`\n"
        messaggio += f"💵 *Prezzo attuale:* `${row['prezzo']:.2f}`\n"
        messaggio += f"🏢 *Market Cap:* `{cap_formattata}`\n"
        messaggio += "-----------------------------------\n"

    invia_a_telegram(messaggio)

def invia_a_telegram(testo):
    url = f"https://telegram.org{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID_TELEGRAM, "text": testo, "parse_mode": "Markdown"}
    res = requests.post(url, json=payload)
    if res.status_code != 200:
        print(f"ERRORE TELEGRAM: {res.status_code} - {res.text}")
    else:
        print("Messaggio inviato correttamente su Telegram.")

if __name__ == "__main__":
    monitora_mercato()
