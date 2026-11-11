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
    """Rileva lo stato del mercato di New York (NYSE/NASDAQ)."""
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    ora_ny = datetime.datetime.now(tz_ny)

    if ora_ny.weekday() >= 5:
        return "CLOSED"

    ora_corrente = ora_ny.time()
    
    inizio_pre = datetime.time(4, 0, 0)
    apertura_reg = datetime.time(9, 30, 0)
    chiusura_reg = datetime.time(16, 0, 0)

    if inizio_pre <= ora_corrente < apertura_reg:
        return "PRE_MARKET"
    
    if apertura_reg <= ora_corrente <= chiusura_reg:
        return "REGULAR"
    
    return "CLOSED"

def ottieni_tutti_componenti():
    """Dizionario combinato di S&P 500 e Nasdaq-100."""
    sp500 = {
        "MMM": "3M Company", "AOS": "A.O. Smith Corporation", "ABT": "Abbott Laboratories", "ABBV": "AbbVie Inc.",
        "ACN": "Accenture plc", "ADBE": "Adobe Inc.", "AMD": "Advanced Micro Devices, Inc.", "AES": "AES Corporation",
        "AFL": "Aflac Incorporated", "A": "Agilent Technologies, Inc.", "APD": "Air Products and Chemicals, Inc.",
        "AKAM": "Akamai Technologies, Inc.", "ALB": "Albemarle Corporation", "ARE": "Alexandria Real Estate Equities, Inc.",
        "ALGN": "Align Technology, Inc.", "ALLE": "Allegion plc", "LNT": "Alliant Energy Corporation",
        "ALL": "Allstate Corporation", "GOOGL": "Alphabet Inc. (Class A)", "GOOG": "Alphabet Inc. (Class C)",
        "MO": "Altria Group, Inc.", "AMZN": "Amazon.com, Inc.", "AMCR": "Amcor plc", "AEE": "Ameren Corporation",
        "AAL": "American Airlines Group Inc.", "AEP": "American Electric Power Company, Inc.", "AXP": "American Express Company",
        "AIG": "American International Group, Inc.", "AMT": "American Tower Corporation", "AWK": "American Water Works Company, Inc.",
        "AMP": "Ameriprise Financial, Inc.", "AME": "AMETEK, Inc.", "AMGN": "Amgen Inc.", "APH": "Amphenol Corporation",
        "ADI": "Analog Devices, Inc.", "ANSS": "Ansys, Inc.", "AON": "Aon plc", "APA": "APA Corporation",
        "AAPL": "Apple Inc.", "AMAT": "Applied Materials, Inc.", "APTV": "Aptiv plc", "ACGL": "Arch Capital Group Ltd.",
        "ADM": "Archer-Daniels-Midland Company", "ANET": "Arista Networks, Inc.", "AJG": "Arthur J. Gallagher & Co.",
        "AIZ": "Assurant, Inc.", "T": "AT&T Inc.", "ATO": "Atmos Energy Corporation", "ADSK": "Autodesk, Inc.",
        "AZO": "AutoZone, Inc.", "AVB": "AvalonBay Communities, Inc.", "AVY": "Avery Dennison Corporation",
        "AXON": "Axon Enterprise, Inc.", "BKR": "Baker Hughes Company", "BALL": "Ball Corporation",
        "BAC": "Bank of America Corporation", "BK": "The Bank of New York Mellon Corporation", "BBWI": "Bath & Body Works, Inc.",
        "BAX": "Baxter International Inc.", "BDX": "Becton, Dickinson and Company", "BRK-B": "Berkshire Hathaway Inc.",
        "BBY": "Best Buy Co., Inc.", "BIO": "Bio-Rad Laboratories, Inc.", "TECH": "Bio-Techne Corporation",
        "BIIB": "Biogen Inc.", "BLK": "BlackRock, Inc.", "BX": "The Blackstone Group Inc.", "BA": "The Boeing Company",
        "BKNG": "Booking Holdings Inc.", "BWA": "BorgWarner Inc.", "BXP": "Boston Properties, Inc.",
        "BSX": "Boston Scientific Corporation", "BMY": "Bristol-Myers Squibb Company", "AVGO": "Broadcom Inc.",
        "BR": "Broadridge Financial Solutions, Inc.", "BRO": "Brown & Brown, Inc.", "BF-B": "Brown-Forman Corporation",
        "BLDR": "Builders FirstSource, Inc.", "BG": "Bunge Global SA", "BCC": "Boise Cascade Co.",
        "CHRW": "C.H. Robinson Worldwide, Inc.", "CDNS": "Cadence Design Systems, Inc.", "CZR": "Caesars Entertainment, Inc.",
        "CPT": "Camden Property Trust", "CPB": "Campbell Soup Company", "COF": "Capital One Financial Corporation",
        "CAH": "Cardinal Health, Inc.", "KMX": "CarMax, Inc.", "CCL": "Carnival Corporation", "CARR": "Carrier Global Corporation",
        "CTLT": "Catalent, Inc.", "CAT": "Caterpillar Inc.", "CBOE": "Cboe Global Markets, Inc.", "CBRE": "CBRE Group, Inc.",
        "CDW": "CDW Corporation", "CE": "Celanese Corporation", "COR": "Cencora, Inc.", "CNC": "Centene Corporation",
        "CNP": "CenterPoint Energy, Inc.", "CF": "CF Industries Holdings, Inc.", "CHTR": "Charter Communications, Inc.",
        "CVX": "Chevron Corporation", "CMG": "Chipotle Mexican Grill, Inc.", "CB": "Chubb Limited",
        "CHD": "Church & Dwight Co., Inc.", "CI": "Cigna Group", "CINF": "Cincinnati Financial Corporation",
        "CTAS": "Cintas Corporation", "CSCO": "Cisco Systems, Inc.", "C": "Citigroup Inc.", "CFG": "Citizens Financial Group, Inc.",
        "CLX": "The Clorox Company", "CME": "CME Group Inc.", "CMS": "CMS Energy Corporation", "KO": "The Coca-Cola Company",
        "CTSH": "Cognizant Technology Solutions Corporation", "CL": "Colgate-Palmolive Company", "CMCSA": "Comcast Corporation",
        "CMA": "Comerica Incorporated", "CAG": "Conagra Brands, Inc.", "COP": "ConocoPhillips", "ED": "Consolidated Edison, Inc.",
        "STZ": "Constellation Brands, Inc.", "CEG": "Constellation Energy Corporation", "COO": "The Cooper Companies, Inc.",
        "CPRT": "Copart, Inc.", "GLW": "Corning Incorporated", "CPAY": "Corpay, Inc.", "CTVA": "Corteva, Inc.",
        "CSGP": "CoStar Group, Inc.", "COST": "Costco Wholesale Corporation", "CCI": "Crown Castle Inc.",
        "CSX": "CSX Corporation", "CMI": "Cummins Inc.", "CVS": "CVS Health Corporation", "DHR": "Danaher Corporation",
        "DRI": "Darden Restaurants, Inc.", "DVA": "DaVita Inc.", "DAY": "Dayforce Inc.", "DE": "Deere & Company",
        "DAL": "Delta Air Lines, Inc.", "XRAY": "Dentsply Sirona Inc.", "DVN": "Devon Energy Corporation", "DXCM": "DexCom, Inc.",
        "FANG": "Diamondback Energy, Inc.", "DLR": "Digital Realty Trust, Inc.", "DFS": "Discover Financial Services",
        "DG": "Dollar General Corporation", "DLTR": "Dollar Tree, Inc.", "D": "Dominion Energy, Inc.",
        "DPZ": "Domino's Pizza, Inc.", "DOV": "Dover Corporation", "DOW": "Dow Inc.", "DHI": "D.R. Horton, Inc.",
        "DTE": "DTE Energy Company", "DUK": "Duke Energy Corporation", "DD": "DuPont de Nemours, Inc.",
        "EMN": "Eastman Chemical Company", "ETN": "Eaton Corporation plc", "EBAY": "eBay Inc.", "ECL": "Ecolab Inc.",
        "EIX": "Edison International", "EW": "Edwards Lifesciences Corporation", "EA": "Electronic Arts Inc.",
        "ELV": "Elevance Health, Inc.", "LLY": "Eli Lilly and Company", "EMR": "Emerson Electric Co.",
        "ENPH": "Enphase Energy, Inc.", "ETR": "Entergy Corporation", "EOG": "EOG Resources, Inc.", "EPAM": "EPAM Systems, Inc.",
        "EQT": "EQT Corporation", "EFX": "Equifax Inc.", "EQIX": "Equinix, Inc.", "EQR": "Equity Residential",
        "ERIE": "Erie Indemnity Company", "ESS": "Essex Property Trust, Inc.", "EL": "The Estée Lauder Companies Inc.",
        "ETSY": "Etsy, Inc.", "EG": "Everest Group, Ltd.", "EVRG": "Evergy, Inc.", "ES": "Eversource Energy",
        "EXC": "Exelon Corporation", "EXPE": "Expedia Group, Inc.", "EXPD": "Expeditors International of Washington, Inc.",
        "EXR": "Extra Space Storage Inc.", "XOM": "Exxon Mobil Corporation", "F5": "F5, Inc.", "FACT": "FactSet Research Systems Inc.",
        "FAIR": "Fair Isaac Corporation", "FAST": "Fastenal Company", "FRT": "Federal Realty Investment Trust",
        "FDX": "FedEx Corporation", "FIS": "Fidelity National Information Services, Inc.", "FITB": "Fifth Third Bancorp",
        "FSLR": "First Solar, Inc.", "FE": "FirstEnergy Corp.", "FI": "Fiserv, Inc.", "FMC": "FMC Corporation",
        "F": "Ford Motor Company", "FTNT": "Fortinet, Inc.", "FTV": "Fortive Corporation", "FOXA": "Fox Corporation (Class A)",
        "FOX": "Fox Corporation (Class B)", "BEN": "Franklin Resources, Inc.", "FCX": "Freeport-McMoRan Inc.",
        "GRMN": "Garmin Ltd.", "IT": "Gartner, Inc.", "GE": "GE Aerospace", "GEV": "GE Vernova Inc.", 
        "GNRC": "Generac Holdings Inc.", "GD": "General Dynamics Corporation", "GIS": "General Mills, Inc.",
        "GM": "General Motors Company", "GPC": "Genuine Parts Company", "GILD": "Gilead Sciences, Inc.",
        "GPN": "Global Payments Inc.", "GL": "Globe Life Inc.", "GWW": "W.W. Grainger, Inc.",
        "HAL": "Halliburton Company", "HIG": "The Hartford Financial Services Group, Inc.", "HAS": "Hasbro, Inc.",
        "HCA": "HCA Healthcare, Inc.", "DOC": "Healthpeak Properties, Inc.", "HSIC": "Henry Schein, Inc.",
        "HSY": "The Hershey Company", "HES": "Hess Corporation", "HPE": "Hewlett Packard Enterprise Company",
        "HLT": "Hilton Worldwide Holdings Inc.", "HOLX": "Hologic, Inc.", "HD": "The Home Depot, Inc.",
        "HON": "Honeywell International Inc.", "HRL": "Hormel Foods Corporation", "HST": "Host Hotels & Resorts, Inc.",
        "HPQ": "HP Inc.", "HUBB": "Hubbell Incorporated", "HUM": "Humana Inc.", "HBAN": "Huntington Bancshares Incorporated",
        "HWM": "Howmet Aerospace Inc.", "IBM": "International Business Machines Corporation", "IEX": "IDEX Corporation",
        "IDXX": "IDEXX Laboratories, Inc.", "ITW": "Illinois Tool Works Inc.", "ILMN": "Illumina, Inc.",
        "INCY": "Incyte Corporation", "IR": "Ingersoll Rand Inc.", "PODD": "Insulet Corporation", "INTC": "Intel Corporation",
        "ICE": "Intercontinental Exchange, Inc.", "IFF": "International Flavors & Fragrances Inc.", "IP": "International Paper Company",
        "IPG": "The Interpublic Group of Companies, Inc.", "INTU": "Intuit Inc.", "ISRG": "Intuitive Surgical, Inc.",
        "IVZ": "Invesco Ltd.", "INVH": "Invitation Homes Inc.", "IQV": "IQVIA Holdings Inc.", "IRM": "Iron Mountain Incorporated",
        "JBHT": "J.B. Hunt Transport Services, Inc.", "JBL": "Jabil Inc.", "JKHY": "Jack Henry & Associates, Inc.",
        "J": "Jacobs Solutions Inc.", "SJM": "The J.M. Smucker Company", "JNJ": "Johnson & Johnson",
        "JCI": "Johnson Controls International plc", "JPM": "JPMorgan Chase & Co.", "JNPR": "Juniper Networks, Inc.",
        "K": "Kellanova", "KVUE": "Kenvue Inc.", "KEY": "KeyCorp", "KEYS": "Keysight Technologies, Inc.",
        "KMB": "Kimberly-Clark Corporation", "KIM": "Kimco Realty Corporation", "KMI": "Kinder Morgan, Inc.",
        "KLAC": "KLA Corporation", "KHC": "The Kraft Heinz Company", "KR": "The Kroger Co.", "LHX": "L3Harris Technologies, Inc.",
        "LH": "Labcorp Holdings Inc.", "LRCX": "Lam Research Corporation", "LW": "Lamb Weston Holdings, Inc.",
        "LVS": "Las Vegas Sands Corp.", "LDOS": "Leidos Holdings, Inc.", "LEN": "Lennar Corporation",
        "LIN": "Linde plc", "LYV": "Live Nation Entertainment, Inc.", "LKQ": "LKQ Corporation", "LMT": "Lockheed Martin Corporation",
        "L": "Loews Corporation", "LOW": "Lowe's Companies, Inc.", "LULU": "Lululemon Athletica Inc.",
        "LYB": "LyondellBasell Industries N.V.", "MTB": "M&T Bank Corporation", "MRO": "Marathon Oil Corporation",
        "MPC": "Marathon Petroleum Corporation", "MKTX": "MarketAxess Holdings Inc.", "MAR": "Marriott International, Inc.",
        "MMC": "Marsh & McLennan Companies, Inc.", "MLM": "Martin Marietta Materials, Inc.", "MAS": "Masco Corporation",
        "MA": "Mastercard Incorporated", "MTCH": "Match Group, Inc.", "MAT": "Mattel, Inc.", "MKC": "McCormick & Company, Incorporated",
        "MCD": "McDonald's Corporation", "MCK": "McKesson Corporation", "MDT": "Medtronic plc", "MRK": "Merck & Co., Inc.",
        "META": "Meta Platforms, Inc.", "MET": "MetLife, Inc.", "MTD": "Mettler-Toledo International Inc.",
        "MGM": "MGM Resorts International", "MCHP": "Microchip Technology Incorporated", "MU": "Micron Technology, Inc.",
        "MSFT": "Microsoft Corporation", "MAA": "Mid-America Apartment Communities, Inc.", "MRNA": "Moderna, Inc.",
        "MHK": "Mohawk Industries, Inc.", "MOH": "Molina Healthcare, Inc.", "TAP": "Molson Coors Beverage Company",
        "MDLZ": "Mondelez International, Inc.", "MPWR": "Monolithic Power Systems, Inc.", "MNST": "Monster Beverage Corporation",
        "MCO": "Moody's Corporation", "MS": "Morgan Stanley", "MOS": "The Mosaic Company", "MSI": "Motorola Solutions, Inc.",
        "MSCI": "MSCI Inc.", "NDAQ": "Nasdaq, Inc.", "NTAP": "NetApp, Inc.", "NFLX": "Netflix, Inc.", "NEM": "Newmont Corporation",
        "NWSA": "News Corporation (Class A)", "NWS": "News Corporation (Class B)", "NEE": "NextEra Energy, Inc.",
        "NKE": "NIKE, Inc.", "NI": "NiSource Inc.", "NDSN": "Nordson Corporation", "NSC": "Norfolk Southern Corporation",
        "NTRS": "Northern Trust Corporation", "NOC": "Northrop Grumman Corporation", "NCLH": "Norwegian Cruise Line Holdings Ltd.",
        "NRG": "NRG Energy, Inc.", "NUE": "Nucor Corporation", "NVDA": "NVIDIA Corporation", "NVR": "NVR, Inc.",
        "NXPI": "NXP Semiconductors N.V.", "ORLY": "O'Reilly Automotive, Inc.", "OXY": "Occidental Petroleum Corporation",
        "ODFL": "Old Dominion Freight Line, Inc.", "OMC": "Omnicom Group Inc.", "ON": "ON Semiconductor",
        "OKE": "ONEOK, Inc.", "ORCL": "Oracle Corporation", "OTIS": "Otis Worldwide Corporation", "PCAR": "PACCAR Inc.",
        "PKG": "Packaging Corporation of America", "PANW": "Palo Alto Networks, Inc.", "PARA": "Paramount Global",
        "PH": "Parker-Hannifin Corporation", "PAYX": "Paychex, Inc.", "PAYC": "Paycom Software, Inc.", "PYPL": "PayPal Holdings, Inc.",
        "PNR": "Pentair plc", "PEP": "PepsiCo, Inc.", "PFE": "Pfizer Inc.", "PCG": "PG&E Corporation", "PM": "Philip Morris International Inc.",
        "PSX": "Phillips 66", "PNW": "Pinnacle West Capital Corporation", "PGR": "The Progressive Corporation",
        "PLD": "Prologis, Inc.", "PRU": "Prudential Financial, Inc.", "PEG": "Public Service Enterprise Group Incorporated",
        "PTC": "PTC Inc.", "PSA": "Public Storage", "PHM": "PulteGroup, Inc.", "QRVO": "Qorvo, Inc.",
        "QCOM": "QUALCOMM Incorporated", "PWR": "Quanta Services, Inc.", "DGX": "Quest Diagnostics Incorporated",
        "RL": "Ralph Lauren Corporation", "RJF": "Raymond James Financial, Inc.", "RTX": "RTX Corporation",
        "O": "Realty Income Corporation", "REG": "Regency Centers Corporation", "REGN": "Regeneron Pharmaceuticals, Inc.",
        "RF": "Regions Financial Corporation", "RSG": "Republic Services, Inc.", "RMD": "ResMed Inc.",
        "RHI": "Robert Half Inc.", "ROK": "Rockwell Automation, Inc.", "ROL": "Rollins, Inc.",
        "ROP": "Roper Technologies, Inc.", "ROST": "Ross Stores, Inc.", "RCL": "Royal Caribbean Cruises Ltd.",
        "SPGI": "S&P Global Inc.", "CRM": "Salesforce, Inc.", "SBAC": "SBA Communications Corporation",
        "SLB": "Schlumberger Limited", "STX": "Seagate Technology Holdings plc", "SEE": "Sealed Air Corporation",
        "SRE": "Sempra Energy", "NOW": "ServiceNow, Inc.", "SHW": "The Sherwin-Williams Company", "SPG": "Simon Property Group, Inc.",
        "SWKS": "Skyworks Solutions, Inc.", "SNA": "Snap-on Incorporated",
        "SOLV": "Solventum Corp.", "SO": "The Southern Company", "LUV": "Southwest Airlines Co.", "SWK": "Stanley Black & Decker, Inc.",
        "SBUX": "Starbucks Corporation", "STT": "State Street Corporation", "STV": "STMicroelectronics N.V.",
        "STK": "Stryker Corporation", "SMCI": "Super Micro Computer, Inc.", "SYF": "Synchrony Financial",
        "SNPS": "Synopsys, Inc.", "SYY": "Sysco Corporation", "TMUS": "T-Mobile US, Inc.", "TROW": "T. Rowe Price Group, Inc.",
        "TTWO": "Take-Two Interactive Software, Inc.", "TPR": "Tapestry, Inc.", "TRGP": "Targa Resources Corp.",
        "TGT": "Target Corporation", "TEL": "TE Connectivity plc", "FTI": "TechnipFMC plc", "TDY": "Teledyne Technologies Incorporated",
        "TFX": "Teleflex Incorporated", "TER": "Teradyne, Inc.", "TSLA": "Tesla, Inc.", "TXN": "Texas Instruments Incorporated",
        "TXT": "Textron Inc.", "TMO": "Thermo Fisher Scientific Inc.", "TJX": "The TJX Companies, Inc.", "TSCO": "Tractor Supply Company",
        "TT": "Trane Technologies plc", "TDG": "TransDigm Group Incorporated", "TRV": "The Travelers Companies, Inc.",
        "TRMB": "Trimble Inc.", "TFC": "Truist Financial Corporation", "TYL": "Tyler Technologies, Inc.", "TSN": "Tyson Foods, Inc.",
        "USB": "U.S. Bancorp", "UBER": "Uber Technologies, Inc.", "UDR": "UDR, Inc.", "ULTA": "Ulta Beauty, Inc.",
        "UNP": "Union Pacific Corporation", "UAL": "United Airlines Holdings, Inc.", "UPS": "United Parcel Service, Inc.",
        "URI": "United Rentals, Inc.", "UNH": "UnitedHealth Group Incorporated", "VLO": "Valero Energy Corporation",
        "VTR": "Ventas, Inc.", "VRSN": "Verisign, Inc.", "VRSK": "Verisk Analytics, Inc.", "VZ": "Verizon Communications Inc.",
        "VRTX": "Vertex Pharmaceuticals Incorporated", "VFC": "V.F. Corporation", "VTRS": "Viatris Inc.",
        "VICI": "VICI Properties Inc.", "V": "Visa Inc.", "VMC": "Vulcan Materials Company", "WRB": "W.R. Berkley Corporation",
        "WAB": "Westinghouse Air Brake Technologies Corporation", "WMT": "Walmart Inc.", "DIS": "The Walt Disney Company",
        "WBD": "Warner Bros. Discovery, Inc.", "WM": "Waste Management, Inc.", "WAT": "Waters Corporation",
        "WEC": "WEC Energy Group, Inc.", "WFC": "Wells Fargo & Company", "WELL": "Welltower Inc.", "WST": "West Pharmaceutical Services, Inc.",
        "WDC": "Western Digital Corporation", "WY": "Weyerhaeuser Company", "WHR": "Whirlpool Corporation",
        "WMB": "Williams Companies, Inc.", "WTW": "Willis Towers Watson Public Limited Company", "WYNN": "Wynn Resorts, Limited",
        "XEL": "Xcel Energy Inc.", "XYL": "Xylem Inc.", "YUM": "Yum! Brands, Inc.", "ZBRA": "Zebra Technologies Corporation",
        "ZBH": "Zimmer Biomet Holdings, Inc.", "ZTS": "Zoetis Inc."
    }

    nasdaq = {
        "AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "AMZN": "Amazon.com, Inc.",
        "NVDA": "NVIDIA Corporation", "GOOGL": "Alphabet Inc. (Class A)", "GOOG": "Alphabet Inc. (Class C)",
        "META": "Meta Platforms, Inc.", "TSLA": "Tesla, Inc.", "AVGO": "Broadcom Inc.",
        "COST": "Costco Wholesale Corporation", "NFLX": "Netflix, Inc.", "AMD": "Advanced Micro Devices, Inc.",
        "TMUS": "T-Mobile US, Inc.", "LIN": "Linde plc", "INTU": "Intuit Inc.",
        "AMGN": "Amgen Inc.", "QCOM": "QUALCOMM Incorporated", "HON": "Honeywell International Inc.",
        "BKNG": "Booking Holdings Inc.", "ISRG": "Intuitive Surgical, Inc.", "AMAT": "Applied Materials, Inc.",
        "ADI": "Analog Devices, Inc.", "VRTX": "Vertex Pharmaceuticals Incorporated", "SBUX": "Starbucks Corporation",
        "MDLZ": "Mondelez International, Inc.", "GILD": "Gilead Sciences, Inc.", "LRCX": "Lam Research Corporation",
        "PANW": "Palo Alto Networks, Inc.", "ADP": "Automatic Data Processing, Inc.", "MU": "Micron Technology, Inc.",
        "SNPS": "Synopsys, Inc.", "CDNS": "Cadence Design Systems, Inc.", "PYPL": "PayPal Holdings, Inc.",
        "REGN": "Regeneron Pharmaceuticals, Inc.", "CSCO": "Cisco Systems, Inc.", "MAR": "Marriott International, Inc.",
        "MELI": "MercadoLibre, Inc.", "KLAC": "KLA Corporation", "ASML": "ASML Holding N.V.",
        "MNST": "Monster Beverage Corporation", "ORLY": "O'Reilly Automotive, Inc.", "PDD": "PDD Holdings Inc.",
        "ABNB": "Airbnb, Inc.", "CTAS": "Cintas Corporation", "ROP": "Roper Technologies, Inc.",
        "ADSK": "Autodesk, Inc.", "DXCM": "DexCom, Inc.", "PCAR": "PACCAR Inc.",
        "PAYX": "Paychex, Inc.", "LULU": "Lululemon Athletica Inc.", "CPRT": "Copart, Inc.",
        "IDXX": "IDEXX Laboratories, Inc.", "EA": "Electronic Arts Inc.", "KDP": "Keurig Dr Pepper Inc.",
        "EXC": "Exelon Corporation", "XEL": "Xcel Energy Inc.", "MRVL": "Marvell Technology, Inc.",
        "CSX": "CSX Corporation", "ODFL": "Old Dominion Freight Line, Inc.", "FAST": "Fastenal Company",
        "VRSK": "Verisk Analytics, Inc.", "BKR": "Baker Hughes Company", "GEHC": "GE HealthCare Technologies Inc.",
        "ON": "ON Semiconductor", "TTD": "The Trade Desk, Inc.", "ANSS": "Ansys, Inc.",
        "WBD": "Warner Bros. Discovery, Inc.", "CHTR": "Charter Communications, Inc.", "DLTR": "Dollar Tree, Inc.",
        "ENPH": "Enphase Energy, Inc.", "EBAY": "eBay Inc.", "CTSH": "Cognizant Technology Solutions Corporation",
        "MCHP": "Microchip Technology Incorporated", "TEAM": "Atlassian Corporation", "GFS": "GlobalFoundries Inc.",
        "ZS": "Zscaler, Inc.", "ROST": "Ross Stores, Inc.", "BIIB": "Biogen Inc.",
        "DDOG": "Datadog, Inc.", "CDW": "CDW Corporation", "ONB": "Old National Bancorp",
        "TTWO": "Take-Two Interactive Software, Inc.", "ILMN": "Illumina, Inc.", "ALGN": "Align Technology, Inc.",
        "ANET": "Arista Networks, Inc.", "SIRI": "Sirius XM Holdings Inc.", "CCEP": "Coca-Cola Europacific Partners PLC",
        "FANG": "Diamondback Energy, Inc.", "APTV": "Aptiv plc", "CPAY": "Corpay, Inc.",
        "WBA": "Walgreens Boots Alliance, Inc.", "ZBRA": "Zebra Technologies Corporation", "KHC": "The Kraft Heinz Company"
    }

    # Unisce i due dizionari ed etichetta l'indice
    tutti_ticker = {}

    for ticker, nome in sp500.items():
        tutti_ticker[ticker] = {"nome": nome, "indice": "S&P 500"}

    for ticker, nome in nasdaq.items():
        if ticker in tutti_ticker:
            tutti_ticker[ticker]["indice"] = "S&P 500 + NASDAQ"
        else:
            tutti_ticker[ticker] = {"nome": nome, "indice": "NASDAQ-100"}

    return tutti_ticker

def monitora_mercato():
    stato_mercato = get_market_state()
    if stato_mercato == "CLOSED":
        tz_ny = zoneinfo.ZoneInfo("America/New_York")
        ora_ny = datetime.datetime.now(tz_ny).strftime("%H:%M")
        print(f"Scansione saltata. Il mercato USA è CHIUSO. Orario attuale NY: {ora_ny}")
        return
    
    print(f"Rilevata sessione: {stato_mercato}. Avvio scansione asincrona su S&P 500 e Nasdaq-100...")
    mappa_titoli = ottieni_tutti_componenti()
    tickers_list = list(mappa_titoli.keys())
    t = Ticker(tickers_list, asynchronous=True)
    
    try:
        quotes = t.quotes
    except Exception as e:
        print(f"ERRORE nel recupero dati dalle API: {e}")
        return
        
    if not quotes or len(quotes) == 0:
        print("ERRORE: Risposta vuota dalle API.")
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
                    
                info_titolo = mappa_titoli.get(ticker, {"nome": ticker, "indice": "USA"})
                all_data.append({
                    "ticker": ticker,
                    "nome": info_titolo["nome"],
                    "indice": info_titolo["indice"],
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
    if not valore: 
        return "N/D"
    if valore >= 1e12: 
        return f"${valore / 1e12:.1f}T"
    elif valore >= 1e9: 
        return f"${valore / 1e9:.1f}B"
    elif valore >= 1e6: 
        return f"${valore / 1e6:.1f}M"
    return "N/D"

def invia_report_vuoto(stato_mercato):
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    orario = datetime.datetime.now(tz_ny).strftime("%H:%M")
    tipo_alert = "PRE-MARKET" if stato_mercato == "PRE_MARKET" else "MARKET"
    messaggio = f"🚨 USA MARKET {tipo_alert} MONITOR ({orario} NY) 🚨\n"
    messaggio += f"Filtro: Titoli S&P 500 / Nasdaq-100 in calo oltre il {abs(SOGLIA_PERDITA)}%\n"
    messaggio += "___________________________________\n\n"
    messaggio += "ℹ️ Nessun titolo identificato\n"
    invia_a_telegram(messaggio)

def invia_report_telegram(df, stato_mercato):
    tz_ny = zoneinfo.ZoneInfo("America/New_York")
    orario = datetime.datetime.now(tz_ny).strftime("%H:%M")
    tipo_alert = "PRE-MARKET DUMP" if stato_mercato == "PRE_MARKET" else "MARKET DUMP"
    messaggio = f"🚨 US MARKETS {tipo_alert} ALERT ({orario} NY) 🚨\n"
    messaggio += f"Titoli (S&P 500 / Nasdaq) in calo oltre il {abs(SOGLIA_PERDITA)}%:\n"
    messaggio += "___________________________________\n\n"
    for _, row in df.iterrows():
        cap_formattata = formatta_market_cap(row["market_cap"])
        messaggio += f"🔹 {row['ticker']} | {row['nome']} [{row['indice']}]\n"
        messaggio += f"📉 Variazione: {row['variazione']:.2f}%\n"
        messaggio += f"💵 Prezzo attuale: ${row['prezzo']:.2f}\n"
        messaggio += f"🏢 Market Cap: {cap_formattata}\n"
        messaggio += "-----------------------------------\n"
    invia_a_telegram(messaggio)

def invia_a_telegram(testo):
    t_token = str(TOKEN_TELEGRAM).strip()
    c_id = str(CHAT_ID_TELEGRAM).strip()
    parti_url = ["https://", "api.", "telegram", ".org", "/bot", t_token, "/sendMessage"]
    url_completo = "".join(parti_url)
    payload = {"chat_id": c_id, "text": testo, "parse_mode": "HTML"}
    try:
        res = requests.post(url_completo, json=payload)
        if res.status_code != 200:
            print(f"Risposta server Telegram (Errore): {res.status_code} - {res.text}")
        else:
            print("Esecuzione completata correttamente. Messaggio inviato!")
    except Exception as e:
        print(f"Errore di invio: {e}")

if __name__ == "__main__":
    monitora_mercato()
