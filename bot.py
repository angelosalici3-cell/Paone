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
    """Rileva se siamo in sessione Regular o in Pre-Market (Orari NY)."""
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    ora_ny = datetime.datetime.now(tz_ny)

    if ora_ny.weekday() >= 5:
        return "CLOSED"

    ora_corrente = ora_ny.time()
    
    # Pre-Market: dalle 04:00 alle 09:30
    if datetime.time(4, 0) <= ora_corrente < datetime.time(9, 30):
        return "PRE_MARKET"
    # Sessione Normale: dalle 09:30 alle 16:00
    elif datetime.time(9, 30) <= ora_corrente <= datetime.time(16, 0):
        return "REGULAR"
    
    return "CLOSED"

def ottieni_componenti_sp500():
    url = "https://wikipedia.org"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    req = requests.get(url, headers=headers)
    tables = pd.read_html(req.text)
    df = tables
    ticker_nomi = dict(zip(df["Symbol"], df["Security"]))
    tickers = [t.replace(".", "-") for t in df["Symbol"].tolist()]
    return tickers, ticker_nomi

def monitora_mercato():
    stato_mercato = get_market_state()
    
    if stato_mercato == "CLOSED":
        tz_ny = zoneinfo.ZoneInfo("America/New_York")
        ora_ny = datetime.datetime.now(tz_ny).strftime("%H:%M")
        print(f"Scansione saltata. Il mercato USA è CHIUSO. Orario NY: {ora_ny}")
        return

    print(f"Rilevata sessione: {stato_mercato}. Avvio scansione...")
    tickers, ticker_nomi = ottieni_componenti_sp500()

    session = requests.Session()
    session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

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
        print("ERRORE: Yahoo Finance ha restituito un DataFrame vuoto. Probabile blocco IP.")
        return

    all_data = []
    for t in tickers:
        try:
            if t not in dati_mercato.columns.levels:
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
                    "nome": ticker_nomi.get(t.replace("-", "."), t),
                    "variazione": variazione,
                    "prezzo": prezzo_attuale,
                })
        except Exception:
            continue

    df_risultati = pd.DataFrame(all_data)
    if df_risultati.empty:
        print("Nessun dato valido estratto dai ticker.")
        return

    df_filtrato = df_risultati[df_risultati["variazione"] <= SOGLIA_PERDITA]

    # --- NUOVA LOGICA: SE IL DATAFRAME È VUOTO INVIA COMUNQUE IL MESSAGGIO ---
    if df_filtrato.empty:
        print(f"Nessun titolo perde più del {abs(SOGLIA_PERDITA)}%. Invio notifica di vuoto...")
        invia_report_vuoto(stato_mercato)
        return

    # Se ci sono titoli, estrae la market cap e invia il report completo
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
    """Invia un messaggio sintetico quando nessun titolo supera la soglia di perdita."""
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    orario = datetime.datetime.now(tz_ny).strftime("%H:%M")
    tipo_alert = "PRE-MARKET" if stato_mercato == "PRE_MARKET" else "MARKET"
    
    messaggio = f"🚨 *{tipo_alert} MONITOR ({orario} NY)* 🚨\n"
    messaggio += f"Filtro: Titoli S&P 500 in calo oltre il {abs(SOGLIA_PERDITA)}%\n"
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
    """Funzione di invio generica con gestione degli errori nei log di GitHub."""
    url = f"https://telegram.org{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID_TELEGRAM, "text": testo, "parse_mode": "Markdown"}
    res = requests.post(url, json=payload)
    if res.status_code != 200:
        print(f"ERRORE TELEGRAM: {res.status_code} - {res.text}")
    else:
        print("Messaggio inviato correttamente su Telegram.")

if __name__ == "__main__":
    monitora_mercato()
