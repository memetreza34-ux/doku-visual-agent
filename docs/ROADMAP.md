# Roadmap – Qualität vor Automation

## Abgeschlossen im Grundgerüst (Phase 1A)

- CLI / Module / offline Demo / CI
- Deutsche Absatz-Szenen + einfache kategoriebasierte Suchplanung
- Pexels Photo-/Video-API; Commons Bild-/Rechtemetadaten
- Treffer-Reihenfolge anhand Textmetadaten; grober Entity/Ort/Jahr-Filter
- Keine automatische Freigabe, keine unprotokollierten Fallbacks
- Sichtungsboard mit Originalquellen; dokumentierbare manuelle Freigaben

## Nächste Umsetzung (Phase 1B, noch offen)

- Aktuelle Fakten recherchieren und mit offiziellen Quellen/Datumsangaben belegen
- Szenensemantik mit LLM und strukturiertem JSON-Schema; regelbasierter Fallback
- Visuelle Bildinhaltsanalyse der Kandidaten (Vision-Modell)
- Abgleich von visueller Beschreibung gegen genaue Sprecher-Aussage
- Frühzeitig Duplikate (pHash) filtern; Bildqualität messen
- Snapshot/Hash von Lizenzen und Quellinformationen für Audit
- Authentische Belege stärker bewerten als bloßes Stock-B-Roll
- Bewertung mit annotiertem Goldstandard aus echten Pilotvideos

## Danach (Phase 2)

- Audio-/Skript-Timestamps, Sprecher-Synchronisierung
- Storyboard je Aussage und visuelle Abwechslung
- Infografiken aus belegten Zahlen, mit Quellenangabe
- Renderpipeline, Export und Qualitätskontrolle
- Keine Veröffentlichung ohne Freigabegates

## Später (Phase 3)

- Kontinuierliches Lernen aus Korrekturen, ohne blindes Umschreiben von Regeln
- Qualitäts-Dashboard / Kosten / Performance / Rechtejournal
- Cross-Video-Asset-Bibliothek mit Herkunft, Lizenz und Duplikaterkennung
