"""Definiert das Anlageuniversum fuer den Don Elias Aktien Agenten.

Alle Kurse kommen von Yahoo Finance, deshalb tragen alle Werte Yahoo Symbole:
  US Aktien und ETFs   schlichtes Kuerzel, Punkte werden zu Bindestrichen
  Deutsche Aktien      Kuerzel mit Endung .DE
  Indizes              mit vorangestelltem Dach, etwa ^GSPC
  Rohstoffe            Futures mit Endung =F, etwa GC=F fuer Gold
  Devisen              Endung =X
  Krypto               Kuerzel plus -USD, etwa BTC-USD
"""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Asset:
    key: str            # eindeutiger Schluessel im Datensatz
    source: str         # "yahoo"
    query: str          # Symbol bei Yahoo
    name: str
    asset_class: str    # aktie_us | aktie_de | etf | rohstoff | index | fx | krypto
    investable: bool = True

    def as_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# ETFs, Rohstoffe, Indizes, Devisen
# ---------------------------------------------------------------------------

_ETFS = {
    "SPY": "SPDR S&P 500 ETF", "QQQ": "Invesco QQQ Nasdaq 100",
    "DIA": "SPDR Dow Jones", "IWM": "iShares Russell 2000",
    "VTI": "Vanguard Total Stock Market", "VOO": "Vanguard S&P 500",
    "EFA": "iShares MSCI EAFE", "EEM": "iShares MSCI Emerging Markets",
    "VGK": "Vanguard FTSE Europe", "EWJ": "iShares MSCI Japan",
    "EWG": "iShares MSCI Germany", "INDA": "iShares MSCI India",
    "MCHI": "iShares MSCI China", "ACWI": "iShares MSCI ACWI",
    "GLD": "SPDR Gold Shares", "SLV": "iShares Silver Trust",
    "GDX": "VanEck Gold Miners", "USO": "United States Oil Fund",
    "DBC": "Invesco DB Commodity", "PDBC": "Invesco Optimum Yield Commodity",
    "TLT": "iShares 20+ Year Treasury", "IEF": "iShares 7-10 Year Treasury",
    "SHY": "iShares 1-3 Year Treasury", "AGG": "iShares Core US Aggregate Bond",
    "BND": "Vanguard Total Bond Market", "LQD": "iShares Investment Grade Corp",
    "HYG": "iShares High Yield Corp", "TIP": "iShares TIPS Bond",
    "XLE": "Energy Select Sector", "XLF": "Financial Select Sector",
    "XLK": "Technology Select Sector", "XLV": "Health Care Select Sector",
    "XLY": "Consumer Discretionary Select", "XLP": "Consumer Staples Select",
    "XLI": "Industrial Select Sector", "XLU": "Utilities Select Sector",
    "XLB": "Materials Select Sector", "XLRE": "Real Estate Select Sector",
    "XLC": "Communication Services Select",
    "SMH": "VanEck Semiconductor", "SOXX": "iShares Semiconductor",
    "ARKK": "ARK Innovation", "IBIT": "iShares Bitcoin Trust",
    "VNQ": "Vanguard Real Estate", "SCHD": "Schwab US Dividend Equity",
    "VIG": "Vanguard Dividend Appreciation", "VYM": "Vanguard High Dividend",
    "IJR": "iShares Core S&P Small Cap", "MDY": "SPDR S&P Midcap 400",
    "USMV": "iShares MSCI Min Volatility", "MTUM": "iShares MSCI USA Momentum",
    "QUAL": "iShares MSCI USA Quality", "VLUE": "iShares MSCI USA Value",
}

_ROHSTOFFE = {
    "GC=F": "Gold Future", "SI=F": "Silber Future",
    "PL=F": "Platin Future", "PA=F": "Palladium Future",
    "CL=F": "Rohoel WTI Future", "BZ=F": "Rohoel Brent Future",
    "NG=F": "Erdgas Future", "HG=F": "Kupfer Future",
    "ZC=F": "Mais Future", "ZW=F": "Weizen Future",
}

_INDIZES = {
    "^GSPC": "S&P 500", "^NDX": "Nasdaq 100", "^DJI": "Dow Jones",
    "^GDAXI": "DAX", "^STOXX50E": "Euro Stoxx 50", "^N225": "Nikkei 225",
    "^VIX": "VIX Volatilitaetsindex", "^TNX": "US Rendite 10 Jahre",
}

_FX = {
    "EURUSD=X": "EUR/USD", "JPY=X": "USD/JPY", "DX-Y.NYB": "US Dollar Index",
}

# ---------------------------------------------------------------------------
# DAX 40, Yahoo Symbole mit Endung .DE
# ---------------------------------------------------------------------------

_DAX = {
    "ADS.DE": "Adidas", "AIR.DE": "Airbus", "ALV.DE": "Allianz",
    "BAS.DE": "BASF", "BAYN.DE": "Bayer", "BEI.DE": "Beiersdorf",
    "BMW.DE": "BMW", "BNR.DE": "Brenntag", "CBK.DE": "Commerzbank",
    "CON.DE": "Continental", "1COV.DE": "Covestro", "DB1.DE": "Deutsche Boerse",
    "DBK.DE": "Deutsche Bank", "DHL.DE": "DHL Group", "DTE.DE": "Deutsche Telekom",
    "DTG.DE": "Daimler Truck", "ENR.DE": "Siemens Energy", "EOAN.DE": "E.ON",
    "FME.DE": "Fresenius Medical Care", "FRE.DE": "Fresenius",
    "HEI.DE": "Heidelberg Materials", "HEN3.DE": "Henkel", "HNR1.DE": "Hannover Rueck",
    "IFX.DE": "Infineon", "MBG.DE": "Mercedes Benz", "MRK.DE": "Merck",
    "MTX.DE": "MTU Aero Engines", "MUV2.DE": "Muenchener Rueck",
    "P911.DE": "Porsche AG", "PAH3.DE": "Porsche Holding", "QIA.DE": "Qiagen",
    "RHM.DE": "Rheinmetall", "RWE.DE": "RWE", "SAP.DE": "SAP",
    "SHL.DE": "Siemens Healthineers", "SIE.DE": "Siemens",
    "SRT3.DE": "Sartorius", "SY1.DE": "Symrise", "VNA.DE": "Vonovia",
    "VOW3.DE": "Volkswagen", "ZAL.DE": "Zalando",
}

# ---------------------------------------------------------------------------
# US Aktien, Liste wird zur Laufzeit geladen, feste Liste als Rueckfallebene
# ---------------------------------------------------------------------------

_SP500_CSV = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
    "main/data/constituents.csv"
)

_US_FALLBACK = [
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "BRK.B",
    "LLY", "JPM", "V", "XOM", "UNH", "MA", "COST", "HD", "PG", "JNJ", "WMT",
    "NFLX", "CRM", "BAC", "ORCL", "AMD", "CVX", "KO", "PEP", "ADBE", "MRK",
    "TMO", "LIN", "ACN", "MCD", "CSCO", "ABT", "PM", "IBM", "GE", "TXN",
    "QCOM", "INTU", "CAT", "DIS", "VZ", "ISRG", "NOW", "AMGN", "SPGI", "CMCSA",
    "PFE", "AXP", "UBER", "RTX", "GS", "BKNG", "AMAT", "NEE", "T", "LOW",
    "PGR", "TJX", "HON", "ETN", "BLK", "SYK", "MS", "C", "VRTX", "LMT",
    "BSX", "MDT", "PANW", "ADI", "REGN", "MU", "CB", "PLD", "MMC", "SBUX",
    "ADP", "KLAC", "LRCX", "BX", "CI", "DE", "SO", "GILD", "MDLZ", "INTC",
    "PLTR", "SHOP", "COIN", "MSTR", "ABNB", "SNOW", "CRWD", "DDOG", "MRNA",
    "SMCI", "ARM", "DELL", "WDC", "MRVL", "ON", "ANET", "FTNT", "ZS", "NET",
]


def _yahoo_us(ticker: str) -> str:
    """AAPL bleibt AAPL, BRK.B wird BRK-B."""
    return ticker.strip().upper().replace(".", "-")


def load_us_tickers(session=None, limit: int | None = None) -> list[str]:
    """Holt die aktuellen S&P 500 Mitglieder, faellt auf die feste Liste zurueck."""
    tickers: list[str] = []
    try:
        import io
        import csv as _csv
        import requests
        sess = session or requests.Session()
        raw = sess.get(_SP500_CSV, timeout=30).text
        rows = list(_csv.DictReader(io.StringIO(raw)))
        tickers = [r["Symbol"] for r in rows if r.get("Symbol")]
    except Exception:
        tickers = []
    merged = list(dict.fromkeys(tickers + _US_FALLBACK))
    if limit:
        merged = merged[:limit]
    return merged


# Krypto
CRYPTO_TOP_N = 40

STABLECOINS = {
    "tether", "usd-coin", "dai", "first-digital-usd", "true-usd",
    "binance-usd", "paypal-usd", "usds", "ethena-usde", "usdd", "frax",
    "blackrock-usd-institutional-digital-liquidity-fund", "usual-usd",
}

# Coins, die es bei Yahoo nicht unter Kuerzel-USD gibt, werden nach dem
# ersten Lauf hier ausgeschlossen. Die Fehlerliste des Reports zeigt sie an.
CRYPTO_SKIP = {"STETH", "WSTETH", "WBETH", "WEETH", "WBTC", "LEO", "CBBTC"}


def crypto_symbol(coin_symbol: str) -> str:
    return f"{coin_symbol.strip().upper()}-USD"


def build_universe(us_tickers: list[str]) -> list[Asset]:
    """Baut das komplette Universum ohne Krypto, das kommt zur Laufzeit dazu."""
    assets: list[Asset] = []
    for t in us_tickers:
        sym = _yahoo_us(t)
        assets.append(Asset(sym, "yahoo", sym, t, "aktie_us"))
    for sym, name in _DAX.items():
        assets.append(Asset(sym, "yahoo", sym, name, "aktie_de"))
    for sym, name in _ETFS.items():
        assets.append(Asset(sym, "yahoo", sym, name, "etf"))
    for sym, name in _ROHSTOFFE.items():
        assets.append(Asset(sym, "yahoo", sym, name, "rohstoff"))
    for sym, name in _FX.items():
        assets.append(Asset(sym, "yahoo", sym, name, "fx", investable=False))
    for sym, name in _INDIZES.items():
        assets.append(Asset(sym, "yahoo", sym, name, "index", investable=False))
    return assets


# Alter Name, damit bestehende Aufrufe nicht brechen
build_stooq_universe = build_universe
