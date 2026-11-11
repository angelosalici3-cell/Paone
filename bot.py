import os
import datetime
import zoneinfo
import pandas as pd
import requests
from yahooquery import Ticker

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
    """Restituisce i principali colossi dello S&P 500 salvati localmente."""
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
        "ABBV": "AbbVie Inc.",
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
        print(f"Scansione saltata. Il mercato USA è CHIUSO. Orario attuale NY: {ora_ny}")
        return

    print(f"Rilevata sessione: {stato_mercato}. Avvio scansione con YahooQuery...")
    tickers_list, ticker_nomi = ottieni_componenti_locali()

    t = Ticker(tickers_list, asynchronous=True)
    
    try:
        quotes = t.quotes
    except Exception as e:
        print(f"ERRORE nel recupero dati dalle API: {e}")
        return

    if not quotes or len(quotes) == 0:
        print("ERRORE: Risposta vuota dalle API dei prezzi.")
        return

    all_data = []
    for ticker in tickers_list:
        data_ticker = quotes.get(ticker)
        if isinstance(data_ticker, dict):
            try:
                if stato_mercato == "PRE_MARKET":
                    variazione = data_ticker.get("preMarketChangePercent", data_ticker.get("regularMarketChangePercent", 0))
                    prezzo = data_ticker.get("preMarketPrice", data_ticker.get("regularMarketPrice", 0))
                else:
                    variazione = data_ticker.get("regularMarketChangePercent", 0)
                    prezzo = data_ticker.get("regularMarketPrice", 0)

                if variazione is None or prezzo is None:
                    continue

                all_data.append({
                    "ticker": ticker,
                    "nome": ticker_nomi.get(ticker, ticker),
                    "variazione": variazione,
                    "prezzo": prezzo,
                    "market_cap": data_ticker.get("marketCap", 0)
                })
            except Exception:
                continue

    df_risultati = pd.DataFrame(all_data)
    if df_risultati.empty:
        print("Nessun dato utile estratto dai titoli.")
        return

    df_filtrato = df_risultati[df_risultati["variazione"] <= SOGLIA_PERDITA]

    if df_filtrato.empty:
        print(f"Nessun titolo perde più del {abs(SOGLIA_PERDITA)}%. Invio notifica di vuoto...")
        invia_report_vuoto(stato_mercato)
        return

    df_final = df_filtrato.sort_values(by=["market_cap", "variazione"], ascending=[False, True])
    invia_report_telegram(df_final, stato_mercato)

def formatta_market_cap(valore):
    if not valore: return "N/D"
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
    """Funzione con pulizia automatica delle stringhe di configurazione."""
    # Rimuove in modo forzato asterischi, spazi o virgolette residue dai segreti
    token_pulito = str(TOKEN_TELEGRAM).replace("*", "").replace(" ", "").strip()
    chat_id_pulito = str(CHAT_ID_TELEGRAM).replace("*", "").replace(" ", "").strip()
    
    url = f"https://telegram.org{token_pulito}/sendMessage"
    payload = {"chat_id": chat_id_pulito, "text": testo, "parse_mode": "Markdown"}
    
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 200:
            print(f"ERRORE TELEGRAM API: {res.status_code} - {res.text}")
        else:
            print("Messaggio inviato correttamente su Telegram.")
    except Exception as e:
        print(f"Errore di connessione durante l'invio a Telegram: {e}")

if __name__ == "__main__":
    monitora_mercato()
