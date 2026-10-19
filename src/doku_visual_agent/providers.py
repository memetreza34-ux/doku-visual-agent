"""Official source adapters; no scraping, unauthorized downloads, or fabricated licenses."""

from __future__ import annotations

from html import unescape
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .core import Asset


class ProviderError(RuntimeError):
    pass


def get_json(url: str, *, headers: dict[str, str] | None = None,
             timeout: int = 15) -> dict[str, Any]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "DokuVisualAgent/0.1 (research; contact via GitHub repository)",
                      "Accept": "application/json", **(headers or {})},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if int(response.headers.get("Content-Length", "0")) > 5_000_000:
                raise ProviderError("Antwort zu groß.")
            data = response.read(5_000_001)
            if len(data) > 5_000_000:
                raise ProviderError("Antwort zu groß.")
            result = json.loads(data)
            if not isinstance(result, dict):
                raise ProviderError("API lieferte unerwartetes JSON.")
            return result
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"API-Anfrage fehlgeschlagen: {exc}") from exc


class Pexels:
    def __init__(self, key: str):
        self.key = key.strip()

    def search(self, query: str, kind: str, limit: int = 6) -> list[Asset]:
        if not self.key:
            raise ProviderError("PEXELS_API_KEY fehlt; Pexels-Suche übersprungen.")
        if kind not in ("pexels_photos", "pexels_videos"):
            raise ValueError(f"Unbekannte Pexels-Kategorie: {kind}")
        path = "v1/search" if kind == "pexels_photos" else "v1/videos/search"
        url = ("https://api.pexels.com/" + path + "?" +
               urllib.parse.urlencode({"query": query, "per_page": min(limit, 20),
                                       "orientation": "landscape"}))
        payload = get_json(url, headers={"Authorization": self.key})
        assets: list[Asset] = []
        for obj in payload.get("photos" if kind == "pexels_photos" else "videos", []):
            if not isinstance(obj, dict) or not obj.get("id"):
                continue
            video = kind == "pexels_videos"
            page_url = str(obj.get("url") or "")
            # Video search has no reliable alt text. URL slug is a weak metadata hint.
            slug = urllib.parse.unquote(page_url.rstrip("/").split("/")[-1])
            title = str(obj.get("alt") or re.sub(r"-\d+$", "", slug).replace("-", " "))
            if video:
                preview = next((str(x.get("picture")) for x in obj.get("video_pictures", [])
                                if isinstance(x, dict) and x.get("picture")), "")
                variants = [f for f in obj.get("video_files", []) if isinstance(f, dict)]
                hd = next((f for f in variants if f.get("quality") == "hd"), None)
                media = str((hd or (variants[0] if variants else {})).get("link") or "")
                creator = str((obj.get("user") or {}).get("name") or "")
                kind_name = "video"
            else:
                src = obj.get("src") or {}
                preview = str(src.get("medium") or src.get("small") or "")
                media = str(src.get("original") or "")
                creator = str(obj.get("photographer") or "")
                kind_name = "photo"
            if not page_url.startswith("https://"):
                continue
            assets.append(Asset(
                id=f"pexels:{kind_name}:{obj['id']}", provider="pexels",
                kind=kind_name, title=title, description="",
                creator=creator, source_url=page_url,
                preview_url=preview, media_url=media,
                license_name="Pexels License", license_url="https://www.pexels.com/license/",
                attribution=f"{creator} / Pexels" if creator else "Pexels",
                width=int(obj.get("width") or 0), height=int(obj.get("height") or 0),
            ))
        return assets


def plain(value: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]*>", " ", value))).strip()


def meta(ex: dict[str, Any], field: str) -> str:
    entry = ex.get(field) or {}
    if not isinstance(entry, dict):
        return ""
    return plain(str(entry.get("value") or ""))


class Commons:
    def search(self, query: str, kind: str = "commons", limit: int = 6) -> list[Asset]:
        if kind != "commons":
            raise ValueError("Wikimedia Commons akzeptiert nur die Kategorie commons.")
        params = {
            "action": "query", "generator": "search", "gsrsearch": query,
            "gsrnamespace": 6, "gsrlimit": min(limit, 10),
            "prop": "imageinfo", "iiprop": "url|size|extmetadata",
            "iiurlwidth": 460, "format": "json", "formatversion": 2,
        }
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
        data = get_json(url)
        results: list[Asset] = []
        for page in (data.get("query") or {}).get("pages", []):
            if not isinstance(page, dict):
                continue
            infos = page.get("imageinfo") or []
            if not infos or not isinstance(infos[0], dict):
                continue
            info = infos[0]
            media_url = str(info.get("url") or "")
            mime = str(info.get("mime") or "")
            if not media_url.startswith("https://"):
                continue
            # No SVG/vector/other files in Phase 1 preview; Commons search still may return them.
            if not re.search(r"\.(jpg|jpeg|png|webp)(?:\?|$)", media_url, re.I):
                continue
            ex = info.get("extmetadata") or {}
            if not isinstance(ex, dict):
                ex = {}
            title = str(page.get("title", "")).removeprefix("File:").replace("_", " ")
            license_name = meta(ex, "LicenseShortName") or "UNKNOWN"
            license_url = meta(ex, "LicenseUrl")
            creator = meta(ex, "Artist") or meta(ex, "Attribution")
            description = meta(ex, "ImageDescription")[:350]
            page_url = str(info.get("descriptionurl") or "")
            if not page_url.startswith("https://"):
                page_url = "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(
                    str(page.get("title") or "").replace(" ", "_"), safe=":_()")
            results.append(Asset(
                id=f"commons:{page.get('pageid')}", provider="commons", kind="photo",
                title=title, description=description, creator=creator,
                source_url=page_url,
                preview_url=str(info.get("thumburl") or media_url),
                media_url=media_url,
                license_name=license_name, license_url=license_url,
                attribution=f"{creator} – {title}" if creator else title,
                width=int(info.get("width") or 0), height=int(info.get("height") or 0),
                extra={"license_review_required": True},
            ))
        return results


class FixtureSource:
    """Deterministic, intentionally fake local data for tests/demo only."""

    def __init__(self, assets: list[dict[str, Any]]):
        self.assets = [Asset(**{**item, "demo_only": True}) for item in assets]

    def search(self, query: str, kind: str, limit: int = 6) -> list[Asset]:
        provider = "commons" if kind == "commons" else "pexels"
        media = None if kind == "commons" else ("photo" if kind == "pexels_photos" else "video")
        return [asset for asset in self.assets
                if asset.provider == provider and (media is None or asset.kind == media)][:limit]
