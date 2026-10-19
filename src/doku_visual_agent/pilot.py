"""Curated real-photo documentary pilot, NOT a license-cleared publication workflow.

Each photo is fetched through Wikimedia Commons imageinfo, its reported
license and author are checked against a human-authored manifest, and a rights
review flag remains explicitly false. An offline robotic voice proves the
audio/render path without presenting it as a production-quality narrator.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import hashlib
import json
from pathlib import Path
import re
import shutil
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .production import allocate_frames, media_probe
from .providers import get_json, meta

USER_AGENT = "DokuVisualAgent/0.3 (https://github.com/memetreza34-ux/doku-visual-agent; research pilot)"
MAX_PHOTO_BYTES = 9_000_000
SUPPORTED = {"CC BY 4.0", "CC BY-SA 4.0", "CC BY-SA 2.0"}
COMMONS_API = "https://commons.wikimedia.org/w/api.php"


class PilotError(ValueError):
    pass


def validate_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(manifest, dict) or manifest.get("pilot_id") != "wolfsburg_history_01":
        raise PilotError("Unbekanntes Pilotprojekt.")
    scenes = manifest.get("scenes")
    if not isinstance(scenes, list) or not 4 <= len(scenes) <= 10:
        raise PilotError("Pilot erfordert 4–10 Szenen.")
    identifiers: set[str] = set()
    file_names: set[str] = set()
    images = 0
    for idx, scene in enumerate(scenes, 1):
        if not isinstance(scene, dict):
            raise PilotError("Szenenformat ungültig.")
        sid = scene.get("id")
        if not isinstance(sid, str) or not re.fullmatch(r"S\d{2}", sid) or sid in identifiers:
            raise PilotError("Szenen-ID fehlt oder ist doppelt.")
        identifiers.add(sid)
        if len(str(scene.get("text", "")).strip()) < 25:
            raise PilotError(f"{sid}: Sprechertext fehlt.")
        if len(str(scene.get("title", "")).strip()) < 3:
            raise PilotError(f"{sid}: Bildtitel fehlt.")
        kind = scene.get("kind")
        if kind == "photo":
            images += 1
            file_title = scene.get("commons_title")
            if (not isinstance(file_title, str)
                    or not file_title.startswith("File:")
                    or not file_title.lower().endswith((".jpg", ".jpeg", ".png"))
                    or len(file_title) > 220
                    or file_title in file_names):
                raise PilotError(f"{sid}: Wikimedia-Dateiname nicht eindeutig.")
            file_names.add(file_title)
            if scene.get("expected_license") not in SUPPORTED:
                raise PilotError(f"{sid}: unbekannte Creative-Commons-Lizenz.")
            if not 4 <= len(str(scene.get("expected_author", ""))) <= 90:
                raise PilotError(f"{sid}: Autorennachweis fehlt.")
            if not isinstance(scene.get("capture_year"), int):
                raise PilotError(f"{sid}: Fotojahr fehlt.")
        elif kind != "graphic":
            raise PilotError(f"{sid}: unbekannte Szene {kind!r}.")
        refs = scene.get("fact_source_urls")
        if not isinstance(refs, list) or not refs or any(
            not isinstance(ref, str) or not ref.startswith("https://")
            for ref in refs
        ):
            raise PilotError(f"{sid}: Faktenquellen fehlen.")
    if images < 3:
        raise PilotError("Pilot soll mindestens drei reale Fotos enthalten.")
    return manifest


def write_narration(manifest_path: Path, output: Path) -> Path:
    manifest = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    output.mkdir(parents=True, exist_ok=True)
    script = "\n\n".join(s["text"].strip() for s in manifest["scenes"])
    destination = output / "narration.txt"
    destination.write_text(script + "\n", encoding="utf-8")
    (output / "shotlist.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return destination


def commons_imageinfo(file_title: str) -> dict[str, Any]:
    params = {
        "action": "query", "prop": "imageinfo", "iiprop": "url|size|extmetadata",
        "iiurlwidth": 1600, "titles": file_title,
        "format": "json", "formatversion": 2,
    }
    url = COMMONS_API + "?" + urllib.parse.urlencode(params)
    raw = get_json(url, headers={"User-Agent": USER_AGENT}, timeout=20)
    pages = (raw.get("query") or {}).get("pages") or []
    if not isinstance(pages, list) or len(pages) != 1 or pages[0].get("missing"):
        raise PilotError(f"Nicht auf Commons gefunden: {file_title}")
    infos = pages[0].get("imageinfo") or []
    if not infos:
        raise PilotError("Commons liefert keine Bildmetadaten.")
    return infos[0]


def verify_metadata(scene: dict[str, Any], info: dict[str, Any]) -> dict[str, str]:
    ext = info.get("extmetadata") or {}
    lic = meta(ext, "LicenseShortName").strip()
    author = meta(ext, "Artist").strip()
    license_url = meta(ext, "LicenseUrl").strip()
    if lic != scene["expected_license"]:
        raise PilotError(f"{scene['id']}: Lizenzangabe wich ab: {lic or 'unbekannt'}")
    if scene["expected_author"].casefold() not in author.casefold():
        raise PilotError(f"{scene['id']}: Autorennachweis weicht ab.")
    if not license_url.startswith("https://creativecommons.org/licenses/"):
        raise PilotError(f"{scene['id']}: keine nachvollziehbare CC-Lizenz-URL.")
    if int(info.get("width") or 0) < 1100 or int(info.get("height") or 0) < 600:
        raise PilotError(f"{scene['id']}: Foto zu niedrig aufgelöst.")
    description_url = info.get("descriptionurl", "")
    if not (isinstance(description_url, str)
            and description_url.startswith("https://commons.wikimedia.org/wiki/File:")):
        raise PilotError(f"{scene['id']}: Commons-Originalseite nicht vorhanden.")
    # Wikimedia imageinfo may yield an upload.wikimedia.org CDN URL or a
    # Special:FilePath/thumbnail endpoint on commons.wikimedia.org.
    # Validate the exact host AND endpoint; never allow arbitrary external URLs.
    candidates = [str(info.get("thumburl") or ""), str(info.get("url") or "")]
    image_url = next((u for u in candidates if allowed_commons_image_url(u)), "")
    if not image_url:
        # The Commons API sometimes returns an alternate delivery host. Never
        # follow it. Ask Wikimedia's documented Special:FilePath endpoint
        # for the SAME curated, API-verified file instead.
        title = scene["commons_title"].removeprefix("File:").replace(" ", "_")
        image_url = ("https://commons.wikimedia.org/wiki/Special:FilePath/" +
                     urllib.parse.quote(title, safe="()_-.") + "?width=1600")
        if not allowed_commons_image_url(image_url):
            raise PilotError(f"{scene['id']}: kein sicherer Wikimedia-Fallback.")
    return {
        "url": image_url, "source_page": description_url,
        "license_name": lic, "license_url": license_url,
        "author": scene["expected_author"],
    }


def allowed_commons_image_url(url: str) -> bool:
    """Allow the original Wikimedia CDN and its documented thumbnail/file paths."""
    try:
        p = urllib.parse.urlsplit(url)
        if (p.scheme != "https" or p.port not in (None, 443)
                or p.username or p.password or not p.hostname):
            return False
        if p.hostname == "upload.wikimedia.org":
            return p.path.startswith("/wikipedia/commons/")
        if p.hostname == "commons.wikimedia.org":
            return (p.path == "/w/thumb.php" or
                    p.path.startswith("/wiki/Special:FilePath/") or
                    p.path.startswith("/wiki/Special:Redirect/file/"))
        return False
    except ValueError:
        return False


class NoRedirectExceptCommons(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not allowed_commons_image_url(newurl):
            raise PilotError("Externe Wikimedia-Weiterleitung gesperrt.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_photo(url: str) -> bytes:
    if not allowed_commons_image_url(url):
        raise PilotError("Nicht erlaubte Wikimedia-Bildadresse.")
    opener = urllib.request.build_opener(NoRedirectExceptCommons())
    try:
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT, "Accept": "image/jpeg,image/png",
        })
        with opener.open(request, timeout=30) as response:
            if not allowed_commons_image_url(response.geturl()):
                raise PilotError("Unerwartetes Bildziel.")
            declared = int(response.headers.get("Content-Length", "0"))
            if declared > MAX_PHOTO_BYTES:
                raise PilotError("Bilddatei zu groß.")
            result = response.read(MAX_PHOTO_BYTES + 1)
            if len(result) > MAX_PHOTO_BYTES:
                raise PilotError("Bilddatei zu groß.")
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise PilotError("Wikimedia-Bild konnte nicht geladen werden.") from exc
    if not (result.startswith(b"\xff\xd8\xff") or result.startswith(b"\x89PNG\r\n\x1a\n")):
        raise PilotError("Download war kein JPEG/PNG.")
    return result


def prepare_pilot(manifest_path: Path, output: Path, voiceover: Path,
                  fps: int = 30) -> dict[str, Any]:
    """Build a visibly non-publishable documentary sample with real curated photo evidence."""
    if fps not in (24, 25, 30):
        raise PilotError("Pilot-FPS muss 24, 25 oder 30 sein.")
    manifest = validate_manifest(json.loads(manifest_path.read_text(encoding="utf-8")))
    if not voiceover.is_file() or voiceover.suffix.lower() != ".wav":
        raise PilotError("Demo-Sprachdatei (*.wav) fehlt.")
    voice = media_probe(voiceover, audio=True)
    duration_frames = round(voice["duration"] * fps)
    splits = allocate_frames([{"narration": s["text"]} for s in manifest["scenes"]],
                             duration_frames, fps, None)
    staged = output / "public" / "media"
    staged.mkdir(parents=True, exist_ok=True)
    scenes = []
    credits = []
    for scene, frames in zip(manifest["scenes"], splits):
        sid = scene["id"]
        props = {
            "sceneId": sid, "narration": scene["text"], "title": scene["title"],
            "durationInFrames": frames, "label": "QUELLENGEPRÜFTE PILOTRECHERCHE",
        }
        if scene["kind"] == "photo":
            info = commons_imageinfo(scene["commons_title"])
            asset = verify_metadata(scene, info)
            image_bytes = download_photo(asset["url"])
            suffix = ".png" if image_bytes.startswith(b"\x89PNG") else ".jpg"
            target = staged / (sid + suffix)
            target.write_bytes(image_bytes)
            props.update({"kind": "image", "asset": "media/" + target.name,
                          "source": asset["author"] + " / Wikimedia Commons", "chart": None})
            credits.append({
                "scene": sid, "file": scene["commons_title"],
                "source_page": asset["source_page"],
                "creator": asset["author"],
                "license": asset["license_name"], "license_url": asset["license_url"],
                "modification": "Ken-Burns-Zoom, Text-/Layout-Overlay im Pilotvideo",
                "image_sha256": hashlib.sha256(image_bytes).hexdigest(),
                "capture_year_annotated": scene["capture_year"],
                "manual_license_review_complete": False,
                "description_credit_required": True,
            })
        else:
            props.update({"kind": "graphic", "asset": None, "chart": None,
                          "source": "Eigene Zeitstrahlgrafik – siehe Quellenmappe"})
        scenes.append(props)
    shutil.copy2(voiceover, staged / "narration.wav")
    final = {
        "schema": 1, "fps": fps, "width": 1920, "height": 1080,
        "durationInFrames": duration_frames, "scenes": scenes,
        "voiceover": "media/narration.wav", "demo": True, "pilot": True,
        "publication_ready": False,
        "rights_review_required": True,
        "quality_review_required": True,
        "timing_quality": "word_count_estimate",
        "voice_quality": "external_audio_requires_listening",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "notice": "REAL COMMONS IMAGES – NOT PUBLISHABLE; rights, exact depictions and audio must be reviewed.",
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "props.json").write_text(json.dumps(final, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    (output / "credits.json").write_text(json.dumps(credits, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    (output / "rights_to_review.md").write_text(
        "# PILOT: NICHT AUTOMATISCH VERÖFFENTLICHEN\n\n"
        "Creative-Commons-Fotos können Namensnennung, Links, Bearbeitungsvermerk "
        "und ShareAlike-Pflichten auslösen. Quelldateien, Bearbeitung, Marken, "
        "Persönlichkeitsrechte und konkrete redaktionelle Nutzung vor Veröffentlichung "
        "erneut prüfen. Einzelne tatsächliche Aufnahmedaten stammen aus der "
        "manuell kuratierten Shotlist und sind nicht maschinell verifiziert.\n",
        encoding="utf-8")

    cards = []
    for item, shot in zip(manifest["scenes"], scenes):
        facts = "".join(
            '<li><a href="' + escape(u, quote=True) + '" rel="noopener noreferrer">' +
            escape(u) + "</a></li>" for u in item["fact_source_urls"]
        )
        if shot["kind"] == "image":
            rights = next(c for c in credits if c["scene"] == shot["sceneId"])
            illustration = (
                '<img loading="lazy" src="public/' + escape(shot["asset"], quote=True) +
                '" alt="Dokumentarisches Commons-Foto, Bildinhalt manuell prüfen">'
            )
            reference = (
                '<p>Urheber: ' + escape(rights["creator"]) +
                " · " + escape(rights["license"]) +
                ' · <a href="' + escape(rights["source_page"], quote=True) +
                '" rel="noopener noreferrer">Originalbild</a>' +
                ' · <a href="' + escape(rights["license_url"], quote=True) +
                '" rel="noopener noreferrer">Lizenz</a></p>'
            )
        else:
            illustration = '<div class="graphic">Eigene Zeitstrahlgrafik · kein Originalfoto</div>'
            reference = '<p>Keine Bildlizenz erforderlich, Faktenquellen separat prüfen.</p>'
        cards.append(
            '<section><h2>' + escape(item["id"]) + " – " +
            escape(item["title"]) + '</h2>' + illustration +
            "<p><strong>Sprecher:</strong> " + escape(item["text"]) + "</p>" +
            reference + "<p><strong>Faktenquellen:</strong></p><ul>" + facts + "</ul>" +
            '<p class="warning">Manuell noch offen: Bildaussage · Lizenz-/Attributionspflichten · Audio · Schnitt.</p>' +
            "</section>"
        )
    html = (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>VW-Doku · echte Bildquellen prüfen</title>"
        '<style>body{font:16px system-ui,sans-serif;background:#0c1724;color:#edf4f8;'
        'max-width:1000px;margin:auto;padding:30px}a{color:#99d8ff}'
        'section{border:1px solid #46566b;border-radius:14px;background:#1a283a;'
        'padding:24px;margin:24px 0}img{width:100%;max-height:440px;object-fit:contain;'
        'background:#0b1220}.graphic{padding:90px 18px;text-align:center;background:#142f46}'
        '.warning{color:#ffcf90;font-weight:700}li{overflow-wrap:anywhere}</style>'
        '</head><body><h1>Volkswagen: Echter Bildtest – redaktionelle Sichtung</h1>'
        '<p class="warning">NICHT FREIGEGEBEN · technischer Film mit echten Commons-Aufnahmen. '
        'Commons-Metadaten allein beweisen nicht, dass das Foto im konkreten Zusammenhang '
        'rechtlich und journalistisch geeignet ist.</p>' +
        "".join(cards) + "</body></html>"
    )
    (output / "review.html").write_text(html, encoding="utf-8")
    return final
