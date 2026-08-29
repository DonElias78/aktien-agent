"""Taeglicher Lauf: Daten holen, Kennzahlen rechnen, Ergebnisse committen.

Aufruf:
    python -m agent.run_daily             # normaler Tageslauf
    python -m agent.run_daily --limit 20  # Testlauf mit wenigen Werten

Erzeugt:
    data/history/<symbol>.csv      fortlaufende Kurshistorie
    data/snapshots/<datum>.csv     Kennzahlen aller Werte an diesem Tag
    data/latest_signals.json       Rangliste und Diagnose fuer den Agenten
    data/run_log.csv               Protokoll jedes Laufs
    reports/<datum>.md             lesbarer Kurzreport
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import traceback

import pandas as pd

from agent import fetch, indicators, storage, universe

LOOKBACK_REFRESH_DAYS = 10   # so viele Tage werden bei jedem Lauf neu geholt
MIN_DAYS_FOR_SCORE = 260     # weniger Historie, kein Score

# Plausibilitaetsgrenzen fuer die Rangliste. Sie sortieren keine unbequemen
# Kurse aus, sondern Datenfehler. Jede Grenze hat einen nachvollziehbaren
# Grund und jeder Ausschluss wird im Report namentlich ausgewiesen.
MAX_TAGESSPRUNG = 2.50   # Sprung ueber 250 Prozent an einem Tag. Gemessen
                         # an echten Faellen: Moderna hat sich am 19.08.2026
                         # nach einer Krebsstudie an einem Tag verdreifacht
                         # (plus 177 Prozent), das ist echt und muss drin
                         # bleiben. Umgestellte Kryptowerte sprangen um 874,
                         # 6314 und 125331 Prozent.
GLATTE_FAKTOREN = (2, 3, 4, 5, 6, 8, 10, 20, 100, 1000)
FAKTOR_TOLERANZ = 0.03   # Splits und Umstellungen treffen einen glatten
                         # Faktor fast exakt, Nachrichten nicht. Monster
                         # Beverage sprang nach dem 2 zu 1 Split um Faktor
                         # 1.96, Moderna um 2.77. Nur der erste Fall ist ein
                         # Artefakt.
MIN_VOLA = 0.005         # unter 0,5 Prozent Jahresschwankung ist es ein
                         # Stablecoin. Der Anleihen ETF SHY liegt bei 1,3
                         # Prozent und muss drin bleiben, RLUSD bei 0,29.
MAX_STALE_TAGE = 5       # aeltere Kurse gelten als nicht mehr aktuell


def ist_glatter_faktor(sprung: float) -> int | None:
    """Prueft, ob ein Tagessprung einem Split oder einer Umstellung entspricht."""
    faktor = 1.0 + abs(sprung)
    for f in GLATTE_FAKTOREN:
        if abs(faktor - f) / f <= FAKTOR_TOLERANZ:
            return f
        if abs(faktor - 1 / f) <= FAKTOR_TOLERANZ / f:
            return f
    return None


def collect(session, assets, full_history: bool, fortschritt_alle: int = 50):
    """Holt alle Werte bei Yahoo, inkrementell wenn schon Historie da ist."""
    ok, failed = [], []
    for i, a in enumerate(assets, 1):
        try:
            old = storage.load_history(a.key)
            start = None
            if not full_history and not old.empty:
                last = pd.to_datetime(old["date"]).max().date()
                start = last - dt.timedelta(days=LOOKBACK_REFRESH_DAYS)
            new = fetch.fetch_yahoo(session, a.query, start=start)
            merged = storage.merge_history(old, new)
            if merged.empty:
                failed.append((a.key, "keine Daten"))
                continue
            storage.save_history(a.key, merged)
            ok.append((a, merged))
        except Exception as exc:  # noqa: BLE001
            failed.append((a.key, str(exc)[:120]))
        if i % fortschritt_alle == 0:
            print(f"  {i}/{len(assets)} verarbeitet, {len(failed)} Fehler", flush=True)
    return ok, failed


def crypto_assets(session, top_n: int):
    """Fragt bei CoinGecko die groessten Coins ab und uebersetzt sie auf Yahoo."""
    try:
        coins = fetch.fetch_top_coins(session, top_n, universe.STABLECOINS)
    except Exception as exc:  # noqa: BLE001
        return [], [("coingecko/markets", str(exc)[:160])]
    assets, skipped = [], []
    for c in coins:
        sym = universe.crypto_symbol(c.get("symbol", ""))
        if sym.split("-")[0] in universe.CRYPTO_SKIP:
            skipped.append((sym, "bewusst uebersprungen, bei Yahoo nicht vorhanden"))
            continue
        assets.append(universe.Asset(sym, "yahoo", sym,
                                     c.get("name") or c.get("symbol", "").upper(),
                                     "krypto"))
    return assets, skipped


def ausschlussgrund(row) -> str:
    """Warum ein Wert nicht in die Rangliste darf. Leer heisst: er darf."""
    if row.get("n_days", 0) < MIN_DAYS_FOR_SCORE:
        return f"zu kurze Historie ({row.get('n_days', 0)} Tage)"
    sprung = row.get("max_tagessprung_252d")
    if sprung is not None and not pd.isna(sprung):
        if sprung > MAX_TAGESSPRUNG:
            return f"Datenbruch, groesster Tagessprung {sprung * 100:.0f} Prozent"
        faktor = ist_glatter_faktor(sprung) if sprung > 0.40 else None
        if faktor:
            return (f"Split oder Umstellung, Tagessprung {sprung * 100:.0f} Prozent "
                    f"entspricht Faktor {faktor}")
    vola = row.get("vol_252d")
    if vola is not None and not pd.isna(vola) and vola < MIN_VOLA:
        return f"kaum Bewegung, Vola {vola * 100:.2f} Prozent, vermutlich Stablecoin"
    grenze = (dt.date.today() - dt.timedelta(days=MAX_STALE_TAGE)).isoformat()
    if row.get("last_date", "") < grenze:
        return f"Kurs veraltet, letzter Stand {row.get('last_date')}"
    return ""


def build_rows(collected):
    rows = []
    for asset, df in collected:
        m = indicators.compute_metrics(df)
        if not m:
            continue
        row = {
            "key": asset.key, "name": asset.name,
            "asset_class": asset.asset_class,
            "investable": asset.investable,
            "source": asset.source,
            "last_date": pd.to_datetime(df["date"]).max().strftime("%Y-%m-%d"),
        }
        row.update(m)
        grund = ausschlussgrund(row)
        row["ausschluss"] = grund
        row["score_raw"] = float("nan") if grund else indicators.score_row(m)
        rows.append(row)
    indicators.cross_section_rank(rows, "score_raw")
    return rows


def top_by_class(rows, asset_class, n=10):
    sel = [r for r in rows
           if r["asset_class"] == asset_class and r.get("score") is not None
           and r.get("investable")]
    sel.sort(key=lambda r: r["score"], reverse=True)
    return sel[:n]


def fmt_pct(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/a"
    return f"{x * 100:+.1f}%"


def fmt_abs(x):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "n/a"
    return f"{x * 100:.1f}%"


def write_report(path, today, rows, failed, duration, stale):
    lines = [f"# Don Elias Aktien Agent, Lauf vom {today}", ""]
    lines.append(f"Werte erfolgreich verarbeitet: {len(rows)}")
    lines.append(f"Fehlgeschlagen: {len(failed)}")
    lines.append(f"Laufzeit: {duration:.0f} Sekunden")
    if stale:
        lines.append(f"Werte mit veraltetem Kursdatum: {len(stale)}")
    lines.append("")
    for cls, titel in (("aktie_us", "US Aktien"), ("aktie_de", "Deutsche Aktien"),
                       ("etf", "ETFs"), ("rohstoff", "Rohstoffe"),
                       ("krypto", "Krypto")):
        top = top_by_class(rows, cls, 10)
        if not top:
            continue
        lines.append(f"## Top 10 {titel}")
        lines.append("")
        lines.append("| Rang | Wert | Score | 12-1 Momentum | 63 Tage | 21 Tage | Vola p.a. | ueber SMA200 |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for i, r in enumerate(top, 1):
            lines.append(
                f"| {i} | {r['name']} ({r['key']}) | {r['score']:.1f} | "
                f"{fmt_pct(r.get('mom_12_1'))} | {fmt_pct(r.get('ret_63d'))} | "
                f"{fmt_pct(r.get('ret_21d'))} | {fmt_abs(r.get('vol_252d'))} | "
                f"{'ja' if r.get('above_sma_200') else 'nein'} |")
        lines.append("")
    ausgeschlossen = [r for r in rows if r.get("ausschluss")]
    if ausgeschlossen:
        lines.append(f"## Aus der Rangliste ausgeschlossen: {len(ausgeschlossen)} Werte")
        lines.append("")
        lines.append("Ausgeschlossen wird nur, was nachweislich ein Datenproblem hat, "
                     "nie ein unbequemer Kurs. Jeder Fall steht hier mit Grund.")
        lines.append("")
        gruende: dict[str, list[str]] = {}
        for r in ausgeschlossen:
            art = r["ausschluss"].split(",")[0]
            gruende.setdefault(art, []).append(f"{r['key']} ({r['ausschluss']})")
        for art, werte in sorted(gruende.items(), key=lambda x: -len(x[1])):
            lines.append(f"- **{art}**: {len(werte)} Werte")
            for w in werte[:12]:
                lines.append(f"  - {w}")
            if len(werte) > 12:
                lines.append(f"  - ... und {len(werte) - 12} weitere")
        lines.append("")

    if failed:
        lines.append("## Fehlgeschlagene Abrufe")
        lines.append("")
        for k, msg in failed[:40]:
            lines.append(f"- {k}: {msg}")
        if len(failed) > 40:
            lines.append(f"- ... und {len(failed) - 40} weitere")
        lines.append("")
    lines.append("---")
    lines.append("Kursquelle: Yahoo Finance, dividendenbereinigte "
                 "Tagesschlusskurse. Die Rangliste der groessten Coins kommt "
                 "von CoinGecko. Keine Echtzeitdaten. Diese Auswertung ist "
                 "Statistik, keine Anlageberatung.")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="nur die ersten N Werte, fuer Tests")
    ap.add_argument("--full-history", action="store_true",
                    help="komplette Historie neu laden statt inkrementell")
    ap.add_argument("--no-crypto", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    today = dt.date.today().isoformat()
    session = fetch._session()

    us = universe.load_us_tickers(session)
    assets = universe.build_universe(us)
    if args.limit:
        assets = assets[: args.limit]

    failed: list[tuple[str, str]] = []
    if not args.no_crypto:
        c_assets, c_failed = crypto_assets(session, universe.CRYPTO_TOP_N)
        assets += c_assets
        failed += c_failed
        print(f"Krypto aus CoinGecko: {len(c_assets)} Coins", flush=True)

    print(f"Universum: {len(assets)} Werte", flush=True)
    ok, f2 = collect(session, assets, args.full_history)
    failed += f2
    print(f"Abruf fertig: {len(ok)} ok, {len(failed)} Fehler", flush=True)
    for key, msg in failed[:25]:
        print(f"  FEHLER {key}: {msg}", flush=True)
    if len(failed) > 25:
        print(f"  ... und {len(failed) - 25} weitere", flush=True)

    rows = build_rows(ok)
    if not rows:
        print("FEHLER: keine verwertbaren Daten", file=sys.stderr)
        return 1

    storage.SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    storage.REPORTS.mkdir(parents=True, exist_ok=True)
    snap = pd.DataFrame(rows)
    snap.insert(0, "snapshot_date", today)
    snap.to_csv(storage.SNAPSHOTS / f"{today}.csv", index=False)

    cutoff = (dt.date.today() - dt.timedelta(days=7)).isoformat()
    stale = [r["key"] for r in rows if r["last_date"] < cutoff]

    signals = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "snapshot_date": today,
        "universe_size": len(rows),
        "failed_count": len(failed),
        "failed": [{"key": k, "error": m} for k, m in failed[:60]],
        "stale_symbols": stale[:60],
        "ausgeschlossen": [{"key": r["key"], "grund": r["ausschluss"]}
                           for r in rows if r.get("ausschluss")][:80],
        "ausgeschlossen_anzahl": sum(1 for r in rows if r.get("ausschluss")),
        "top": {cls: top_by_class(rows, cls, 15) for cls in
                ("aktie_us", "aktie_de", "etf", "rohstoff", "krypto")},
        "breadth": {
            "anteil_ueber_sma200": round(
                sum(1 for r in rows if r.get("above_sma_200")) / len(rows), 3),
            "median_ret_21d": round(
                float(pd.Series([r.get("ret_21d") for r in rows]).median(skipna=True)), 5),
        },
        "benchmarks": {r["key"]: {"ret_21d": r.get("ret_21d"),
                                  "ret_252d": r.get("ret_252d"),
                                  "close": r.get("close")}
                       for r in rows
                       if r["key"] in ("^GSPC", "^GDAXI", "SPY", "GC=F",
                                       "BTC-USD", "^VIX")},
    }
    (storage.ROOT / "data" / "latest_signals.json").write_text(
        json.dumps(signals, indent=2, default=str), encoding="utf-8")

    duration = time.time() - t0
    write_report(storage.REPORTS / f"{today}.md", today, rows, failed, duration, stale)
    (storage.REPORTS / "latest.md").write_text(
        (storage.REPORTS / f"{today}.md").read_text(encoding="utf-8"), encoding="utf-8")

    log_path = storage.ROOT / "data" / "run_log.csv"
    header = not log_path.exists()
    with log_path.open("a", encoding="utf-8") as fh:
        if header:
            fh.write("datum,werte_ok,werte_fehler,dauer_sek,stale\n")
        fh.write(f"{today},{len(rows)},{len(failed)},{duration:.0f},{len(stale)}\n")

    print(f"fertig in {duration:.0f}s, {len(rows)} Werte, {len(failed)} Fehler")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
