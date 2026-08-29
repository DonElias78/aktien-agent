"""Offline Test der gesamten Kette ohne Netzzugriff.

Ersetzt die Yahoo Abrufe durch erzeugte Zufallskurse und prueft, ob
Speicherung, Kennzahlen, Ranking, Report und Backtest sauber durchlaufen.
Ein Symbol faellt absichtlich aus, damit die Fehlerbehandlung mitgeprueft wird.

Aufruf:  python -m tests.test_offline
"""

from __future__ import annotations

import datetime as dt
import json
import sys

import numpy as np
import pandas as pd

from agent import fetch, indicators, storage, universe


def synth(n_days=1600, seed=0, drift=0.0003, vol=0.015) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    # Laenge aus dem tatsaechlichen Kalender ableiten, nicht annehmen:
    # pandas liefert je nach Version einen Tag weniger zurueck.
    dates = pd.bdate_range(end=dt.date.today(), periods=n_days)
    n_days = len(dates)
    rets = rng.normal(drift, vol, n_days)
    close = 100 * np.exp(np.cumsum(rets))
    return pd.DataFrame({
        "date": dates, "open": close, "high": close * 1.01,
        "low": close * 0.99, "close": close, "close_raw": close * 0.98,
        "volume": rng.integers(1e5, 1e7, n_days),
    })


def main() -> int:
    counter = {"n": 0}

    def fake_yahoo(session, symbol, start=None):
        counter["n"] += 1
        if symbol == "KAPUTT":
            raise fetch.FetchError("404 Symbol unbekannt")
        tage = 900 if symbol.endswith("-USD") else 1600
        return synth(n_days=tage, seed=abs(hash(symbol)) % 10_000,
                     drift=0.0002 + (abs(hash(symbol)) % 7) * 0.0001)

    def fake_top_coins(session, top_n, exclude):
        return [{"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
                {"id": "lido-staked-ether", "symbol": "steth", "name": "Lido stETH"}]

    fetch.fetch_yahoo = fake_yahoo
    fetch.fetch_top_coins = fake_top_coins
    universe.load_us_tickers = lambda session=None, limit=None: [
        "AAPL", "MSFT", "NVDA", "BRK.B", "KAPUTT"]

    from agent import run_daily
    rc = run_daily.main()
    assert rc == 0, "run_daily lieferte Fehlercode"

    today = dt.date.today().isoformat()
    snap = storage.SNAPSHOTS / f"{today}.csv"
    assert snap.exists(), "Snapshot fehlt"
    df = pd.read_csv(snap)
    print(f"OK Snapshot: {len(df)} Zeilen, {len(df.columns)} Spalten")
    assert {"score", "mom_12_1", "vol_252d", "above_sma_200"} <= set(df.columns)
    assert df["score"].notna().sum() > 0, "kein Score berechnet"

    # Symbolformen pruefen
    keys = set(df["key"])
    assert "BRK-B" in keys, "Punkt im US Kuerzel wurde nicht umgesetzt"
    assert "SAP.DE" in keys, "deutsche Aktie fehlt"
    assert "GC=F" in keys, "Gold fehlt"
    assert "^GSPC" in keys, "Index fehlt"
    assert "BTC-USD" in keys, "Krypto fehlt"
    assert "STETH-USD" not in keys, "uebersprungener Coin wurde doch geladen"
    print("OK Symbolformen: BRK-B, SAP.DE, GC=F, ^GSPC, BTC-USD")

    # Indizes und Devisen duerfen nie im Kaufranking auftauchen
    sig = json.loads((storage.ROOT / "data" / "latest_signals.json").read_text())
    alle_top = [r["key"] for liste in sig["top"].values() for r in liste]
    assert "^GSPC" not in alle_top and "EURUSD=X" not in alle_top, \
        "nicht investierbarer Wert steht im Ranking"
    print("OK Ranking enthaelt keine Indizes oder Devisen")
    print("   Universum:", sig["universe_size"], "Werte,",
          sig["failed_count"], "Fehler, Breite ueber SMA200:",
          sig["breadth"]["anteil_ueber_sma200"])
    assert sig["failed_count"] >= 1, "der eingebaute Ausfall wurde verschluckt"

    rep = (storage.REPORTS / "latest.md").read_text(encoding="utf-8")
    assert "Top 10" in rep and "Yahoo" in rep
    print("OK Report:", len(rep), "Zeichen")

    # Kennzahlen gegen Handrechnung
    s = pd.Series([100, 110, 121], dtype=float)
    assert abs(indicators._ret(s, 1) - 0.10) < 1e-9
    assert abs(indicators._ret(s, 2) - 0.21) < 1e-9
    flat = pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=400),
                         "close": np.linspace(100, 200, 400)})
    m = indicators.compute_metrics(flat)
    assert m["above_sma_200"] is True
    assert abs(m["dist_high_252d"]) < 1e-9
    print("OK Kennzahlen gegen Handrechnung")

    from agent import run_backtest
    sys.argv = ["x", "--start", "2019-01-01", "--classes", "aktie_us,etf,krypto"]
    rc = run_backtest.main()
    assert rc == 0
    bt = (storage.REPORTS / "backtest.md").read_text(encoding="utf-8")
    assert "Verzerrungen" in bt
    print("OK Backtest:", len(bt), "Zeichen")

    print(f"\nAlle Tests bestanden. {counter['n']} simulierte Abrufe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
