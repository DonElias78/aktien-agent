"""Offline Test der gesamten Kette ohne Netzzugriff.

Ersetzt die Abrufe durch erzeugte Zufallskurse und prueft, ob Speicherung,
Kennzahlen, Ranking, Report und Backtest sauber durchlaufen.

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
    dates = pd.bdate_range(end=dt.date.today(), periods=n_days)
    rets = rng.normal(drift, vol, n_days)
    close = 100 * np.exp(np.cumsum(rets))
    return pd.DataFrame({
        "date": dates, "open": close, "high": close * 1.01,
        "low": close * 0.99, "close": close,
        "volume": rng.integers(1e5, 1e7, n_days),
    })


def main() -> int:
    counter = {"n": 0}

    def fake_stooq(session, symbol, start=None):
        counter["n"] += 1
        if symbol == "kaputt.us":
            raise fetch.FetchError("simulierter Ausfall")
        return synth(seed=abs(hash(symbol)) % 10_000,
                     drift=0.0002 + (abs(hash(symbol)) % 7) * 0.0001)

    def fake_top_coins(session, top_n, exclude):
        return [{"id": f"coin{i}", "symbol": f"c{i}"} for i in range(3)]

    def fake_coin_hist(session, coin_id, days="max"):
        return synth(n_days=900, seed=abs(hash(coin_id)) % 999, vol=0.04)

    fetch.fetch_stooq = fake_stooq
    fetch.fetch_top_coins = fake_top_coins
    fetch.fetch_coin_history = fake_coin_hist
    universe.load_us_tickers = lambda session=None, limit=None: [
        "AAPL", "MSFT", "NVDA", "BRK.B", "KAPUTT"]

    from agent import run_daily
    rc = run_daily.main()
    assert rc == 0, "run_daily lieferte Fehlercode"

    today = dt.date.today().isoformat()
    snap = storage.SNAPSHOTS / f"{today}.csv"
    assert snap.exists(), "Snapshot fehlt"
    df = pd.read_csv(snap)
    print(f"OK Snapshot: {len(df)} Zeilen, Spalten {len(df.columns)}")
    assert {"score", "mom_12_1", "vol_252d", "above_sma_200"} <= set(df.columns)
    assert df["score"].notna().sum() > 0, "kein Score berechnet"

    sig = json.loads((storage.ROOT / "data" / "latest_signals.json").read_text())
    print("OK Signale:", sig["universe_size"], "Werte,",
          sig["failed_count"], "Fehler,",
          "Breite ueber SMA200:", sig["breadth"]["anteil_ueber_sma200"])
    assert sig["universe_size"] > 0
    assert any(len(v) > 0 for v in sig["top"].values()), "keine Rangliste"

    rep = (storage.REPORTS / "latest.md").read_text(encoding="utf-8")
    assert "Top 10" in rep, "Report ohne Rangliste"
    print("OK Report:", len(rep), "Zeichen")

    # Kennzahlen gegen Handrechnung pruefen
    s = pd.Series([100, 110, 121], dtype=float)
    assert abs(indicators._ret(s, 1) - 0.10) < 1e-9
    assert abs(indicators._ret(s, 2) - 0.21) < 1e-9
    flat = pd.DataFrame({"date": pd.bdate_range("2020-01-01", periods=400),
                         "close": np.linspace(100, 200, 400)})
    m = indicators.compute_metrics(flat)
    assert m["above_sma_200"] is True
    assert abs(m["dist_high_252d"]) < 1e-9, "Hoechststand falsch"
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
