"""Kennzahlen und Bewertungslogik.

Alle Formeln stehen offen im Code, damit jede Zahl im Report nachrechenbar
ist. Es gibt keine versteckten Parameter.

Die Bewertung folgt zwei in der Finanzliteratur dokumentierten Effekten:
  Querschnitts Momentum (Jegadeesh/Titman 1993): Rendite der letzten 12
  Monate ohne den letzten Monat, weil der letzte Monat historisch zur
  Umkehr neigt.
  Trendfilter (Moskowitz/Ooi/Pedersen 2012, Faber 2007): nur Werte ueber
  ihrem 200 Tage Durchschnitt.
Ob das im eigenen Universum traegt, entscheidet der Backtest, nicht die
Literatur. Der Backtest liegt in run_backtest.py.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

TRADING_DAYS = 252


def _ret(series: pd.Series, lookback: int) -> float:
    if len(series) <= lookback:
        return float("nan")
    past = series.iloc[-1 - lookback]
    if past <= 0 or np.isnan(past):
        return float("nan")
    return float(series.iloc[-1] / past - 1.0)


def rsi(series: pd.Series, period: int = 14) -> float:
    if len(series) < period + 1:
        return float("nan")
    delta = series.diff().dropna()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    if loss.empty or gain.empty:
        return float("nan")
    last_loss = loss.iloc[-1]
    last_gain = gain.iloc[-1]
    if last_loss == 0:
        return 100.0
    rs = last_gain / last_loss
    return float(100 - 100 / (1 + rs))


def max_drawdown(series: pd.Series) -> float:
    if series.empty:
        return float("nan")
    running_max = series.cummax()
    dd = series / running_max - 1.0
    return float(dd.min())


def compute_metrics(df: pd.DataFrame) -> dict:
    """df: Spalten date, close, optional volume. Rueckgabe: Kennzahlen Dict."""
    out: dict[str, float] = {}
    if df is None or df.empty or "close" not in df:
        return out
    s = df["close"].astype(float).reset_index(drop=True)
    out["close"] = float(s.iloc[-1])
    out["n_days"] = int(len(s))

    for label, lb in (("ret_1d", 1), ("ret_5d", 5), ("ret_21d", 21),
                      ("ret_63d", 63), ("ret_126d", 126), ("ret_252d", 252)):
        out[label] = _ret(s, lb)

    # Momentum 12 minus 1: Rendite ueber 252 Tage, letzte 21 Tage ausgeklammert
    if len(s) > 252:
        past = s.iloc[-253]
        recent = s.iloc[-22]
        out["mom_12_1"] = float(recent / past - 1.0) if past > 0 else float("nan")
    else:
        out["mom_12_1"] = float("nan")

    rets = s.pct_change().dropna()
    # Groesster Tagessprung im letzten Jahr. Dient als Bruchtest: echte Kurse
    # springen selten ueber 90 Prozent an einem Tag, Umbenennungen und
    # Umstellungen von Kryptowerten schon.
    out["max_tagessprung_252d"] = (float(rets.tail(252).abs().max())
                                   if len(rets) >= 1 else float("nan"))
    out["vol_21d"] = float(rets.tail(21).std() * np.sqrt(TRADING_DAYS)) if len(rets) >= 21 else float("nan")
    out["vol_252d"] = float(rets.tail(252).std() * np.sqrt(TRADING_DAYS)) if len(rets) >= 252 else float("nan")

    out["sma_50"] = float(s.tail(50).mean()) if len(s) >= 50 else float("nan")
    out["sma_200"] = float(s.tail(200).mean()) if len(s) >= 200 else float("nan")
    out["above_sma_200"] = bool(out["close"] > out["sma_200"]) if not np.isnan(out.get("sma_200", np.nan)) else False
    out["above_sma_50"] = bool(out["close"] > out["sma_50"]) if not np.isnan(out.get("sma_50", np.nan)) else False

    win = s.tail(252)
    out["high_252d"] = float(win.max())
    out["low_252d"] = float(win.min())
    out["dist_high_252d"] = float(out["close"] / out["high_252d"] - 1.0) if out["high_252d"] > 0 else float("nan")
    out["drawdown_252d"] = max_drawdown(win)
    out["rsi_14"] = rsi(s, 14)

    if "volume" in df:
        v = pd.to_numeric(df["volume"], errors="coerce").dropna()
        if len(v) >= 21:
            out["vol_avg_21d"] = float(v.tail(21).mean())
            out["vol_ratio"] = float(v.iloc[-1] / v.tail(21).mean()) if v.tail(21).mean() > 0 else float("nan")
    return out


def score_row(m: dict) -> float:
    """Rohscore vor der Querschnitts Normierung.

    Bestandteile, gleich gewichtet und bewusst simpel gehalten:
      Momentum 12 minus 1
      Rendite 63 Tage
      Trendbonus, wenn Kurs ueber SMA200 und SMA50
      Abschlag fuer hohe Volatilitaet (risikoadjustiert statt roh)
    """
    mom = m.get("mom_12_1")
    r63 = m.get("ret_63d")
    vol = m.get("vol_252d") or m.get("vol_21d")
    if mom is None or (isinstance(mom, float) and np.isnan(mom)):
        return float("nan")
    if vol is None or (isinstance(vol, float) and (np.isnan(vol) or vol <= 0)):
        return float("nan")
    base = (mom / vol)
    if r63 is not None and not (isinstance(r63, float) and np.isnan(r63)):
        base += (r63 / vol) * 0.5
    if m.get("above_sma_200"):
        base += 0.25
    if m.get("above_sma_50"):
        base += 0.10
    return float(base)


def cross_section_rank(rows: list[dict], field: str = "score_raw") -> list[dict]:
    """Perzentilrang 0 bis 100 innerhalb des Universums."""
    vals = pd.Series([r.get(field, float("nan")) for r in rows], dtype="float64")
    ranks = vals.rank(pct=True) * 100
    for r, v in zip(rows, ranks):
        r["score"] = None if pd.isna(v) else round(float(v), 1)
    return rows
