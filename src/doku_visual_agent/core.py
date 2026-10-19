"""Deterministic scene planning and conservative metadata-only candidate ranking."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
import unicodedata
from typing import Any


COMMON_STOP = {
    "aber", "als", "am", "an", "and", "auf", "aus", "bei", "bis", "da", "das",
    "dass", "dem", "den", "der", "des", "die", "dies", "diese", "dieser", "ein",
    "eine", "einem", "einen", "einer", "er", "es", "fuer", "für", "haben", "hat",
    "im", "in", "ist", "mit", "nach", "nicht", "oder", "sich", "sie", "sind",
    "so", "the", "to", "und", "vom", "von", "was", "werden", "wie", "wir", "wird",
    "with", "zu", "zum", "zur", "of", "a", "for", "at", "on", "an", "about",
}
TRANSLATE = {
    "vw": "volkswagen", "autos": "car", "auto": "car",
    "automobil": "car", "automotive": "car", "fahrzeuge": "car",
    "fahrzeug": "car", "autofabrik": "factory", "fabrik": "factory",
    "fabriken": "factory", "werk": "factory", "werke": "factory",
    "produktion": "production", "fertigung": "production",
    "herstellung": "production", "montage": "assembly",
    "roboter": "robot", "robotern": "robot", "roboterarme": "robot",
    "industrieroboter": "robot", "elektroauto": "electric",
    "elektroautos": "electric", "batterien": "battery",
    "batterie": "battery", "geschichte": "history", "historisch": "history",
    "frueher": "history", "früher": "history", "industrie": "industry",
}
FINANCE = ("umsatz", "gewinn", "verlust", "absatz", "kosten", "bilanz", "milliarden",
           "millionen", "prozent", "rendite", "geschaftszahl", "geschäftszahl",
           "beschaftigt", "beschäftigt", "ergebnis", "diagramm")
NEWS = ("angekundigt", "angekündigt", "streik", "schliess", "schließ", "heute",
        "gestern", "aktuell", "berichtet", "beschlossen", "vergangene woche")
ARCHIVE = ("geschichte", "historisch", "damals", "früher", "archiv", "1960",
           "1970", "1980", "1990", "1950")
FACTORY = ("wolfsburg", "werk", "fabrik", "standort", "zentrale", "hauptsitz")
KNOWN_ENTITIES = ("Volkswagen", "BMW", "Tesla", "Mercedes-Benz", "Siemens", "Bosch")
LOCATIONS = ("Wolfsburg", "Dresden", "Berlin", "Zwickau", "Emden", "Hannover")


def tokens(value: str) -> set[str]:
    folded = unicodedata.normalize("NFKD", value.lower())
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    words = re.findall(r"[a-z0-9]+", folded)
    return {TRANSLATE.get(w, w) for w in words if len(w) >= 3 and w not in COMMON_STOP}


@dataclass(frozen=True)
class SearchTask:
    provider: str
    query: str
    purpose: str


@dataclass(frozen=True)
class Scene:
    id: str
    narration: str
    visual_type: str
    entity: str
    place: str
    year: str
    tasks: tuple[SearchTask, ...]
    guidance: str


@dataclass(frozen=True)
class Asset:
    id: str
    provider: str
    kind: str
    title: str
    description: str
    creator: str
    source_url: str
    preview_url: str
    media_url: str
    license_name: str
    license_url: str
    attribution: str = ""
    width: int = 0
    height: int = 0
    demo_only: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def classify(narration: str) -> str:
    t = narration.lower()
    if any(word in t for word in FINANCE):
        return "data_graphic"
    if any(word in t for word in NEWS):
        return "event_evidence"
    if any(word in t for word in ARCHIVE) or re.search(r"\b(18|19|20)\d{2}\b", t):
        return "archive"
    if any(word in t for word in FACTORY):
        return "specific_location" if entity_in(t) or location_in(t) else "generic_broll"
    return "company_image" if entity_in(t) else "generic_broll"


def entity_in(value: str) -> str:
    if re.search(r"\bvw\b", value, flags=re.I):
        return "Volkswagen"
    for name in KNOWN_ENTITIES:
        if re.search(r"\b" + re.escape(name) + r"\b", value, flags=re.I):
            return name
    return ""


def location_in(value: str) -> str:
    for place in LOCATIONS:
        if re.search(r"\b" + re.escape(place) + r"\b", value, flags=re.I):
            return place
    return ""


def _queries(narration: str, visual_type: str, entity: str, place: str, year: str) -> tuple[SearchTask, ...]:
    if visual_type == "data_graphic":
        return ()
    if visual_type in ("event_evidence", "specific_location", "company_image", "archive"):
        key = " ".join(v for v in (entity, place, year) if v) or narration[:90]
        if visual_type == "archive":
            key = f"{key} historical factory"
        if visual_type == "event_evidence":
            key = f"{key} {narration[:65]}"
        if visual_type == "company_image" and entity:
            key = f"{key} company"
        return (SearchTask("commons", key.strip(), "konkreter Beleg"),)

    t = narration.lower()
    if any(word in t for word in ("batterie", "elektroauto", "elektromobil")):
        query = "electric vehicle battery manufacturing"
    elif any(word in t for word in ("roboter", "produktion", "fabrik", "montage", "werk")):
        query = "automotive factory robot production"
    elif any(word in t for word in ("mitarbeiter", "arbeitnehmer", "beschäftigte")):
        query = "industrial workers"
    else:
        # Fallback does not promise to depict a named real-world event.
        query = " ".join(sorted(tokens(narration))[:5]) or "industry"
    return (SearchTask("pexels_photos", query, "Symbolbild"),
            SearchTask("pexels_videos", query, "Symbolbild"))


def make_scenes(script: str) -> list[Scene]:
    cleaned = re.sub(r"(?m)^\s*#{1,6}\s+[^\n]+\n?", "", script).strip()
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", cleaned)]
    paragraphs = [p for p in paragraphs if p]
    if not paragraphs:
        raise ValueError("Skript enthält keine Absätze.")
    if len(paragraphs) > 100:
        raise ValueError("Maximal 100 Absätze/Szenen pro Durchlauf.")
    scenes = []
    for i, para in enumerate(paragraphs, 1):
        entity = entity_in(para)
        place = location_in(para)
        year_match = re.search(r"\b(?:18|19|20)\d{2}\b", para)
        year = year_match.group() if year_match else ""
        kind = classify(para)
        guidance = {
            "data_graphic": "Nur Diagramme mit belegten Zahlen erstellen; keine erfundenen Daten.",
            "event_evidence": "Konkretes Ereignis: Originalbeleg und Datum redaktionell prüfen; kein Symbolbild als Ereignisbeweis.",
            "archive": "Archivaufnahme: Zeitraum, Ort und Urheber vor Verwendung bestätigen.",
            "specific_location": "Konkreter Ort/Firma: Aufnahme muss nachweisbar passen.",
            "company_image": "Firma und Aufnahmeort aus Originalquelle prüfen.",
            "generic_broll": "Stockmaterial ausschließlich als klar erkennbares Symbolbild.",
        }[kind]
        scenes.append(Scene(
            id=f"S{i:02d}", narration=para, visual_type=kind, entity=entity, place=place,
            year=year, tasks=_queries(para, kind, entity, place, year), guidance=guidance,
        ))
    return scenes


def inspect_candidate(scene: Scene, asset: Asset) -> dict[str, Any] | None:
    if not asset.source_url.startswith("https://"):
        return None
    metadata = f"{asset.title} {asset.description}"
    terms = tokens(metadata)
    target = tokens(scene.narration)
    required = tokens(" ".join((scene.entity, scene.place, scene.year)))
    if scene.visual_type in ("specific_location", "archive", "event_evidence", "company_image"):
        if required and not required.issubset(terms):
            return None
        if asset.provider == "pexels":
            return None  # Stock clips are not verified evidence of a specific real-world place/event.
    if scene.visual_type == "data_graphic":
        return None
    overlap = len(target & terms)
    if not overlap and not (required & terms):
        return None
    # This is a metadata relevance score, never a visual verification/confidence percentage.
    score = round(10 * overlap / max(1, len(target)) + 2 * len(required & terms), 3)
    if asset.kind == "video" and scene.visual_type == "generic_broll":
        score += 0.5
    if asset.provider == "commons" and scene.visual_type != "generic_broll":
        score += 1
    return {
        "asset": asdict(asset),
        "metadata_score": round(score, 3),
        "usage_label": "Symbolbild" if scene.visual_type == "generic_broll" else "Originalbeleg prüfen",
        "review_status": "pending",
        "why": f"{overlap} passende Skript-Metadaten-Begriffe; Bildinhalt noch nicht geprüft",
    }


def select_candidates(scene: Scene, assets: list[Asset], limit: int = 4,
                      already_seen: set[str] | None = None) -> list[dict[str, Any]]:
    seen = already_seen if already_seen is not None else set()
    ranked = [x for asset in assets if asset.id not in seen
              if (x := inspect_candidate(scene, asset)) is not None]
    ranked.sort(key=lambda item: (-item["metadata_score"], item["asset"]["id"]))
    results = []
    local_ids: set[str] = set()
    for candidate in ranked:
        asset_id = candidate["asset"]["id"]
        if asset_id in local_ids:
            continue
        local_ids.add(asset_id)
        results.append(candidate)
        if len(results) >= limit:
            break
    seen.update(item["asset"]["id"] for item in results)
    return results
