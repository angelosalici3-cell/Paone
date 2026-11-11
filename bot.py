import os
import datetime
import zoneinfo
import pandas as pd
import requests
import yfinance as yf

# --- CONFIGURAZIONE CON VARIABILI D'AMBIENTE (SICUREZZA) ---
TOKEN_TELEGRAM = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID_TELEGRAM = os.getenv("TELEGRAM_CHAT_ID")
SOGLIA_PERDITA = -5.0  # % di perdita minima per attivare l'alert

def is_market_open():
    """Verifica se il mercato di New York (NYSE) è attualmente aperto."""
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    ora_ny = datetime.datetime.now(tz_ny)

    # Fine settimana (Sabato = 5, Domenica = 6)
    if ora_ny.weekday() >= 5:
        return False

    # Apertura 09:30, Chiusura 16:00
    inizio_mercato = ora_ny.replace(hour=9, minute=30, second=0, microsecond=0)
    fine_mercato = ora_ny.replace(hour=16, minute=0, second=0, microsecond=0)

    return inizio_mercato <= ora_ny <= fine_mercato

def ottieni_componenti_sp500():
    url = "https://wikipedia.org"
    tables = pd.read_html(url)
    df = tables[0]
    ticker_nomi = dict(zip(df["Symbol"], df["Security"]))
    tickers = [t.replace(".", "-") for t in df["Symbol"].tolist()]
    return tickers, ticker_nomi

def monitora_mercato():
    if not is_market_open():
        tz_ny = zoneinfo.ZoneInfo("America/New_York")
        ora_ny = ora_ny = datetime.datetime.now(tz_ny).strftime("%H:%M")
        print(f"Scansione saltata. Il mercato USA è CHIUSO (Orario NY: {ora_ny}).")
        return

    print("Mercato aperto. Avvio scansione...")
    tickers, ticker_nomi = ottieni_componenti_sp500()

    dati_mercato = yf.download(tickers, period="2d", group_by="ticker", threads=True, progress=False)

    all_data = []
    for t in tickers:
        try:
            ticker_data = dati_mercato[t]
            if len(ticker_data) >= 2:
                prezzo_ieri = ticker_data["Close"].iloc[-2]
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
    invia_report_telegram(df_final)

def formatta_market_cap(valore):
    if valore >= 1e12: return f"${valore / 1e12:.1f}T"
    elif valore >= 1e9: return f"${valore / 1e9:.1f}B"
    elif valore >= 1e6: return f"${valore / 1e6:.1f}M"
    return "N/D"

def invia_report_telegram(df):
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    orario = datetime.datetime.now(tz_ny).strftime("%H:%M")
    messaggio = f"🚨 *MARKET DUMP ALERT ({orario} NY)* 🚨\n"
    messaggio += f"Titoli S&P 500 in calo oltre il {abs(SOGLIA_PERDITA)}% ordinati per importanza (Cap. di Mercato):\n"
    messaggio += "‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾‾\n\n"

    for _, row in df.iterrows():
        cap_formattata = formatta_market_cap(row["market_cap"])
        messaggio += f"🔹 *{row['ticker']}* | {row['nome']}\n"
        messaggio += f"📉 *Variazione:* `{row['variazione']:.2f}%`\n"
        messaggio += f"💵 *Prezzo:* `${row['prezzo']:.2f}`\n"
        messaggio += f"🏢 *Market Cap:* `{cap_formattata}`\n"
        messaggio += "-----------------------------------\n"

    url = f"https://telegram.org{TOKEN_TELEGRAM}/sendMessage"
    payload = {"chat_id": CHAT_ID_TELEGRAM, "text": messaggio, "parse_mode": "Markdown"}
    requests.post(url, json=payload)
    print("Report inviato su Telegram.")

if __name__ == "__main__":
    monitora_mercato()
