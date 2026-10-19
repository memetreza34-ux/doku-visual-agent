"""Build a transparent research plan. Never select a media file for publication."""

from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from .semantic import improve_scene
from .vision import VisionError

from .core import make_scenes, select_candidates
from .providers import Commons, FixtureSource, Pexels, ProviderError


def build_plan(script: str, *, pexels_key: str = "", fixture: list[dict] | None = None,
               results_per_task: int = 8, candidates_per_scene: int = 4,
               semantic_client: Any = None, vision_enabled: bool = False) -> dict:
    scenes = make_scenes(script)
    warnings = []
    if semantic_client is not None:
        updated = []
        for scene in scenes:
            try:
                updated.append(improve_scene(scene, semantic_client))
            except VisionError as exc:
                updated.append(scene)  # Preserve conservative original search plan.
                warnings.append(f"{scene.id}: KI-Suchplanung fehlgeschlagen: {exc}")
        scenes = updated
    is_demo = fixture is not None
    pexels = Pexels(pexels_key) if not is_demo else FixtureSource(fixture)
    commons = Commons() if not is_demo else pexels
    seen: set[str] = set()
    output = []
    search_cache = {}

    for scene in scenes:
        assets = []
        queries = []
        for task in scene.tasks:
            cache_key = (task.provider, task.query)
            queries.append(asdict(task))
            if cache_key not in search_cache:
                try:
                    adapter = commons if task.provider == "commons" else pexels
                    search_cache[cache_key] = adapter.search(
                        task.query, task.provider, limit=results_per_task)
                except ProviderError as exc:
                    search_cache[cache_key] = []
                    warnings.append(f"{task.provider} / {task.query}: {exc}")
            assets.extend(search_cache[cache_key])
        suggestions = select_candidates(scene, assets, limit=candidates_per_scene,
                                        already_seen=seen, allow_weak=vision_enabled)
        output.append({
            "id": scene.id, "narration": scene.narration, "visual_type": scene.visual_type,
            "entity": scene.entity, "place": scene.place, "year": scene.year,
            "guidance": scene.guidance, "visual_goal": scene.visual_goal,
            "semantic_note": scene.semantic_note,
            "search_tasks": queries,
            "candidates": suggestions,
            "state": "manual_review_needed" if suggestions else "needs_research_or_graphic",
        })

    return {
        "schema_version": 1,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "OFFLINE_DEMO_NOT_REAL_MEDIA" if is_demo else "LIVE_SEARCH_UNREVIEWED",
        "publication_ready": False,
        "planning_mode": "llm_assisted_unverified" if semantic_client is not None else "rule_based",
        "scenes": output,
        "warnings": list(dict.fromkeys(warnings)),
        "notice": "Kein Treffer belegt allein das Dargestellte oder die Nutzungsrechte.",
    }


def save_plan(plan: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "plan.json").write_text(
        json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )


def approve_asset(run: Path, scene_id: str, asset_id: str, role: str,
                  license_evidence: str, visual_evidence: str) -> Path:
    if role not in ("exakt", "symbolbild"):
        raise ValueError("Rolle muss exakt oder symbolbild sein.")
    if len(license_evidence.strip()) < 15 or len(visual_evidence.strip()) < 15:
        raise ValueError("Beide Nachweise müssen begründet werden (mindestens 15 Zeichen).")
    plan = json.loads((run / "plan.json").read_text(encoding="utf-8"))
    if plan.get("mode") != "LIVE_SEARCH_UNREVIEWED":
        raise ValueError("Die Offline-Demo kann nicht freigegeben werden.")
    scene = next((s for s in plan["scenes"] if s["id"] == scene_id), None)
    if scene is None:
        raise ValueError("Unbekannte Szenen-ID.")
    asset = next((c["asset"] for c in scene["candidates"] if c["asset"]["id"] == asset_id), None)
    if asset is None:
        raise ValueError("Asset steht nicht in der Vorschlagsliste dieser Szene.")
    if next((c.get("review_status") for c in scene["candidates"]
             if c["asset"]["id"] == asset_id), None) == "rejected_by_vision":
        raise ValueError("Von der KI als unpassend aussortiertes Asset; erneut recherchieren.")
    if role == "symbolbild" and scene["visual_type"] != "generic_broll":
        raise ValueError("Konkrete Sachbehauptungen/Ereignisse dürfen nicht durch Symbolbild freigegeben werden.")
    if role == "exakt" and scene["visual_type"] == "generic_broll":
        raise ValueError("Ein generisches Stockmotiv ist kein verifizierter Originalbeleg.")
    approvals_path = run / "approvals.json"
    existing = json.loads(approvals_path.read_text(encoding="utf-8")) if approvals_path.exists() else []
    entry = {
        "scene_id": scene_id, "asset_id": asset_id, "role": role,
        "source_url": asset["source_url"], "license_name": asset["license_name"],
        "license_evidence": license_evidence.strip(),
        "visual_evidence": visual_evidence.strip(),
        "reviewed_utc": datetime.now(timezone.utc).isoformat(),
        "reviewed_by": "manuelle CLI-Bestätigung",
    }
    existing = [e for e in existing if (e["scene_id"], e["asset_id"]) != (scene_id, asset_id)]
    existing.append(entry)
    approvals_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n",
                              encoding="utf-8")
    return approvals_path
