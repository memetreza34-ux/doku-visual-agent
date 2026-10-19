# Doku Visual Agent

**Phase 1: überprüfbare Bild- und B-Roll-Recherche für deutschsprachige Wissens-Dokus.**

Das Projekt baut zunächst **keinen beliebigen Auto-Video-Generator**. Es zerlegt ein Skript in Szenen, sucht über offizielle APIs nach realen Fotos und Stockvideos, bewertet die **Metadatenrelevanz**, erstellt einen anschaulichen Sichtungsbericht und hält ungeprüftes Material zurück.

## Funktionsstand

| Funktion | Stand |
| --- | --- |
| Deutsches Skript in Absätze/Szenen zerlegen | Implementiert |
| Visualtyp unterscheiden (Daten, Archiv, konkreter Ort, Symbolbild, Nachrichten) | Regelbasiertes MVP |
| Pexels Fotos + Videos suchen | Live über PEXELS_API_KEY |
| Wikimedia Commons Bilder und Lizenzmetadaten suchen | Live ohne API-Schlüssel |
| Kandidaten sortieren, Duplikate reduzieren, Quellen bewahren | Implementiert; Metadatenbewertung, **keine** Bildinhaltserkennung |
| Offline-Demo und automatisierte Tests | Implementiert |
| Visueller HTML-Review-Bericht | Implementiert |
| Manuelle dokumentierte Freigabe von Assets | Implementiert |
| Vollautomatische Tatsachenprüfung, KI-Vision, fertiger Videoschnitt | **Noch nicht implementiert** |

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

## 3. Visuals prüfen und freigeben

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

## Entwicklungsstatus

Dies ist bewusst ein **testbares Phase-1-MVP**, noch kein Endprodukt und kein bewiesenes 90-%-Automationssystem. Als nächstes folgen KI-gestützte Satzplanung und echte Bildinhaltsprüfung, bevor wir einen automatischen Videoschnitt anbinden.
