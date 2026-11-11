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
    tables = pd.read_html(url)
    df = tables[0]
    ticker_nomi = dict(zip(df["Symbol"], df["Security"]))
    tickers = [t.replace(".", "-") for t in df["Symbol"].tolist()]
    return tickers, ticker_nomi

def monitora_mercato():
    stato_mercato = get_market_state()
    
    if stato_mercato == "CLOSED":
        print("Scansione saltata. Il mercato USA (incluso Pre-market) è CHIUSO.")
        return

    print(f"Rilevata sessione: {stato_mercato}. Avvio scansione...")
    tickers, ticker_nomi = ottieni_componenti_sp500()

    # NOTA: prepost=True permette di scaricare le quotazioni del pre-market e dell'after-hours
    dati_mercato = yf.download(tickers, period="2d", group_by="ticker", threads=True, progress=False, prepost=True)

    all_data = []
    for t in tickers:
        try:
            ticker_data = dati_mercato[t]
            if len(ticker_data) >= 2:
                prezzo_ieri = ticker_data["Close"].iloc[-2]
                
                # Se siamo in pre-market prendiamo l'ultimissimo prezzo disponibile (Open/Close instabili)
                # yfinance popola l'ultima riga con i dati pre-market se prepost=True
                prezzo_attuale = ticker_data["Close"].iloc[-1] 
                
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
    df_filtrato = df_risultati[df_risultati["variazione"] <= SOGLIA_PERDITA]

    if df_filtrato.empty:
        print("Nessun titolo supera la soglia di perdita.")
        return

    # Ottieni capitalizzazione per i titoli filtrati
    titoli_da_controllare = df_filtrato["ticker"].tolist()
    tickers_info = yf.Tickers(" ".join(titoli_da_controllare))

    mcap_list = []
    for t in titoli_da_controllare:
        try:
            mcap = tickers_info.tickers[t].info.get("marketCap", 0)
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
    return "N/D"

def invia_report_telegram(df, stato_mercato):
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    orario = datetime.datetime.now(tz_ny).strftime("%H:%M")
    
    # Cambia il titolo in base al momento della giornata
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

    url = f"https://telegram.org{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID_TELEGRAM, "text": messaggio, "parse_mode": "Markdown"}
    requests.post(url, json=payload)
    print("Report inviato con successo su Telegram.")

if __name__ == "__main__":
    monitora_mercato()
