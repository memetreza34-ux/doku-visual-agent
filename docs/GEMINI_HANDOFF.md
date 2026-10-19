# GEMINI – Entwicklungsübergabe für Doku Visual Agent

> Anweisung für einen KI-Coding-Agenten mit Zugriff auf dieses GitHub-Repository.
> Nur die tatsächlichen implementierten Funktionen als erledigt markieren.
> **Nicht veröffentlichen**: Rechts- und Bildinhalt-Freigaben fehlen weiterhin.

## Projekt

Repository: https://github.com/memetreza34-ux/doku-visual-agent

Ziel: Deutsche, professionell gestaltete, faktenbasierte Dokumentationen über Firmen, Technik und Wirtschaft. **Echte passende dokumentarische Bilder** stehen vor schönen, aber falschen Motiven. Das fertige Produkt soll später nach Eingabe eines Themas Recherche, Skript, echte Bild-/B-Roll-Beschaffung, Sprecherstimme, Diagramme, Remotion, QA und Export unterstützen.

### Vorhandener Stand (Code, nicht Produkt-Fertigmeldung)

- Python CLI: \`plan\`, \`approve\`, \`draft-script\`, \`prepare-render\`, \`pilot-script\`, \`pilot-prepare\`, \`tts-gemini\`.
- Quellen-Adapter: Wikimedia Commons und Pexels; opt-in KI-Vision + semantische Suchbegriffe über Gemini.
- \`remotion/src/index.jsx\`: 1920×1080 Szenen-Renderer mit Bildbewegungen, B-Roll, Diagrammen, Voiceover, Beschriftungen, Demo-Markierung.
- \`examples/vw_wolfsburg_pilot.json\`: historische 6-Szenen-Storyboardprobe mit 4 Commons-Aufnahmen und 2 Grafiken.
- Freigabegates vor echtem Render, Bilder- und Lizenzjournal, Tests Python 3.11–3.13.
- GitHub Actions prüft Python, ein kurzes echtes Remotion-MP4 sowie einen vollständigen realen Foto-Pilot mit technischer eSpeak-Stimme. **Immer tatsächlichen Laufstatus prüfen**; CI kann auch an externer API/Datei scheitern.

## Deine Prioritäten in fester Reihenfolge

1. **Pilot CI nachhaltig stabilisieren und tatsächliches MP4 prüfen.** GitHub Actions prüfen, Logs lesen, echte Fehler beheben. Keine unpassenden Fotos als Ersatz einsetzen. Ergebnis muss Video **und** Audio enthalten. Die Bilder und ihr Quellnachweis müssen im Artefakt sein. Keine Behauptung „fertig“, wenn es nur Unit-Tests sind.
2. **Jede einzelne Szene mit echten Visuals prüfen.** Zu Skript, konkretem Jahr, Firma, Ort und Quelle. Keine Stockaufnahmen als VW-Ereignismaterial ausgeben. Bewertungsmatrix pro Szene (Inhalt, Bildästhetik, Quellen, Rechte). Fehler mit reproduzierbarem Test dauerhaft abfangen.
3. **Professionelle Sprecherstimme:** \`tts-gemini\` mit separat gesetztem \`GEMINI_API_KEY\`. Keine Keys in Code/Commits, keine unnötigen kostenpflichtigen Testschleifen. Das Ergebnis anhören, exakten Sprechertext abgleichen, natürliches Deutsch anstreben.
4. **Zeitgenauigkeit:** Automatische Wort-/Absatz-Timestamps aus Audio statt nur Verhältnis nach Wortanzahl; verifizierter Szenenwechsel zur jeweiligen Aussage. Untertitel müssen synchron sein.
5. **Doku-reife Recherche:** Quellengebundene Unternehmens-/Nachrichtenrecherche mit Datumsstempel, Originalquellen, Zahlenprüfung und konkreten Visualwünschen. Keine Behauptung ohne Nachweis.
6. **Video-Visuals:** Hochwertige, lizenzierte tatsächliche Clips (nicht nur ein einzelnes Video-Thumbnail); bei fehlendem Ereignismaterial korrekte Kennzeichnung als Symbolbild. Echte Karten/Infografiken/Diagramme aus belegten Zahlen.
7. **Qualitätsschleife:** Render ansehen/hören, Fehlerprotokoll schreiben, Root Cause im Repo dauerhaft reparieren, erneut testen, keine Duplikate, kein überflüssiger visueller Füllstoff. Originaltreue vor Menge.
8. **Produktionsreife:** 60-Sekunden-Realtest bestehen, dann 4–10-Minuten-Doku mit 1080p, Quellen-Credits, gutem Voiceover, sauberem Thumbnail und Caption exportieren. Nicht vor erfolgreicher Fakten-/Rechteprüfung publizieren.

## Ausführung: Pilot ohne API-Schlüssel

~~~bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m doku_visual_agent pilot-script --manifest examples/vw_wolfsburg_pilot.json --output runs/pilot
espeak-ng -v de -s 153 -f runs/pilot/narration.txt -w runs/pilot/narration.wav
python -m doku_visual_agent pilot-prepare --manifest examples/vw_wolfsburg_pilot.json --voiceover runs/pilot/narration.wav --output runs/pilot/render
cd remotion
npm install
npx remotion render src/index.jsx DokuVideo ../runs/pilot/VW-PILOT-NICHT-VEROEFFENTLICHEN.mp4 --props ../runs/pilot/render/props.json --public-dir ../runs/pilot/render/public --scale 0.5
~~~

Für natürliche TTS lokal (optional, nach Zustimmung zu API-Kosten):
~~~bash
export GEMINI_API_KEY="..."
python -m doku_visual_agent tts-gemini --script runs/pilot/narration.txt --output runs/pilot/narration.wav --voice Kore
~~~

**Niemals** eine echte API-Key-Zeichenfolge in Antworten, Logs, PRs oder Commits schreiben. Das Rendering bleibt nach \`pilot-prepare\` ausdrücklich \`publication_ready=false\`.

## Ausgabekonvention

- Entwicklung in GitHub-Branch + PR, keine ungeprüften Änderungen nach \`main\`.
- PR-Beschreibung: Implementiert / Testbefund / aktueller End-to-End-Status / offene Qualitätslücken.
- Exportprojekt: Video, Cover, Caption (Titel, Beschreibung, 5 Hashtags), geprüfte Credits, Script mit Timestamps, Qualitätsreport. Im endgültigen Exportordner keine unnötigen Doppelordner.
- Chat-Antwort nach Phase 1: **Link zum Bildprompt bzw. zur Bildrecherche** und **Link zur Skriptdatei** nennen.
- Kontinuierliche Verbesserung hat oberste Priorität. CI-grüne Unit-Tests ersetzen keine inhaltliche Bildprüfung.

## Übergabekriterien

Die Arbeit ist *nicht* fertig, solange eine der folgenden Bedingungen gilt:
- Vollständiger Pilot wurde nie tatsächlich als MP4 mit Audio gerendert und angesehen.
- Bild zeigt nicht das, was der Satz behauptet; Quellen-/Lizenzlage unklar.
- Sprecher-/Visual-Timing ist falsch.
- Aktuelle Wirtschaftsfakten sind unbestätigt, Zahlen fehlen Originalquelle.
- Finalvideo wurde nie auf Schnitte, doppelte Szenen, Untertitel, Copyright und Bildinhalt geprüft.

Bei Blockern (API-Key, externe Rechte, fehlende Medien) die Lücke ausdrücklich benennen, sicheren Fallback nutzen und alle anderen umsetzbaren Verbesserungen zuerst erledigen.
