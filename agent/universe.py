"""Definiert das Anlageuniversum fuer den Don Elias Aktien Agenten.

Quellen der Symbole:
  Aktien und ETFs: stooq.com (kostenlose Tages CSV, kein API Key)
  Krypto:          api.coingecko.com (Demo Tier, kein API Key noetig)

Jedes Symbol traegt eine Assetklasse und ein Kennzeichen, ob es investierbar
ist. Indizes werden mitgefuehrt, aber nie als Kaufkandidat geranked.
"""

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Asset:
    key: str            # eindeutiger Schluessel im Datensatz
    source: str         # "stooq" oder "coingecko"
    query: str          # Symbol bzw. ID an der Quelle
    name: str
    asset_class: str    # aktie_us | aktie_de | etf | rohstoff | index | fx | krypto
    investable: bool = True

    def as_dict(self):
        return asdict(self)


# ---------------------------------------------------------------------------
# ETFs, Rohstoffe, Indizes, FX  (stooq)
# ---------------------------------------------------------------------------

_ETFS = {
    "spy": "SPDR S&P 500 ETF", "qqq": "Invesco QQQ Nasdaq 100",
    "dia": "SPDR Dow Jones", "iwm": "iShares Russell 2000",
    "vti": "Vanguard Total Stock Market", "voo": "Vanguard S&P 500",
    "efa": "iShares MSCI EAFE", "eem": "iShares MSCI Emerging Markets",
    "vgk": "Vanguard FTSE Europe", "ewj": "iShares MSCI Japan",
    "ewg": "iShares MSCI Germany", "inda": "iShares MSCI India",
    "mchi": "iShares MSCI China", "acwi": "iShares MSCI ACWI",
    "gld": "SPDR Gold Shares", "slv": "iShares Silver Trust",
    "gdx": "VanEck Gold Miners", "uso": "United States Oil Fund",
    "dbc": "Invesco DB Commodity", "pdbc": "Invesco Optimum Yield Commodity",
    "tlt": "iShares 20+ Year Treasury", "ief": "iShares 7-10 Year Treasury",
    "shy": "iShares 1-3 Year Treasury", "agg": "iShares Core US Aggregate Bond",
    "bnd": "Vanguard Total Bond Market", "lqd": "iShares Investment Grade Corp",
    "hyg": "iShares High Yield Corp", "tip": "iShares TIPS Bond",
    "xle": "Energy Select Sector", "xlf": "Financial Select Sector",
    "xlk": "Technology Select Sector", "xlv": "Health Care Select Sector",
    "xly": "Consumer Discretionary Select", "xlp": "Consumer Staples Select",
    "xli": "Industrial Select Sector", "xlu": "Utilities Select Sector",
    "xlb": "Materials Select Sector", "xlre": "Real Estate Select Sector",
    "xlc": "Communication Services Select",
    "smh": "VanEck Semiconductor", "soxx": "iShares Semiconductor",
    "arkk": "ARK Innovation", "ibit": "iShares Bitcoin Trust",
    "vnq": "Vanguard Real Estate", "schd": "Schwab US Dividend Equity",
    "vig": "Vanguard Dividend Appreciation", "vym": "Vanguard High Dividend",
    "ijr": "iShares Core S&P Small Cap", "mdy": "SPDR S&P Midcap 400",
    "efav": "iShares MSCI Min Volatility", "mtum": "iShares MSCI USA Momentum",
    "qual": "iShares MSCI USA Quality", "vlue": "iShares MSCI USA Value",
}

_ROHSTOFFE = {
    "xauusd": "Gold Spot USD", "xagusd": "Silber Spot USD",
    "xptusd": "Platin Spot USD", "xpdusd": "Palladium Spot USD",
    "cl.f": "Rohoel WTI Future", "ng.f": "Erdgas Future",
    "hg.f": "Kupfer Future",
}

_INDIZES = {
    "^spx": "S&P 500", "^ndq": "Nasdaq 100", "^dji": "Dow Jones",
    "^dax": "DAX", "^sx5e": "Euro Stoxx 50", "^nkx": "Nikkei 225",
    "^vix": "VIX Volatilitaetsindex",
}

_FX = {
    "eurusd": "EUR/USD", "usdjpy": "USD/JPY", "dx.f": "US Dollar Index Future",
}

# ---------------------------------------------------------------------------
# Deutsche Aktien (DAX 40) bei stooq mit Suffix .de
# ---------------------------------------------------------------------------

_DAX = [
    "ads", "air", "alv", "bas", "bayn", "bei", "bmw", "bnr", "cbk", "con",
    "1cov", "db1", "dbk", "dhl", "dte", "dtg", "enr", "eoan", "fme", "fre",
    "hei", "hen3", "hnr1", "ifx", "mbg", "mrk", "mtx", "muv2", "p911", "pah3",
    "qia", "rhm", "rwe", "sap", "shl", "sie", "srt3", "sy1", "vna", "vow3",
    "zal",
]

# ---------------------------------------------------------------------------
# US Aktien: Liste wird zur Laufzeit geladen, Fallback ist fest verdrahtet
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


def _stooq_us(ticker: str) -> str:
    """AAPL -> aapl.us, BRK.B -> brk-b.us"""
    return ticker.strip().lower().replace(".", "-") + ".us"


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
    # Fallback und Ergaenzung um Werte ausserhalb des S&P 500
    merged = list(dict.fromkeys(tickers + _US_FALLBACK))
    if limit:
        merged = merged[:limit]
    return merged


# Krypto: Anzahl der Top Coins nach Marktkapitalisierung
CRYPTO_TOP_N = 40

# Coins, die als Stablecoin gelten und aus dem Ranking fliegen
STABLECOINS = {
    "tether", "usd-coin", "dai", "first-digital-usd", "true-usd",
    "binance-usd", "paypal-usd", "usds", "ethena-usde", "usdd", "frax",
}


def build_stooq_universe(us_tickers: list[str]) -> list[Asset]:
    assets: list[Asset] = []
    for t in us_tickers:
        assets.append(Asset(_stooq_us(t), "stooq", _stooq_us(t), t, "aktie_us"))
    for t in _DAX:
        assets.append(Asset(f"{t}.de", "stooq", f"{t}.de", t.upper(), "aktie_de"))
    for sym, name in _ETFS.items():
        assets.append(Asset(_stooq_us(sym), "stooq", _stooq_us(sym), name, "etf"))
    for sym, name in _ROHSTOFFE.items():
        assets.append(Asset(sym, "stooq", sym, name, "rohstoff"))
    for sym, name in _FX.items():
        assets.append(Asset(sym, "stooq", sym, name, "fx", investable=False))
    for sym, name in _INDIZES.items():
        assets.append(Asset(sym, "stooq", sym, name, "index", investable=False))
    return assets
