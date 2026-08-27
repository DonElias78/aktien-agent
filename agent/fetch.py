"""Datenbeschaffung fuer den Don Elias Aktien Agenten.

Zwei Quellen:
  stooq.com    Tages OHLCV als CSV, kein Key, inkrementell per Datumsfilter
  CoinGecko    Tageskurse fuer Krypto, Demo Tier ohne Key moeglich

Jeder Abruf ist gedrosselt und wird bei Fehlern wiederholt. Fehlschlaege
werden nicht verschluckt, sondern als Liste zurueckgegeben, damit der
Tagesreport sie ausweist.
"""

from __future__ import annotations

import io
import os
import time
import random
import datetime as dt

import pandas as pd
import requests

STOOQ_URL = "https://stooq.com/q/d/l/"
CG_URL = "https://api.coingecko.com/api/v3"

USER_AGENT = "don-elias-aktien-agent/1.0 (+github actions)"

STOOQ_SLEEP = float(os.getenv("STOOQ_SLEEP", "0.6"))
CG_SLEEP = float(os.getenv("CG_SLEEP", "3.0"))


class FetchError(Exception):
    pass


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": USER_AGENT})
    return s


def _get(session: requests.Session, url: str, params: dict, tries: int = 4) -> str:
    last = None
    for attempt in range(tries):
        try:
            r = session.get(url, params=params, timeout=40)
            if r.status_code == 429:
                raise FetchError("429 rate limit")
            r.raise_for_status()
            return r.text
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep((2 ** attempt) + random.random())
    raise FetchError(f"{url} fehlgeschlagen: {last}")


# ---------------------------------------------------------------------------
# stooq
# ---------------------------------------------------------------------------

def fetch_stooq(session: requests.Session, symbol: str,
                start: dt.date | None = None) -> pd.DataFrame:
    """Tages OHLCV. start=None laedt die komplette verfuegbare Historie."""
    params = {"s": symbol, "i": "d"}
    if start:
        params["d1"] = start.strftime("%Y%m%d")
        params["d2"] = dt.date.today().strftime("%Y%m%d")
    text = _get(session, STOOQ_URL, params)
    if not text.lstrip().lower().startswith("date"):
        if "exceed" in text[:300].lower():
            raise FetchError(f"stooq Tageslimit erreicht bei {symbol}: {text[:80]}")
        raise FetchError(f"stooq lieferte kein CSV fuer {symbol}: {text[:80]}")
    df = pd.read_csv(io.StringIO(text))
    if df.empty:
        return df
    df.columns = [c.strip().lower() for c in df.columns]
    keep = [c for c in ("date", "open", "high", "low", "close", "volume") if c in df.columns]
    df = df[keep].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date", "close"]).sort_values("date")
    time.sleep(STOOQ_SLEEP)
    return df


# ---------------------------------------------------------------------------
# CoinGecko
# ---------------------------------------------------------------------------

def _cg_params(extra: dict) -> dict:
    key = os.getenv("COINGECKO_API_KEY", "").strip()
    if key:
        extra = dict(extra)
        extra["x_cg_demo_api_key"] = key
    return extra


def fetch_top_coins(session: requests.Session, top_n: int, exclude: set[str]) -> list[dict]:
    text = _get(session, f"{CG_URL}/coins/markets", _cg_params({
        "vs_currency": "usd", "order": "market_cap_desc",
        "per_page": str(min(top_n * 2, 250)), "page": "1",
        "price_change_percentage": "24h,7d,30d",
    }))
    import json
    rows = json.loads(text)
    out = [r for r in rows if r.get("id") not in exclude]
    time.sleep(CG_SLEEP)
    return out[:top_n]


def fetch_coin_history(session: requests.Session, coin_id: str, days: str = "max") -> pd.DataFrame:
    text = _get(session, f"{CG_URL}/coins/{coin_id}/market_chart", _cg_params({
        "vs_currency": "usd", "days": days, "interval": "daily",
    }))
    import json
    payload = json.loads(text)
    prices = payload.get("prices") or []
    vols = dict((int(t), v) for t, v in (payload.get("total_volumes") or []))
    rows = []
    for ts, price in prices:
        d = dt.datetime.fromtimestamp(ts / 1000, dt.timezone.utc).date()
        rows.append({"date": pd.Timestamp(d), "close": price,
                     "volume": vols.get(int(ts), float("nan"))})
    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset="date", keep="last").sort_values("date")
        df["open"] = df["close"]
        df["high"] = df["close"]
        df["low"] = df["close"]
    time.sleep(CG_SLEEP)
    return df
