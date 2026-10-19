# Doku Visual Agent

**Phase 1: überprüfbare Bild- und B-Roll-Recherche für deutschsprachige Wissens-Dokus.**

Das Projekt baut zunächst **keinen beliebigen Auto-Video-Generator**. Es zerlegt ein Skript in Szenen, sucht über offizielle APIs nach realen Fotos und Stockvideos, bewertet die **Metadatenrelevanz** und optional echte **Bildvorschauen mit Gemini**, erstellt einen anschaulichen Sichtungsbericht und hält ungeprüftes Material zurück.

## Funktionsstand

| Funktion | Stand |
| --- | --- |
| Deutsches Skript in Absätze/Szenen zerlegen | Implementiert |
| Visualtyp unterscheiden (Daten, Archiv, konkreter Ort, Symbolbild, Nachrichten) | Regelbasiertes MVP |
| Pexels Fotos + Videos suchen | Live über PEXELS_API_KEY |
| Wikimedia Commons Bilder und Lizenzmetadaten suchen | Live ohne API-Schlüssel |
| Kandidaten sortieren, Duplikate reduzieren, Quellen bewahren | Implementiert (Metadaten) |
| Tatsächliche Bildvorschau mit Gemini einschätzen | Optional, mit API-Key, noch kein unabhängiger Qualitätstest |
| KI-Semantik für Suchbegriffe | Optional, regelbasierter Fallback |
| KI-Fehlmatches markieren und für Freigabe sperren | Implementiert (kein Autopublish) |
| Offline-Demo und automatisierte Tests | Implementiert |
| Visueller HTML-Review-Bericht | Implementiert |
| Manuelle dokumentierte Freigabe von Assets | Implementiert |
| Vollautomatische Tatsachenprüfung und fertiger Videoschnitt | **Noch nicht implementiert** |

**Wichtig:** Ein Treffer ist kein nachgewiesener Bildinhalt. Eine Plattformlizenz garantiert nicht, dass abgebildete Personen, Marken oder Orte für jeden Kontext freigegeben sind. Die Pipeline lädt keine Videos herunter, behauptet keine Nutzungsrechte und veröffentlicht nichts selbstständig.

## Installation

Benötigt Python 3.11+.

```bash
git clone https://github.com/memetreza34-ux/doku-visual-agent.git
cd doku-visual-agent
python -m pip install -e .
python -m unittest discover -s tests -v
```

## 1. Offline testen – ohne API-Schlüssel

```bash
python -m doku_visual_agent plan --script examples/volkswagen_60s.txt \
  --fixture examples/demo_assets.json --output runs/vw-demo
```

Die Beispieldatei enthält **künstliche Testdaten, keine echten Bildnachweise**. Ausgegeben werden:

- `runs/vw-demo/plan.json`: strukturierte Szenen, Suchbegriffe, Kandidaten, Quellen, Warnungen
- `runs/vw-demo/review.html`: visuelle Vorschau, Begründung, Lizenzhinweise

## 2. Live recherchieren

Erstelle einen Pexels-API-Schlüssel: https://www.pexels.com/api/

```bash
export PEXELS_API_KEY="DEIN_KEY"
python -m doku_visual_agent plan --script examples/volkswagen_60s.txt \
  --output runs/vw-live
```

Ohne Pexels-Schlüssel funktioniert die Wikimedia-Suche weiterhin. Ein optionaler API-Fehler wird im Bericht sichtbar dokumentiert. Pexels liefert Stockmaterial, **nicht automatisch echte Aufnahmen eines bestimmten VW-Ereignisses**.

Auf jeder API-basierten Pexels-Recherche und in der Review-Ansicht findet sich ein Link zur Quelle. Offizielle Dokumentation: https://www.pexels.com/api/documentation/ und https://www.mediawiki.org/wiki/API:Imageinfo .

## 3. KI-gestützte Suchplanung und visuelle Bildprüfung (Phase 1B)

**Opt-in**: Gemini kann Suchbegriffe anhand des Sprechersatzes verbessern (`--semantic`) und **reale Vorschaubilder** auf optische Passung prüfen (`--vision`). Für Videos wird nur ein Preview-Frame geprüft, keine vollständige Clipanalyse.

Du benötigst dafür einen optionalen Gemini-API-Key: https://aistudio.google.com/apikey . Kosten und verfügbare Modelle selbst prüfen.

```bash
export GEMINI_API_KEY="DEIN_API_KEY"
export PEXELS_API_KEY="DEIN_PEXELS_KEY"
python -m doku_visual_agent plan --script examples/volkswagen_60s.txt --output runs/vw-vision --semantic --vision --vision-per-scene 2 --max-vision-total 20
```

- `--vision-per-scene 2` begrenzt Bildprüfungen auf 2 je Szene (1–6). `--max-vision-total 20` begrenzt zusätzlich den gesamten Durchlauf (1–100). Jede Anfrage kann Kosten verursachen.
- Die Offline-Demo verwendet künstliche Datensätze und **kann nicht** als echte Visionprüfung verwendet werden.
- Die Bildprüfung stuft optisch irrelevante Treffer als `unrelated` ein. Diese können nicht normal freigegeben werden.
- Alle anderen Bilder bleiben **redaktionell und lizenzrechtlich zu prüfen**. Ein KI-Bildurteil beweist niemals die Echtheit eines spezifischen Unternehmensstandorts, eines Ereignisses oder ein Nutzungsrecht.
- Aktivierte Vision sendet Bildvorschauen an die Gemini-API. Externe Bilder werden nur von freigegebenen Pexels-/Wikimedia-Domains geladen.

Siehe [Technik und Qualitätsgrenzen](docs/PHASE_1B.md).

## 4. Visuals prüfen und freigeben

Ein Mensch muss für jedes vorgeschlagene Asset die tatsächliche Bildaussage, den Ursprung, die Rechte und ggf. Einwilligungen prüfen. Es gibt **keine automatische Freigabe**.

```bash
python -m doku_visual_agent approve --run runs/vw-live \
  --scene S01 --asset "commons:BEISPIEL-ID" \
  --role exakt \
  --license-evidence "CC BY-SA 4.0, Urheber und Bedingungen auf Dateiseite geprüft" \
  --visual-evidence "Werk und Aufnahmeort anhand Bild und Dateibeschreibung geprüft"
```

Die Freigaben liegen getrennt in `approvals.json`. Für Symbolbilder ist `--role symbolbild` zu verwenden; bei Ereignissen oder konkreten Orten ersetzt ein Symbolbild **niemals** einen Originalbeleg. Freigaben für die Offline-Demo sind gesperrt.

## Qualitätsregeln

1. **Aussagenbezug vor Optik.** Keine beliebige Fabrikaufnahme als Beweis für Vorgänge bei Volkswagen.
2. **Daten brauchen Belege.** Für Zahlen-Szenen werden Diagramme als *noch zu recherchierende Aufgabe* geplant, keine Zahlen erfunden.
3. **Unklare Rechte = keine Freigabe.** Auch CC-Lizenzen können Bedingungen enthalten.
4. **Quelle pro Asset.** Landingpage, Fotograf und Lizenz soweit verfügbar.
5. **Unsicherheit sichtbar.** Metadatentreffer sind keine visuelle oder redaktionelle Verifizierung.
6. **Keine Duplikate und keine stillen Fallbacks.** Wenn nichts passt, markiert der Report die Lücke.

Siehe [QUALITÄT.md](docs/QUALITAET.md) und [ROADMAP.md](docs/ROADMAP.md).

## Datenschutz und Kosten

Das Skript wird in der Live-Suche ausschließlich zur Ableitung von Suchanfragen verwendet. Suchbegriffe gehen an die gewählten externen Dienste. Keine API-Schlüssel ins Repository committen. Den `runs/`-Ordner nicht einchecken; er kann Recherche- und Projektinformationen enthalten.

Pexels hat API-Limits und Richtlinien zur Nutzung. Wikimedia Commons ist keine pauschale kommerzielle Freigabe. Prüfe die Bedingungen jeweils aktuell.


## Phase 2A: Gesteuerter Remotion-Videoexport

Nach der Bildprüfung kann die Pipeline nun eine JSON-Timeline und ein geprüftes Medienpaket für Remotion vorbereiten. Sie synchronisiert die Gesamtdauer des Sprecher-Audios mit den Szenen und erstellt aus freigegebenen Fotos, Clips und belegten Diagrammen eine Video-Timeline. Eine **zuverlässige Wort-Synchronisation** oder automatische KI-Stimme gibt es noch nicht.

### Sichere grafische Demo ohne fremde Medien

~~~bash
python -m doku_visual_agent plan --script examples/volkswagen_60s.txt --fixture examples/demo_assets.json --output runs/demo
python -m doku_visual_agent prepare-render --run runs/demo --output runs/demo/render --demo
cd remotion
npm install
npx remotion render src/index.jsx DokuVideo ../runs/demo/DEMO.mp4 --props ../runs/demo/render/props.json --public-dir ../runs/demo/render/public
~~~

Das Ergebnis ist eine **sichtbar als Demo markierte, stumme Layoutvorschau**. Es zeigt keine recherchierten VW-Fotos und enthält keinen KI-Sprecher.

Für reale Videos sind manuell freigegebene Bilddateien, bindings.json, eine Sprecherdatei und ggf. geprüfte Diagramme nötig. Die Pipeline blockiert fehlende Rechte-/Quellenfreigaben und fehlende Medien. Weitere Informationen: [Phase 2A Anleitung](docs/PHASE_2A.md).

**Offen:** aktuelle Quellenrecherche und Faktensicherheit, eigenständige Skripterstellung, automatische TTS, präzise Sprach-Timestamps, echter Qualitätsbenchmark, 5-10-Minuten-Doku-Praxistest.

## Entwicklungsstatus

Phase 1B enthält KI-Szenenplanung und die Sichtung einzelner realer Vorschaubilder. Die Implementierung wird mit gemockten Tests geprüft, **nicht** mit einer noch ausstehenden unabhängigen Live-Bildgenauigkeitsmessung. Faktenrecherche und fertiger Videoschnitt folgen erst nach dem Volkswagen-Pilotprojekt.
