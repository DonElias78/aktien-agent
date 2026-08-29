# Backtest der Bewertungsregel

Erstellt am 2026-08-29
Universum: 559 Werte, Klassen ['aktie_us', 'etf']
Zeitraum: 2005-01-03 bis 2026-08-28
Handelskosten je Umschichtung: 10.0 Basispunkte auf den Umschlag

## Ergebnisse der Varianten

| Top N | Trendfilter | CAGR | Vola p.a. | Sharpe | Max Drawdown | positive Monate | Monate |
|---|---|---|---|---|---|---|---|
| 5 | ja | 49.1% | 37.9% | 1.24 | -53.2% | 65% | 246 |
| 5 | nein | 46.6% | 38.6% | 1.18 | -63.4% | 65% | 246 |
| 10 | ja | 36.2% | 32.0% | 1.12 | -52.2% | 65% | 246 |
| 10 | nein | 36.1% | 32.5% | 1.11 | -59.4% | 65% | 246 |
| 20 | ja | 28.1% | 25.9% | 1.09 | -50.3% | 65% | 246 |
| 20 | nein | 27.2% | 26.9% | 1.03 | -57.6% | 67% | 246 |

## Vergleich Kaufen und Halten

| Wert | CAGR | Vola p.a. | Sharpe | Max Drawdown |
|---|---|---|---|---|
| spy | 11.1% | 14.8% | 0.79 | -50.8% |
| qqq | 15.5% | 18.4% | 0.88 | -49.7% |
| gld | 11.1% | 17.3% | 0.70 | -42.9% |

## Verzerrungen, die dieses Ergebnis nach oben ziehen

- Survivorship Bias: Das Universum enthaelt die heutigen Indexmitglieder. Firmen, die pleite gingen oder aus dem Index flogen, fehlen. Das schoent jede Rueckrechnung, teils deutlich.
- Look ahead auf Universumsebene: Die Auswahl der Werte kennt die Gegenwart, die Regel selbst nicht.
- Gerechnet wird auf dividendenbereinigten Kursen von Yahoo. Dividenden gelten damit als sofort wieder angelegt, ohne Steuerabzug. Real faellt auf Ausschuettungen Steuer an, die Rueckrechnung liegt dadurch ueber der erreichbaren Rendite.
- Preisindizes wie der DAX Kursindex und Rohstofffutures kennen keine Dividende. Ein Vergleich zwischen Klassen hinkt deshalb systematisch.
- Steuern, Spreads und Slippage sind ausser den pauschalen Kosten nicht modelliert.
- Mehrere Varianten auf denselben Daten getestet heisst: die beste Variante ist teilweise Zufall. Ein Vorsprung von wenigen Zehntel im Sharpe ist kein Beweis.

Konsequenz: Diese Zahlen taugen als Plausibilitaetspruefung der Regel, nicht als Renditeversprechen. Der eigentliche Test ist der Vorwaertslauf ab heute.