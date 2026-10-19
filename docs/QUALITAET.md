# Qualitätsstandard – Phase 1

## Prüfkriterien für jedes vorgeschlagene Visual

1. **Faktischer Bezug (Pflicht):** Zeigt der Inhalt wirklich das genannte Unternehmen, Ereignis, die Stadt oder Technik? Der Code vergleicht nur Metadaten. Mensch/Computer-Vision muss die Aufnahme prüfen.
2. **Quellkette (Pflicht):** Original-Landingpage, Urheber, Datum und möglichst Erstveröffentlichung nachvollziehbar.
3. **Rechte (Pflicht):** Lizenz und relevante Pflichten im konkreten kommerziellen Nutzungskontext dokumentiert; Marken/Personen gesondert bedenken. Ein API-Treffer ist keine Nutzungsfreigabe.
4. **Visualqualität:** Lesbarkeit, Auflösung, passende Perspektive, keine Wasserzeichen, keine künstlichen Verfälschungen.
5. **Szenenbezug:** Bild erklärt den gesagten Satz; keine bloß thematisch ähnlichen Füllbilder.
6. **Abwechslung:** Keine Wiederholung desselben Assets über Szenen; bei wiederholten Motiven aktiver gestalterischer Grund erforderlich.
7. **Nachvollziehbarkeit:** Alle Entscheidungen in `plan.json` und `approvals.json`.

## Nicht erlaubte Abkürzungen

- Fremdes Fabrikvideo als echte VW-Aufnahme ausgeben.
- Historisches Bild ohne verifiziertes Datum und Ort als Ereignisbeleg verwenden.
- Zahlen oder Charts auf Grundlage von Schätzungen erzeugen.
- CC BY / CC BY-SA ohne nötige Urheberangabe und Prüfung benutzen.
- Pexels als Freibrief für Marken-/Persönlichkeitsrechte behandeln.
- KI-Score als verifizierte Bildinhaltsanalyse darstellen.
- Bilder massenhaft aus Websites scrapen; offizielle Schnittstellen nutzen.

## Messbarer Abnahmetest vor Ausbau

Pilot: mindestens 60 Sekunden Dokumentationsskript, 4–8 Szenen.

- Für **jede** Szene: konkreter Visualtyp und Textaussage.
- **0** falsch dargestellte Ereignisse oder Orte.
- **0** unfreigegebene Assets in einem veröffentlichten Export.
- **0** erfundene Daten oder Quellen.
- Jeder Vorschlag enthält Landingpage und Status.
- Sichtung jeder Bildvorschau, ggf. Ausweichen auf eigene Grafik.
- Gesondert protokollieren: Anteil relevanter Treffer, manuelle Minuten pro Szene, Doppelungsquote, Kosten.

**Erst nach bestandenem Bildauswahltest**: semantische KI-Bewertung, Bilderkennung, Medienimport und Rendering integrieren.
