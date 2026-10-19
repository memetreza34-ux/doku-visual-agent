# Roadmap – Qualität vor Automation

## Abgeschlossen im Grundgerüst (Phase 1A)

- CLI / Module / offline Demo / CI
- Deutsche Absatz-Szenen + einfache kategoriebasierte Suchplanung
- Pexels Photo-/Video-API; Commons Bild-/Rechtemetadaten
- Treffer-Reihenfolge anhand Textmetadaten; grober Entity/Ort/Jahr-Filter
- Keine automatische Freigabe, keine unprotokollierten Fallbacks
- Sichtungsboard mit Originalquellen; dokumentierbare manuelle Freigaben

## Phase 1B – technische Integration, noch keine Live-Abnahme

- **Offen:** Aktuelle Fakten recherchieren und mit offiziellen Quellen/Datumsangaben belegen
- **Implementiert:** Opt-in Gemini-Suchsemantik mit strukturiertem JSON und regelbasiertem Fallback
- **Implementiert:** Opt-in Gemini-Vorschaubildanalyse, nur für geprüfte CDN-Domains
- **Implementiert:** Szenenabgleich mit nachvollziehbarem KI-Urteil, ohne Quelle/Identität zu behaupten
- Frühzeitig Duplikate (pHash) filtern; Bildqualität messen
- Snapshot/Hash von Lizenzen und Quellinformationen für Audit
- Authentische Belege stärker bewerten als bloßes Stock-B-Roll
- **Teilweise:** 24 kuratierte Skriptszenen sowie Vision-Tests mit Mock-Antworten. **Offen:** reale Bilder bewerten und unabhängige Präzisionsmessung

## Phase 2A: implementierter Renderpfad (Pilot noch offen)

- Python-Timelinegenerator: aus plan.json, Freigaben, lokalen Assets und Sprecherdatei ein Remotion-Paket.
- Integritäts- und Lizenzfreigabe-Gates für jedes Bild / jeden Clip, kein blindes Einfügen fremder Dateien.
- Für belegte Daten-Szenen: Diagramm aus explizit geprüften Zahlen.
- Erste React/Remotion-Komposition: Bewegung, Quellenhinweise, Szenenübergänge, Voiceover-Mix.
- Demo-Modus mit sichtbarem Kennzeichen; Bildinhalt aus echten Quellen dabei nicht vorgetäuscht.
- Offen: vollautomatische Faktensuche, Skripte, TTS, Wort-Timing und Live-Videoschnittqualität.

## Danach (Phase 2B)


- Audio-/Skript-Timestamps, Sprecher-Synchronisierung
- Storyboard je Aussage und visuelle Abwechslung
- Infografiken aus belegten Zahlen, mit Quellenangabe
- Renderpipeline, Export und Qualitätskontrolle
- Keine Veröffentlichung ohne Freigabegates

## Später (Phase 3)

- Kontinuierliches Lernen aus Korrekturen, ohne blindes Umschreiben von Regeln
- Qualitäts-Dashboard / Kosten / Performance / Rechtejournal
- Cross-Video-Asset-Bibliothek mit Herkunft, Lizenz und Duplikaterkennung
