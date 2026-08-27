# Don Elias Aktien Agent, Datensammler

Dieses Repository sammelt jeden Tag automatisch Kurse fuer Aktien, ETFs,
Rohstoffe und Krypto, rechnet daraus Kennzahlen und legt die Ergebnisse als
CSV, JSON und Markdown ab. Der KI Agent in Claude liest diese Dateien
anschliessend, bewertet die Lage und schickt den Tagesreport per Mail.

Die Arbeitsteilung ist bewusst so geschnitten:

| Teil | Wer | Warum |
|---|---|---|
| Kurse holen | GitHub Actions | Hat freien Netzzugang, laeuft auch wenn kein Rechner an ist |
| Kennzahlen rechnen | Python in diesem Repo | Deterministisch, jede Zahl nachrechenbar |
| Einordnung, Report, Mail | Claude | Sprache, Kontext, Auffaelligkeiten |

## Einrichtung in sechs Schritten

1. Neues Repository auf GitHub anlegen, Name zum Beispiel `aktien-agent`.
   Sichtbarkeit **public**, dann sind die Actions Minuten unbegrenzt und die
   Daten koennen ohne Token gelesen werden. Es landen keine persoenlichen
   Daten in diesem Repo.
2. Alle Dateien aus diesem Ordner hochladen. Im Browser geht das per
   "Add file", "Upload files", danach den gesamten Ordnerinhalt hineinziehen.
3. Reiter **Actions** oeffnen und die Workflows aktivieren, falls GitHub
   danach fragt.
4. Unter **Settings**, **Actions**, **General**, ganz unten bei
   "Workflow permissions" auf **Read and write permissions** stellen.
   Ohne das darf der Workflow die Ergebnisse nicht zurueckschreiben.
5. Ersten Lauf starten: **Actions**, "Taeglicher Datenlauf", **Run workflow**,
   dabei `full_history` auf **true** setzen. Dieser Lauf dauert am laengsten,
   weil er die komplette Historie holt.
6. Danach laeuft der Zeitplan taeglich um 04:30 UTC von allein.

Optional: Ein kostenloser CoinGecko Demo Schluessel macht die Kryptoabrufe
stabiler. Falls vorhanden, unter **Settings**, **Secrets and variables**,
**Actions** als `COINGECKO_API_KEY` hinterlegen. Ohne Schluessel funktioniert
es ebenfalls, nur langsamer gedrosselt.

## Was der Agent liest

| Datei | Inhalt |
|---|---|
| `data/latest_signals.json` | Ranglisten, Marktbreite, Diagnose des letzten Laufs |
| `data/snapshots/<datum>.csv` | Alle Kennzahlen aller Werte an einem Tag |
| `data/history/<symbol>.csv` | Fortlaufende Kurshistorie je Wert |
| `data/run_log.csv` | Protokoll jedes Laufs mit Fehlerzahl |
| `reports/latest.md` | Lesbarer Kurzreport |
| `reports/backtest.md` | Ergebnis der Rueckrechnung inklusive Verzerrungen |

Rohzugriff ohne Token, Beispiel:
`https://raw.githubusercontent.com/<nutzer>/<repo>/main/data/latest_signals.json`

## Backtest

Der Backtest laeuft nicht taeglich, sondern auf Knopfdruck:
**Actions**, "Backtest", **Run workflow**. Voraussetzung ist ein
abgeschlossener Lauf mit `full_history`, weil er die Historien aus
`data/history/` verwendet.

Getestet wird eine offen dokumentierte Regel: monatliche Umschichtung in die
Top N nach Momentum ueber zwoelf Monate ohne den letzten Monat, wahlweise mit
Trendfilter ueber dem 200 Tage Durchschnitt, gleichgewichtet, mit pauschalen
Handelskosten.

Der erzeugte Report benennt die Verzerrungen selbst, unter anderem
Survivorship Bias und fehlende Dividenden. Die Zahlen sind eine
Plausibilitaetspruefung, kein Renditeversprechen.

## Bekannte Grenzen

- Tagesschlusskurse, keine Echtzeitdaten.
- stooq und CoinGecko sind kostenlose Quellen ohne Verfuegbarkeitszusage.
  Einzelne Symbole koennen ausfallen. Jeder Report weist die Ausfaelle aus,
  statt sie zu verschweigen.
- Deutsche Symbole bei stooq sind nicht fuer jeden DAX Wert vorhanden. Die
  Fehlerliste des ersten Laufs zeigt, welche gestrichen werden muessen.
- GitHub deaktiviert geplante Workflows nach 60 Tagen ohne Repository
  Aktivitaet und verschickt vorher eine Mail. Ein manueller Commit oder ein
  Klick auf "Run workflow" reaktiviert sie.
- Geplante Laeufe starten bei hoher Last auf GitHub teils mit Verzoegerung.

## Kein Anlageberatung

Dieses Repository erzeugt Statistik. Es gibt keine Kauf oder Verkaufsempfehlung
ab, kennt weder deine Vermoegenslage noch deinen Anlagehorizont und ersetzt
keine Beratung.

## Lokal testen ohne Netz

```
pip install -r requirements.txt
python -m tests.test_offline
```

Der Test ersetzt die Kursabrufe durch erzeugte Zufallskurse und prueft die
gesamte Kette bis zum Backtest.
