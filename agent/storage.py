"""Ablage der Kursdaten im Repository.

Pro Wert eine CSV unter data/history/. Taegliche Laeufe haengen nur neue
Zeilen an, dadurch bleiben die Git Diffs klein und die Historie
nachvollziehbar.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
HISTORY = ROOT / "data" / "history"
SNAPSHOTS = ROOT / "data" / "snapshots"
REPORTS = ROOT / "reports"

COLUMNS = ["date", "open", "high", "low", "close", "close_raw", "volume"]


def safe_name(key: str) -> str:
    return re.sub(r"[^a-z0-9_.-]", "_", key.lower())


def history_path(key: str) -> Path:
    return HISTORY / f"{safe_name(key)}.csv"


def load_history(key: str) -> pd.DataFrame:
    p = history_path(key)
    if not p.exists():
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_csv(p)
    if "date" in df:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date")
    return df


def save_history(key: str, df: pd.DataFrame) -> None:
    HISTORY.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    for col in COLUMNS:
        if col not in out:
            out[col] = pd.NA
    out = out[COLUMNS]
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out.to_csv(history_path(key), index=False)


def merge_history(old: pd.DataFrame, new: pd.DataFrame) -> pd.DataFrame:
    if old is None or old.empty:
        base = new
    elif new is None or new.empty:
        base = old
    else:
        base = pd.concat([old, new], ignore_index=True)
    if base is None or base.empty:
        return pd.DataFrame(columns=COLUMNS)
    base["date"] = pd.to_datetime(base["date"], errors="coerce")
    base = base.dropna(subset=["date", "close"])
    base = base.drop_duplicates(subset="date", keep="last").sort_values("date")
    return base.reset_index(drop=True)
