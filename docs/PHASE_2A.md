# Phase 2A: Remotion-Export mit Freigabe-Gates

Dieses Modul rendert einen Videoentwurf aus der bereits vorhandenen Szenenrecherche. Es ist **keine vollständig autonome Doku-KI**. Erforderliche Bild-/Rechtebelege werden nicht übersprungen.

## Voraussetzungen

Python 3.11+, FFmpeg/ffprobe, Node 20+, npm, Chromium (Remotion kann den Browser beim ersten Start installieren).

## Offline-Demo: Ohne echte Fakten, Stimme oder fremde Bilder

~~~bash
python -m pip install -e .
python -m doku_visual_agent plan --script examples/volkswagen_60s.txt --fixture examples/demo_assets.json --output runs/demo
python -m doku_visual_agent prepare-render --run runs/demo --output runs/demo/render --demo
cd remotion
npm install
npx remotion render src/index.jsx DokuVideo ../runs/demo/DEMO.mp4 --props ../runs/demo/render/props.json --public-dir ../runs/demo/render/public
~~~

Das Ergebnis ist eine **als Demo markierte grafische Vorschau**, nicht eine recherchierte Volkswagen-Dokumentation. Ohne Stimme bleibt die Demo stumm.

## Echte Videos aus geprüften Quellen

1. Plan live recherchieren und alle Bilder mit Bildinhalt, exakter Quelle und Lizenzbedingungen manuell prüfen.
2. Freigegebene Kandidaten mit dem bestehenden CLI-Unterbefehl approve protokollieren. Alle echten Mediendateien müssen rechtmäßig vorliegen.
3. Freigegebene Fotos/Videos in einem lokalen Ordner ablegen (z. B. assets/).
4. Die Datei bindings.json anlegen: Sie ordnet einer Szenen-ID eine Asset-ID und einen Dateinamen zu. Daten-Szenen brauchen stattdessen ein überprüftes Diagramm mit Originalquelle.
5. Sprecher-Audio vorbereiten (MP3, WAV oder M4A). Szenendauern werden anhand der mit ffprobe gemessenen Gesamtdauer geschätzt.
6. Timeline und geprüftes Medienpaket erstellen:

~~~bash
python -m doku_visual_agent prepare-render --run runs/vw-live --media-root assets --assets bindings.json --voiceover voice.mp3 --output runs/vw-live/render
cd remotion
npm install
npx remotion render src/index.jsx DokuVideo ../runs/vw-live/final.mp4 --props ../runs/vw-live/render/props.json --public-dir ../runs/vw-live/render/public
~~~

Beispiel einer bindings.json (FIKTIVE IDs, keine faktischen VW-Aussagen):

~~~json
{
  "S01": {"asset_id": "commons:123", "file": "werk.jpg"},
  "S02": {"asset_id": "pexels:video:456", "file": "fertigung.mp4"},
  "S03": {
    "chart": {
      "reviewed": true,
      "title": "Belegter Vergleich",
      "source_url": "https://example.org/originalquelle",
      "evidence": "Jahreszahlen und Einheiten im Geschäftsbericht geprüft",
      "unit": "Mio. EUR",
      "values": [{"label": "Jahr A", "value": 2}, {"label": "Jahr B", "value": 3}]
    }
  }
}
~~~

Die Chartdaten oben sind Platzhalter und dürfen niemals als echte Unternehmenszahlen veröffentlicht werden.

## Ausgabe

- render/props.json: Szenen, Frame-Dauern, Medienreferenzen und Quellen.
- render/credits.json: Zuordnung von Originalquellen und Urhebern.
- render/public/media: Eingelesene Medienkopien; keine Dateien ohne explizite Freigabe.
- final.mp4: erst nach dem Remotion-Render.

## Synchronisation / Grenzen

Ohne individuelle Zeitmarken werden Szenenlängen proportional zur **Wortanzahl** verteilt. Es existiert noch keine Wort-Synchronisation und keine automatische TTS. Präzisere Zeitmarken können als JSON-Liste von Szenendauern in Sekunden mit dem Argument --timings übergeben werden. Die Summendauer muss zur Sprecherdatei passen.

Die Software ersetzt weder die erforderliche Prüfung journalistischer Fakten noch das Urheberrecht. Die Rechtsfreigabe wird nur protokolliert, nicht automatisiert festgestellt.

Als Nächstes: Quellengebundene Skripterstellung, WhisperX-Wort-Timing, technische Infografiken, Video-Frame-Validierung, Qualitätstest mit realen Aufnahmen.
