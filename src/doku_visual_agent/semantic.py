"""Opt-in semantic visual intent planner. It cannot establish external facts."""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from .core import Scene, SearchTask
from .vision import VisionError

REAL_CONTEXT = {"event_evidence", "specific_location", "archive", "company_image"}


def improve_scene(scene: Scene, model: Any) -> Scene:
    """Ask an LLM for visual intent and search terms; never downgrade evidence rules."""
    instruction = (
        "Du erstellst Suchbegriffe für eine hochwertige journalistische Videodokumentation. "
        "Du recherchierst KEINE Tatsachen und darfst nichts erfinden. "
        "Schlage keine geschützten, geleakten oder fragwürdig verfügbaren Aufnahmen vor. "
        "Kein Stockvideo darf als Aufnahme eines realen Unternehmens/Ereignisses dargestellt werden. "
        "Antworte nur als JSON: visual_goal (max 200 Zeichen), search_queries "
        "(1-2 kurze Suchbegriffe auf Englisch), risk_note (max 180 Zeichen). "
        "Für Archiv/konkreten Ort/Ereignis suche über Wikimedia Commons mit echten Firmennamen/Orten "
        "und ggf. Jahr. Für abstrakte Situationen suche allgemeines Stock-B-Roll. "
        "Für Finanzzahlen nur Visualziel beschreiben, keine Aktienkurse/Zahlen erfinden.\n\n"
        f"Text: {scene.narration[:1200]}\n"
        f"Erkannter Szenentyp: {scene.visual_type}\n"
        f"Firma: {scene.entity}\nOrt: {scene.place}\nJahr: {scene.year}"
    )
    obj = model.generate(instruction)
    if not isinstance(obj, dict):
        raise VisionError("Ungültiger KI-Suchplan.")
    goal = str(obj.get("visual_goal", "")).strip()[:200]
    risk = str(obj.get("risk_note", "")).strip()[:180]
    queries = obj.get("search_queries", [])
    if not goal or not isinstance(queries, list):
        raise VisionError("Unvollständiger KI-Suchplan.")
    if scene.visual_type == "data_graphic":
        return replace(scene, visual_goal=goal, semantic_note=risk)
    cleaned: list[str] = []
    for query in queries[:2]:
        if not isinstance(query, str):
            continue
        q = " ".join(query.strip().split())[:110]
        if len(q) < 4 or any(c in q for c in "\n\r\t{}<>"):
            continue
        required = [x for x in (scene.entity, scene.place, scene.year) if x]
        if scene.visual_type in REAL_CONTEXT:
            for item in required:
                if item.casefold() not in q.casefold():
                    q += " " + item
        if q not in cleaned:
            cleaned.append(q)
    if not cleaned:
        raise VisionError("KI konnte keine gültigen Suchbegriffe erzeugen.")
    if scene.visual_type in REAL_CONTEXT:
        tasks = tuple(SearchTask("commons", query, "Konkreten Beleg prüfen") for query in cleaned)
    else:
        tasks = tuple(SearchTask(provider, query, "Stock/Symbolbild")
                      for query in cleaned[:1] for provider in ("pexels_photos", "pexels_videos"))
    return replace(scene, tasks=tasks, visual_goal=goal, semantic_note=risk)
