"""Render-ready storyboards built ONLY from approved, locally supplied media.

A prepared edit is not a rights clearance: it retains the provenance record.
No automatic scraping, no artificial video filler, no publishing.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXT = {".mp4"}
VOICE_EXT = {".mp3", ".wav", ".m4a"}
MAX_MEDIA_BYTES = 350_000_000
MAX_AUDIO_BYTES = 100_000_000
FPS = 30


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def https_url(value: str) -> bool:
    from urllib.parse import urlsplit
    try:
        p = urlsplit(value)
        return p.scheme == "https" and bool(p.hostname) and p.port in (None, 443) and not p.username
    except ValueError:
        return False


def media_probe(path: Path, *, audio: bool = False) -> dict:
    """Use ffprobe via argument array, no shell, no user-controlled command strings."""
    if shutil.which("ffprobe") is None:
        raise ValueError("ffprobe (FFmpeg) ist nicht installiert.")
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,width,height,duration",
             "-of", "json", str(path)],
            check=True, capture_output=True, text=True, timeout=15,
        )
        payload = json.loads(proc.stdout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            json.JSONDecodeError) as exc:
        raise ValueError(f"Medienprüfung fehlgeschlagen: {path.name}") from exc
    streams = payload.get("streams") or []
    wanted = "audio" if audio else "video"
    stream = next((s for s in streams if s.get("codec_type") == wanted), None)
    if stream is None:
        raise ValueError(f"Kein {wanted}-Stream: {path.name}")
    duration_value = (payload.get("format") or {}).get("duration") or stream.get("duration")
    duration = float(duration_value) if duration_value else 0.0
    if audio and (not math.isfinite(duration) or duration < 1):
        raise ValueError("Voiceover benötigt messbare Dauer von mindestens einer Sekunde.")
    if not audio and path.suffix.lower() == ".mp4" and (
        not math.isfinite(duration) or duration < 0.5
    ):
        raise ValueError("Video ist zu kurz oder Dauer nicht messbar.")
    return {"duration": duration, "width": int(stream.get("width") or 0),
            "height": int(stream.get("height") or 0)}


def checked_media(root: Path, name: str, extensions: set[str],
                  max_bytes: int) -> Path:
    """Only read from explicit media root; reject traversal, symlinks, and oversized files."""
    if not name or Path(name).is_absolute() or "\\" in name:
        raise ValueError("Medienpfad muss relativ zum Medienordner sein.")
    relative = Path(name)
    if any(part in (".", "..") for part in relative.parts):
        raise ValueError("Unsicherer Medienpfad.")
    absolute_root = root.resolve(strict=True)
    candidate = root / relative
    if not candidate.resolve().is_relative_to(absolute_root) or not candidate.is_file():
        raise ValueError("Datei außerhalb des Medienordners oder nicht vorhanden.")
    if candidate.is_symlink() or any(p.is_symlink() for p in candidate.parents if p != root):
        raise ValueError("Symbolische Links bei Medien gesperrt.")
    if candidate.suffix.lower() not in extensions:
        raise ValueError(f"Nicht erlaubter Medientyp: {candidate.suffix}")
    size = candidate.stat().st_size
    if size == 0 or size > max_bytes:
        raise ValueError(f"Mediengröße ungültig: {candidate.name}")
    return candidate


def allocate_frames(scenes: list[dict], total: int, fps: int,
                    timings: list[float] | None) -> list[int]:
    if not scenes:
        raise ValueError("Kein Skript vorhanden.")
    minimum = max(15, round(fps * 0.6))
    count = len(scenes)
    if total < count * minimum:
        raise ValueError("Voiceover ist für die Anzahl Szenen zu kurz.")
    if timings is not None:
        if len(timings) != count or any(
            not isinstance(x, (int, float)) or isinstance(x, bool)
            or not math.isfinite(x) or x <= 0 for x in timings
        ):
            raise ValueError("Ungültige manuelle Szenendauern.")
        if abs(sum(timings) * fps - total) > fps * 0.5:
            raise ValueError("Manuelle Szenendauern passen nicht zur Audiodauer.")
        weights = timings
    else:
        # Approximate paragraph timing, NOT word-level speech recognition.
        weights = [max(1, len(re.findall(r"\w+", s["narration"]))) for s in scenes]
    residual = total - count * minimum
    raw = [w / sum(weights) * residual for w in weights]
    add = [math.floor(x) for x in raw]
    remainder = residual - sum(add)
    order = sorted(range(count), key=lambda i: -(raw[i] - add[i]))
    for i in order[:remainder]:
        add[i] += 1
    durations = [minimum + x for x in add]
    assert sum(durations) == total
    return durations


def _verify_approval(scene: dict, approvals: list[dict], binding: dict) -> tuple[dict, dict]:
    matched = [c for c in scene.get("candidates", [])
               if c.get("asset", {}).get("id") == binding.get("asset_id")]
    if len(matched) != 1:
        raise ValueError(f"{scene['id']}: Asset ist kein Recherche-Kandidat.")
    candidate = matched[0]
    asset = candidate["asset"]
    if asset.get("demo_only") or candidate.get("review_status") == "rejected_by_vision":
        raise ValueError(f"{scene['id']}: Demo- oder KI-abgelehntes Bild gesperrt.")
    records = [a for a in approvals if a.get("scene_id") == scene["id"]
               and a.get("asset_id") == binding["asset_id"]]
    if len(records) != 1:
        raise ValueError(f"{scene['id']}: Es fehlt genau eine manuelle Medienfreigabe.")
    approval = records[0]
    for key in ("visual_evidence", "license_evidence"):
        if len(str(approval.get(key, "")).strip()) < 15:
            raise ValueError(f"{scene['id']}: {key} nicht dokumentiert.")
    if not https_url(asset.get("source_url", "")):
        raise ValueError(f"{scene['id']}: Keine gültige Quellseite.")
    if approval.get("source_url") != asset.get("source_url"):
        raise ValueError(f"{scene['id']}: Quelllink stimmt nicht mit Freigabe überein.")
    if approval.get("role") not in ("exakt", "symbolbild"):
        raise ValueError("Unbekannte Bildrolle.")
    if scene["visual_type"] == "generic_broll" and approval["role"] != "symbolbild":
        raise ValueError("Stock-Symbolbild muss als Symbolbild gekennzeichnet sein.")
    if scene["visual_type"] != "generic_broll" and approval["role"] != "exakt":
        raise ValueError("Eine konkrete Aussage benötigt eine geprüfte echte Aufnahme.")
    return asset, approval


def _verified_chart(scene: dict, chart: dict) -> dict:
    if scene.get("visual_type") != "data_graphic":
        raise ValueError(f"{scene['id']}: Ein Datenchart ersetzt keinen Szenenbeleg.")
    if chart.get("reviewed") is not True or not https_url(chart.get("source_url", "")):
        raise ValueError(f"{scene['id']}: Diagrammdaten benötigen geprüfte HTTPS-Quelle.")
    values = chart.get("values")
    if not isinstance(values, list) or not 2 <= len(values) <= 8:
        raise ValueError("Diagramm benötigt 2–8 belegte Zahlenwerte.")
    if len(str(chart.get("evidence", "")).strip()) < 15:
        raise ValueError("Quellen-/Zahlennachweis unvollständig.")
    for item in values:
        x = item.get("value")
        if (not isinstance(x, (int, float)) or isinstance(x, bool)
            or not math.isfinite(x) or x < 0 or x > 1e12
            or not 1 <= len(str(item.get("label", ""))) <= 28):
            raise ValueError("Diagramm enthält ungültige Werte oder Beschriftungen.")
    return {"title": str(chart.get("title", "Vergleich"))[:100],
            "values": [{"label": str(x["label"]), "value": x["value"]} for x in values],
            "source_url": chart["source_url"], "evidence": chart["evidence"][:300],
            "unit": str(chart.get("unit", ""))[:24]}


def prepare_render(run: Path, media_root: Path | None, assets_file: Path | None,
                   output: Path, *, voiceover: Path | None = None,
                   timings_file: Path | None = None, demo: bool = False,
                   fps: int = FPS) -> dict:
    if fps not in (24, 25, 30, 50, 60):
        raise ValueError("FPS muss 24, 25, 30, 50 oder 60 sein.")
    plan = load_json(run / "plan.json")
    scenes = plan.get("scenes") or []
    if not isinstance(scenes, list) or not scenes or len(scenes) > 100:
        raise ValueError("Plan benötigt zwischen 1 und 100 Szenen.")
    if demo:
        if plan.get("mode") != "OFFLINE_DEMO_NOT_REAL_MEDIA":
            raise ValueError("Demo-Modus nur mit Offline-Fixtures verwenden.")
        if voiceover or assets_file:
            raise ValueError("Demo-Export darf kein echtes Audio/Material erhalten.")
        total = fps * 3 * len(scenes)
        durations = [fps * 3] * len(scenes)
    else:
        if plan.get("mode") != "LIVE_SEARCH_UNREVIEWED":
            raise ValueError("Realer Export nur aus Live-Recherche, niemals Testdaten.")
        if voiceover is None or not assets_file or media_root is None:
            raise ValueError("Live-Export benötigt Voiceover, Assetbindungen und Medienordner.")
        if not voiceover.is_file() or voiceover.suffix.lower() not in VOICE_EXT:
            raise ValueError("Fehlende oder ungültige Voiceover-Datei.")
        if voiceover.stat().st_size > MAX_AUDIO_BYTES:
            raise ValueError("Voiceover zu groß.")
        audio_info = media_probe(voiceover, audio=True)
        total = round(audio_info["duration"] * fps)
        timing_values = None
        if timings_file:
            raw = load_json(timings_file)
            if not isinstance(raw, list):
                raise ValueError("Timings benötigen JSON-Liste von Sekundendauern.")
            timing_values = raw
        durations = allocate_frames(scenes, total, fps, timing_values)

    if output.resolve() == run.resolve() or output.resolve() == Path.cwd():
        raise ValueError("Ausgabe muss ein eigener Render-Unterordner sein.")
    public = output / "public"
    staged = public / "media"
    staged.mkdir(parents=True, exist_ok=True)
    approvals = [] if demo else load_json(run / "approvals.json")
    if not isinstance(approvals, list):
        raise ValueError("Ungültige Freigabedatei.")
    bindings = {} if demo else load_json(assets_file)
    if not isinstance(bindings, dict):
        raise ValueError("Assetbindungen benötigen JSON-Objekt mit Szenen-IDs.")
    results, files_to_copy, errors = [], [], []
    for scene, frames in zip(scenes, durations):
        sid = str(scene.get("id", ""))
        title = scene.get("visual_goal") or scene.get("entity") or scene.get("visual_type", "Doku")
        entry = {"sceneId": sid, "narration": str(scene["narration"]),
                 "title": str(title)[:90], "durationInFrames": frames}
        if demo:
            entry.update({"kind": "graphic", "label": "OFFLINE DEMO – KEINE RECHERCHIERTEN FAKTEN",
                          "source": "", "asset": None, "chart": None})
        else:
            binding = bindings.get(sid)
            try:
                if scene["visual_type"] == "data_graphic":
                    if not isinstance(binding, dict) or "chart" not in binding:
                        raise ValueError("Daten-Szene benötigt freigegebenes Diagramm.")
                    entry.update({"kind": "chart", "chart": _verified_chart(scene, binding["chart"]),
                                  "asset": None, "label": "DATEN AUS GEPRÜFTER QUELLE",
                                  "source": binding["chart"]["source_url"]})
                else:
                    if not isinstance(binding, dict):
                        raise ValueError("Kein freigegebenes Asset zugeordnet.")
                    asset, approval = _verify_approval(scene, approvals, binding)
                    file = checked_media(media_root, str(binding.get("file", "")),
                                         IMAGE_EXT | VIDEO_EXT, MAX_MEDIA_BYTES)
                    probe = media_probe(file)
                    if file.suffix.lower() == ".mp4" and (
                        probe["duration"] < frames / fps - 0.05
                    ):
                        raise ValueError("Video-B-Roll kürzer als erforderliche Szene.")
                    if probe["width"] < 640 or probe["height"] < 360:
                        raise ValueError("Bild/Video hat zu geringe Auflösung.")
                    dest = f"media/{sid}{file.suffix.lower()}"
                    files_to_copy.append((file, staged / f"{sid}{file.suffix.lower()}"))
                    entry.update({
                        "kind": "video" if file.suffix.lower() == ".mp4" else "image",
                        "asset": dest, "chart": None,
                        "label": "SYMBOLBILD" if approval["role"] == "symbolbild" else "GEPRÜFTE QUELLENAUFNAHME",
                        "source": asset["source_url"], "license": asset["license_name"],
                        "credit": asset.get("attribution") or asset.get("creator", ""),
                        "media_sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                    })
            except (ValueError, OSError) as exc:
                errors.append(f"{sid}: {exc}")
        results.append(entry)
    if errors:
        raise ValueError("Export blockiert, unvollständige Szenen:\n" + "\n".join(errors))
    for src, dest in files_to_copy:
        shutil.copy2(src, dest)
    voice_file = None
    if not demo and voiceover is not None:
        voice_file = f"media/voiceover{voiceover.suffix.lower()}"
        shutil.copy2(voiceover, public / voice_file)
    manifest = {
        "schema": 1, "fps": fps, "width": 1920, "height": 1080,
        "durationInFrames": total, "scenes": results,
        "voiceover": voice_file, "demo": demo,
        "timing_quality": "silent_demo" if demo else (
            "manual_scene_durations" if timings_file else "estimated_by_word_count"
        ),
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "notice": "Nur nach Bild- und Rechteprüfung publizieren; Zeitangaben sind keine Wort-Synchronisation.",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "props.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
    (output / "credits.json").write_text(
        json.dumps([{"scene": s["sceneId"], "source": s.get("source"),
                     "license": s.get("license", ""), "credit": s.get("credit", "")}
                    for s in results if s.get("source")],
                   ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )
    return manifest
