"""Datenbeschaffung fuer den Don Elias Aktien Agenten.

Kursquelle ist Yahoo Finance. Die Entscheidung ist gemessen, nicht geraten:
stooq beantwortet Anfragen aus Rechenzentren mit einer HTML Sperrseite statt
mit CSV, CoinGecko begrenzt die Historie im Gratistarif auf 365 Tage.
Yahoo liefert Aktien, ETFs, Indizes, Rohstoffe, Devisen und Krypto aus einer
Hand, dividendenbereinigt und mit voller Tageshistorie.

Wichtig: Yahoo ignoriert bei range=max den Tagesabstand und antwortet mit
Monatswerten. Deshalb wird ausschliesslich ueber period1 und period2
abgefragt. Das ist nachgemessen: AAPL liefert so 11520 Tageskurse ab 1980
statt 168 Monatswerten.

CoinGecko wird nur noch fuer die Rangliste der groessten Coins benutzt.
"""

from __future__ import annotations

import json
import os
import random
import time
import datetime as dt
import urllib.parse

import pandas as pd
import requests

YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
CG_URL = "https://api.coingecko.com/api/v3"

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

YAHOO_SLEEP = float(os.getenv("YAHOO_SLEEP", "0.2"))
CG_SLEEP = float(os.getenv("CG_SLEEP", "3.0"))


class FetchError(Exception):
    pass


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
    return s


def _get(session: requests.Session, url: str, params: dict | None = None,
         tries: int = 3) -> str:
    last = None
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, timeout=40)
            if r.status_code == 429:
                raise FetchError("429 Drosselung")
            if r.status_code == 404:
                raise FetchError("404 Symbol unbekannt")
            r.raise_for_status()
            return r.text
        except FetchError as exc:
            if "404" in str(exc):
                raise
            last = exc
            time.sleep((2 ** attempt) + random.random())
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep((2 ** attempt) + random.random())
    raise FetchError(f"{url} fehlgeschlagen: {last}")


# ---------------------------------------------------------------------------
# Yahoo Finance
# ---------------------------------------------------------------------------

def fetch_yahoo(session: requests.Session, symbol: str,
                start: dt.date | None = None) -> pd.DataFrame:
    """Tageskurse. start=None laedt die komplette verfuegbare Historie.

    Rueckgabe: date, open, high, low, close (dividendenbereinigt),
    close_raw (unbereinigt), volume
    """
    period1 = 0 if start is None else int(
        dt.datetime.combine(start, dt.time()).timestamp())
    params = {
        "period1": str(max(period1, 0)),
        "period2": str(int(time.time()) + 86400),
        "interval": "1d",
        "events": "div,split",
        "includeAdjustedClose": "true",
    }
    text = _get(session, YAHOO_URL.format(urllib.parse.quote(symbol)), params)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FetchError(f"Antwort ist kein JSON: {text[:80]}") from exc

    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise FetchError(str(chart["error"])[:120])
    results = chart.get("result") or []
    if not results:
        raise FetchError("leere Antwort")
    res = results[0]
    ts = res.get("timestamp") or []
    if not ts:
        raise FetchError("keine Zeitreihe enthalten")

    quote = (res.get("indicators", {}).get("quote") or [{}])[0]
    adj = (res.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")

    df = pd.DataFrame({
        "date": [pd.Timestamp(dt.datetime.fromtimestamp(t, dt.timezone.utc).date())
                 for t in ts],
        "open": quote.get("open"),
        "high": quote.get("high"),
        "low": quote.get("low"),
        "close_raw": quote.get("close"),
        "volume": quote.get("volume"),
    })
    df["close"] = adj if adj is not None else df["close_raw"]

    # Yahoo liefert einzelne Tage ohne Kurs, etwa Feiertage an Terminboersen.
    df = df.dropna(subset=["close"])
    df = df.drop_duplicates(subset="date", keep="last").sort_values("date")
    time.sleep(YAHOO_SLEEP)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# CoinGecko, nur fuer die Rangliste der groessten Coins
# ---------------------------------------------------------------------------

def fetch_top_coins(session: requests.Session, top_n: int,
                    exclude: set[str]) -> list[dict]:
    """Liefert die groessten Coins nach Marktkapitalisierung."""
    params = {"vs_currency": "usd", "order": "market_cap_desc",
              "per_page": str(min(max(top_n * 2, 10), 250)), "page": "1"}
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    if key:
        params["x_cg_demo_api_key"] = key
    text = _get(session, f"{CG_URL}/coins/markets", params)
    rows = json.loads(text)
    out = [r for r in rows
           if r.get("id") not in exclude and r.get("symbol")]
    time.sleep(CG_SLEEP)
    return out[:top_n]
