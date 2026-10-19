# Phase 1B – Visual-Semantik, Bildsicht und Sicherheitsgrenzen

## Ablauf

1. **Skript verstehen:** Bestehende strenge Visualkategorien und Firmennamen/Orte/Jahre bleiben aus der lokalen Klassifikation. Mit `--semantic` optimiert Gemini Suchbegriffe und erklärt die gewünschte Darstellung. Fehlende oder fehlerhafte KI-Antworten führen zurück zum konservativen Regelwerk.
2. **Quellen suchen:** Stock-B-Roll aus Pexels für allgemeine Szenen, Commons für konkrete dokumentarische Quellen; kein Scraping beliebiger fremder Websites.
3. **Visuelle Triage:** Mit `--vision` werden echte Bildvorschauen (nicht Dateinamen allein) an Gemini gesendet. Resultat: `relevant`, `partly_relevant`, `unrelated`, `uncertain`, `error`, `not_checked`. Unpassende Treffer werden für Freigabe gesperrt.
4. **Redaktionelle Abnahme:** **Nie** automatische Publikation oder Lizenz-Freigabe. Standort, Zeit, Personen, Marke, Ereignis und Nutzungsrecht sind unabhängig zu prüfen.

## Schutzmaßnahmen

- Gemini-Modell standardmäßig `gemini-2.5-flash`, konfigurierbar mit `--gemini-model`.
- Nur mit gesetztem lokalem `GEMINI_API_KEY`; kein API-Key im Repo, Bericht oder Query-URL.
- Maximal 1–6 Bilder pro Szene (Standard 3), maximal 3 MB Vorschaubild; ausschließlich JPEG, PNG, WebP mit passender Dateisignatur.
- HTTPS, Host-Allowlist `images.pexels.com` oder `upload.wikimedia.org`; Redirects an andere Hosts sowie nicht standardmäßige Ports blockiert.
- Modell- und Transportfehler werden sichtbar angezeigt, sie erzeugen nie ein grünes Publikationssignal.
- Bildvorschauen können Daten Dritter enthalten: Bei `--vision` werden sie zum KI-Anbieter übertragen.
- Video-Vorschaubilder sind **nur einzelne Frames**. Die tatsächliche Szene im gesamten Clip bleibt ungeprüft.
- Modellantworten sowie externe Metadaten gelten als nicht vertrauenswürdig und werden HTML-escaped.

## Evaluation: was wir wissen und was nicht

- Offline-Einheitstests und CI sind reproduzierbar.
- Mindestens 24 manuell kuratierte deutsche Szenen-Intent-Fälle testen den Typ und die Firmennennung.
- Mock-Tests prüfen relevante und irrelevante KI-Antworten, Sicherheitsgrenzen, Ausfälle, sowie die Blockade einer automatischen Freigabe.
- **Noch keine** echte Ground-Truth-Messung des Bild-Satz-Matchings, keine Bildfehlerquote, keine gemessenen API-Kosten. Erst nach einem dokumentierten 60-Sekunden-Volkswagen-Pilot kann man die Zuverlässigkeit bewerten.

## Danach

- Reale, unabhängige annotierte Bild-/Satz-Paare mit menschlicher Gegenkontrolle.
- Video-Stichproben über mehrere Frames, pHash/CLIP-Duplikatprüfung und Quellen-/Lizenzjournal.
- Bei fehlendem zulässigen Beleg eine eigene Infografik statt falschem Stockbild.
- Erst danach Zeitachsen, Sound-Synchronisation und Video-Rendering.
