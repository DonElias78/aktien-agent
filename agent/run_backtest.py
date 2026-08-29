"""Backtest der Bewertungsregeln auf langer Historie.

Aufruf:
    python -m agent.run_backtest --start 2005-01-01 --classes aktie_us,etf

Prueft eine simple, vollstaendig offengelegte Regel:
  monatliche Umschichtung
  Rangliste nach Momentum 12 minus 1
  optionaler Trendfilter Kurs ueber SMA200
  Gleichgewichtung der Top N
  Handelskosten je Umschichtung als Parameter

Ausgabe: reports/backtest.md und data/backtest_equity.csv

Bewusst offengelegte Verzerrungen stehen im Report, nicht im Kleingedruckten.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import numpy as np
import pandas as pd

from agent import storage, universe

TRADING_DAYS = 252


def load_panel(classes: set[str], start: str) -> tuple[pd.DataFrame, dict]:
    """Baut eine Kursmatrix Datum x Symbol aus data/history/."""
    meta = {}
    us = universe._US_FALLBACK  # ohne Netz: feste Liste als Klassenzuordnung
    for a in universe.build_universe(us):
        meta[storage.safe_name(a.key)] = a
    series = {}
    for path in sorted(storage.HISTORY.glob("*.csv")):
        stem = path.stem
        a = meta.get(stem)
        if a is not None:
            cls, investable = a.asset_class, a.investable
        elif stem.endswith("-usd"):
            cls, investable = "krypto", True
        elif stem.endswith(".de"):
            cls, investable = "aktie_de", True
        elif stem.startswith("_"):
            cls, investable = "index", False
        else:
            cls, investable = "aktie_us", True
        if cls not in classes or not investable:
            continue
        df = pd.read_csv(path)
        if "date" not in df or "close" not in df or df.empty:
            continue
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date", "close"]).drop_duplicates("date", keep="last")
        s = df.set_index("date")["close"].astype(float).sort_index()
        s = s[s > 0]
        if len(s) < 300:
            continue
        series[stem] = s
    if not series:
        raise SystemExit("Keine Historien gefunden. Erst run_daily mit --full-history laufen lassen.")
    panel = pd.DataFrame(series).sort_index()
    panel = panel[panel.index >= pd.Timestamp(start)]
    panel = panel.ffill(limit=5)
    return panel, meta


def backtest(panel: pd.DataFrame, top_n: int, use_trend: bool,
             cost_bps: float = 10.0) -> dict:
    """Monatliche Umschichtung. Gibt Equity Kurve und Kennzahlen zurueck."""
    monthly_idx = panel.resample("ME").last().index
    monthly_idx = [d for d in monthly_idx if d in panel.index or True]
    sma200 = panel.rolling(200, min_periods=200).mean()

    equity = [1.0]
    dates = []
    prev_holdings: set[str] = set()
    monthly_returns = []
    holdings_log = []

    px_monthly = panel.reindex(monthly_idx, method="ffill")
    sma_monthly = sma200.reindex(monthly_idx, method="ffill")

    for i in range(13, len(monthly_idx) - 1):
        t = monthly_idx[i]
        t_next = monthly_idx[i + 1]
        p_now = px_monthly.loc[t]
        p_12 = px_monthly.loc[monthly_idx[i - 12]]
        p_1 = px_monthly.loc[monthly_idx[i - 1]]

        mom = (p_1 / p_12) - 1.0
        valid = mom.notna() & p_now.notna()
        if use_trend:
            valid &= (p_now > sma_monthly.loc[t])
        cand = mom[valid].sort_values(ascending=False)
        picks = list(cand.head(top_n).index)
        if not picks:
            monthly_returns.append(0.0)
            equity.append(equity[-1])
            dates.append(t_next)
            prev_holdings = set()
            continue

        fwd = (px_monthly.loc[t_next, picks] / p_now[picks] - 1.0)
        fwd = fwd.replace([np.inf, -np.inf], np.nan).dropna()
        r = float(fwd.mean()) if len(fwd) else 0.0

        turnover = len(set(picks) ^ prev_holdings) / max(len(picks), 1)
        r -= turnover * (cost_bps / 10000.0)
        prev_holdings = set(picks)

        monthly_returns.append(r)
        equity.append(equity[-1] * (1 + r))
        dates.append(t_next)
        holdings_log.append({"date": t.strftime("%Y-%m-%d"), "picks": picks})

    eq = pd.Series(equity[1:], index=pd.DatetimeIndex(dates))
    return {"equity": eq, "returns": pd.Series(monthly_returns, index=eq.index),
            "holdings": holdings_log}


def stats(eq: pd.Series, rets: pd.Series) -> dict:
    if eq.empty:
        return {}
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else float("nan")
    vol = rets.std() * np.sqrt(12)
    sharpe = (rets.mean() * 12) / vol if vol > 0 else float("nan")
    dd = (eq / eq.cummax() - 1).min()
    return {
        "start": eq.index[0].strftime("%Y-%m-%d"),
        "ende": eq.index[-1].strftime("%Y-%m-%d"),
        "jahre": round(years, 1),
        "endwert_aus_1": round(float(eq.iloc[-1]), 3),
        "cagr": round(float(cagr), 4),
        "vola_pa": round(float(vol), 4),
        "sharpe": round(float(sharpe), 2),
        "max_drawdown": round(float(dd), 4),
        "positive_monate": round(float((rets > 0).mean()), 3),
        "monate": int(len(rets)),
    }


def buy_and_hold(panel: pd.DataFrame, symbol: str) -> dict:
    if symbol not in panel.columns:
        return {}
    s = panel[symbol].dropna()
    m = s.resample("ME").last().dropna()
    eq = m / m.iloc[0]
    return stats(eq, eq.pct_change().dropna())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2005-01-01")
    ap.add_argument("--classes", default="aktie_us,etf")
    ap.add_argument("--cost-bps", type=float, default=10.0)
    args = ap.parse_args()

    classes = set(args.classes.split(","))
    panel, _ = load_panel(classes, args.start)
    print(f"Panel: {panel.shape[1]} Werte, {panel.shape[0]} Tage, "
          f"{panel.index.min().date()} bis {panel.index.max().date()}")

    grid = []
    best = None
    for top_n in (5, 10, 20):
        for use_trend in (True, False):
            res = backtest(panel, top_n, use_trend, args.cost_bps)
            st = stats(res["equity"], res["returns"])
            st.update({"top_n": top_n, "trendfilter": use_trend})
            grid.append(st)
            if best is None or st.get("sharpe", -9) > best[0].get("sharpe", -9):
                best = (st, res)

    bench = {sym: buy_and_hold(panel, sym) for sym in ("spy", "qqq", "gld", "btc-usd")}
    bench = {k: v for k, v in bench.items() if v}

    storage.REPORTS.mkdir(parents=True, exist_ok=True)
    if best:
        best[1]["equity"].to_csv(storage.ROOT / "data" / "backtest_equity.csv",
                                 header=["equity"])

    lines = ["# Backtest der Bewertungsregel", ""]
    lines.append(f"Erstellt am {dt.date.today().isoformat()}")
    lines.append(f"Universum: {panel.shape[1]} Werte, Klassen {sorted(classes)}")
    lines.append(f"Zeitraum: {panel.index.min().date()} bis {panel.index.max().date()}")
    lines.append(f"Handelskosten je Umschichtung: {args.cost_bps} Basispunkte auf den Umschlag")
    lines.append("")
    lines.append("## Ergebnisse der Varianten")
    lines.append("")
    lines.append("| Top N | Trendfilter | CAGR | Vola p.a. | Sharpe | Max Drawdown | positive Monate | Monate |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for st in grid:
        lines.append(
            f"| {st['top_n']} | {'ja' if st['trendfilter'] else 'nein'} | "
            f"{st['cagr']*100:.1f}% | {st['vola_pa']*100:.1f}% | {st['sharpe']:.2f} | "
            f"{st['max_drawdown']*100:.1f}% | {st['positive_monate']*100:.0f}% | {st['monate']} |")
    lines.append("")
    if bench:
        lines.append("## Vergleich Kaufen und Halten")
        lines.append("")
        lines.append("| Wert | CAGR | Vola p.a. | Sharpe | Max Drawdown |")
        lines.append("|---|---|---|---|---|")
        for sym, st in bench.items():
            lines.append(f"| {sym} | {st['cagr']*100:.1f}% | {st['vola_pa']*100:.1f}% | "
                         f"{st['sharpe']:.2f} | {st['max_drawdown']*100:.1f}% |")
        lines.append("")
    lines.append("## Verzerrungen, die dieses Ergebnis nach oben ziehen")
    lines.append("")
    lines.append("- Survivorship Bias: Das Universum enthaelt die heutigen Indexmitglieder. "
                 "Firmen, die pleite gingen oder aus dem Index flogen, fehlen. Das schoent "
                 "jede Rueckrechnung, teils deutlich.")
    lines.append("- Look ahead auf Universumsebene: Die Auswahl der Werte kennt die Gegenwart, "
                 "die Regel selbst nicht.")
    lines.append("- Gerechnet wird auf dividendenbereinigten Kursen von Yahoo. Dividenden gelten "
                 "damit als sofort wieder angelegt, ohne Steuerabzug. Real faellt auf Ausschuettungen "
                 "Steuer an, die Rueckrechnung liegt dadurch ueber der erreichbaren Rendite.")
    lines.append("- Preisindizes wie der DAX Kursindex und Rohstofffutures kennen keine Dividende. "
                 "Ein Vergleich zwischen Klassen hinkt deshalb systematisch.")
    lines.append("- Steuern, Spreads und Slippage sind ausser den pauschalen Kosten nicht modelliert.")
    lines.append("- Mehrere Varianten auf denselben Daten getestet heisst: die beste Variante "
                 "ist teilweise Zufall. Ein Vorsprung von wenigen Zehntel im Sharpe ist kein Beweis.")
    lines.append("")
    lines.append("Konsequenz: Diese Zahlen taugen als Plausibilitaetspruefung der Regel, "
                 "nicht als Renditeversprechen. Der eigentliche Test ist der Vorwaertslauf ab heute.")
    (storage.REPORTS / "backtest.md").write_text("\n".join(lines), encoding="utf-8")
    (storage.ROOT / "data" / "backtest_summary.json").write_text(
        json.dumps({"grid": grid, "benchmarks": bench}, indent=2), encoding="utf-8")
    print("Backtest geschrieben nach reports/backtest.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
