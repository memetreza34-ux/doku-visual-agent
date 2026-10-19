# Volkswagen-Pilot – Wolfsburger Werk 1938 bis 2025

## Story-Winkel

**Volkswagen: Vom Käfer zum Werk der Gegenwart** – keine ungesicherten aktuellen Meldungen oder internen VW-Ereignisse. Ziel: Echte passende Bilder mit Narration statt schöner, thematisch beliebiger Stock-Motive.

## Geprüfte Referenzseiten für den Entwurf

Fakten (1938 Baubeginn, Serienstart Käfer 1945, Golf ab 1974, Areal rund 6,5 km²): https://www.volkswagen-newsroom.com/en/wolfsburg-plant-the-heart-of-the-vw-brand-6811

Vier dokumentarische Aufnahmen, deren Commons-Seiten Urheber und Lizenz angeben:
1. [Wolfsburg Volkswagen Plant.jpg](https://commons.wikimedia.org/wiki/File:Wolfsburg_Volkswagen_Plant.jpg) – Jorge Franganillo, 2025, CC BY 4.0.
2. [Wolfsburg - Inside the Volkswagen Plant.jpg](https://commons.wikimedia.org/wiki/File:Wolfsburg_-_Inside_the_Volkswagen_Plant.jpg) – Roger Wollstadt, 7.10.1960, CC BY-SA 2.0.
3. [Wolfsburg - Volkswagen Assembly Line.jpg](https://commons.wikimedia.org/wiki/File:Wolfsburg_-_Volkswagen_Assembly_Line.jpg) – Roger Wollstadt, 4.10.1960, CC BY-SA 2.0.
4. [Aerial image of the Wolfsburg Volkswagen Plant (view from the southeast).jpg](https://commons.wikimedia.org/wiki/File:Aerial_image_of_the_Wolfsburg_Volkswagen_Plant_(view_from_the_southeast).jpg) – Carsten Steger, 20.08.2024, CC BY-SA 4.0.

Die Originalseiten nennen Kamerajahr, Urheber und Lizenz. Unser CLI prüft bei Abruf automatisch die *gemeldeten* Lizenzfelder und den Urheber gegen die Shotlist – es garantiert nicht die rechtliche Durchsetzbarkeit einer Lizenz.

### Optionale natürliche Sprecherstimme (Gemini TTS)

Für eine natürlichere Teststimme lässt sich statt `espeak-ng` die offizielle Gemini-TTS-API verwenden. Dafür ist ein eigener API-Schlüssel nötig; die Nutzung kann Kosten verursachen. Ein Skript bleibt exakt die Textvorlage, aber eine hörbare Qualitäts-/Wortlautkontrolle ist trotzdem Pflicht.

```bash
export GEMINI_API_KEY="DEIN_KEY"
python -m doku_visual_agent tts-gemini --script runs/pilot/narration.txt --output runs/pilot/narration.wav --voice Kore
```

Das Modul verwendet `gemini-3.8-flash-tts` über Googles dokumentierte Interactions-API und akzeptiert nur gültige WAV-Dateien. Ohne Schlüssel bleibt der kostenlose, aber deutlich weniger natürliche `espeak-ng`-Test nutzbar. Die laufenden GitHub-Actions-Tests geben bewusst kein Geld für Gemini aus.

## Technischer Ablauf

1. `pilot-script`: Lesbare Sprecherdatei `narration.txt` aus `examples/vw_wolfsburg_pilot.json`.
2. `espeak-ng`: rein technische **deutsche Robotik-Teststimme**, keine professionelle KI-Stimme.
3. `pilot-prepare`: Wikimedia-API über exakte `File:`-Titel, Prüfung von Lizenz, Urheber und CDN, Download der 1600px-Bildversionen. Nur ausgewählte, explizit kuratierte Titel, kein willkürliches Web-Scraping.
4. Wortanzahl-basierte Szenendauern (keine Wort-Synchronität), Bild-Zooms + beschriftete Zeitstrahlgrafiken in Remotion.
5. MP4 technisch über `ffprobe` prüfen, Quellenjournal und Pilotvideo als GitHub-Actions-Artefakt (7 Tage) bereitstellen.

### Sicherheit / Qualitätslücken

- **Nicht veröffentlichen.** Rechte (Namensnennung, Lizenzlink, Bearbeitung, ShareAlike, Personen/Marken) vor Veröffentlichung vollständig prüfen und umsetzen. Das Video hat explizit `publication_ready=false`.
- Historische Angaben gelten nur für den redaktionellen Entwurf und müssen nochmals mit Originalquellen gegengeprüft werden.
- Audiotiming wird nach Wortanzahl approximiert, keine WhisperX-Unterteilung; technisch billige Stimme dient ausschließlich dem Integrationstest.
- Es gibt noch **kein** echtes lizenzsicheres Video-B-Roll im Pilot. Das muss später ergänzend geprüft werden.
- Keine eigenständige journalistische Newsrecherche (VW-Krisen, Stellenabbau etc.) im Pilot.
- Externe API oder CDN kann ausfallen; **keine** heimliche Substitution von synthetischen Bildern. Fehler muss sichtbar bleiben.
- Bilder können trotz passender Dateiüberschrift inhaltlich abweichen; die Videoqualität ist über eine manuelle Sichtung zu bewerten.
- Ein akzeptiertes Common-Bild ist **nicht automatisch** rechtlich für YouTube-Monetarisierung freigegeben.

## Quality Gate vor Ausbau

Echter Render und nachgewiesene Streams, vier eindeutige reale Fotodateien, Originalseiten+Lizenzmetadaten+SHA256, keine unpassenden Firmenbilder, klar markierte Demo, keine erfundenen aktuellen Ereignisse; danach tatsächliche Bild-/Schnitt- und Lizenzkontrolle. Erst anschließend hochwertigen TTS, Animationstuning, B-Rolls und vollständiges Autoformat entwickeln.

## Visuelles Review

Nach `pilot-prepare` liegt `runs/pilot/render/review.html` vor. Es zeigt jede echte Bildvorschau neben Sprechertext, Fotograf, Lizenz und Faktenquellen. Die Datei und vier Bilder werden dem GitHub-Actions-Artefakt beigelegt. Damit lässt sich **jede Szene** vor dem Upload beurteilen; das Review schaltet die Veröffentlichung nicht automatisch frei.
