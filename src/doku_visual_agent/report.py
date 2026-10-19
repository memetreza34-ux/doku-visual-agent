"""Read-only visual review board, escaped HTML and safe remote preview URLs."""

from __future__ import annotations

from html import escape
from pathlib import Path
from urllib.parse import urlparse


def h(value: object) -> str:
    return escape(str(value), quote=True)


def safe_https(url: object) -> str:
    value = str(url or "")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return ""
    return h(value)


def render_html(plan: dict) -> str:
    parts = []
    for scene in plan["scenes"]:
        items = []
        for item in scene["candidates"]:
            asset = item["asset"]
            src = safe_https(asset.get("preview_url"))
            image = (f'<img loading="lazy" referrerpolicy="no-referrer" alt="Ungeprüfte Vorschau" src="{src}">'
                     if src else '<div class="placeholder">Keine Vorschau</div>')
            source = safe_https(asset["source_url"])
            licence = safe_https(asset.get("license_url"))
            items.append(
                '<article class="asset">' + image +
                f'<h4>{h(asset["title"])}</h4>' +
                f'<p><strong>{h(item["usage_label"])}</strong> · {h(asset["provider"])} / {h(asset["kind"])}</p>' +
                f'<p>{h(item["why"])} · Score (nur Metadaten): {h(item["metadata_score"])}</p>' +
                f'<p>Urheber: {h(asset["creator"] or "unbekannt")} · Lizenzangabe: {h(asset["license_name"])}</p>' +
                f'<p><a href="{source}" target="_blank" rel="noopener noreferrer">Originalquelle</a>' +
                (f' · <a href="{licence}" target="_blank" rel="noopener noreferrer">Lizenz</a>' if licence else '') +
                f'</p><p class="id">Asset-ID: {h(asset["id"])}</p>' +
                '<p class="warning">NICHT FREIGEGEBEN – Bildinhalt, Rechte und Kontext prüfen.</p></article>'
            )
        if not items:
            items.append('<p class="empty">Kein passender Recherchetreffer. Bitte weitere Quellen suchen '
                         'oder eine belegte eigene Grafik konzipieren; kein beliebiges Stockbild einsetzen.</p>')
        query_text = "; ".join(f'{x["provider"]}: {x["query"]}' for x in scene["search_tasks"])
        parts.append(
            f'<section><h2>{h(scene["id"])} · {h(scene["visual_type"])}</h2>'
            f'<blockquote>{h(scene["narration"])}</blockquote>'
            f'<p><b>Visual-Regel:</b> {h(scene["guidance"])}</p>'
            f'<p class="small"><b>Suchaufträge:</b> {h(query_text or "Keine: Datenbeleg für Diagramm erforderlich")}</p>'
            f'<div class="assets">{"".join(items)}</div></section>'
        )
    warnings = "".join(f"<li>{h(w)}</li>" for w in plan["warnings"])
    demo = " – KÜNSTLICHE DEMODATEN, KEINE BILDNACHWEISE" if plan["mode"].startswith("OFFLINE") else ""
    return (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Doku Visual Agent · Sichtung</title>'
        '<style>'
        'body{background:#0e1420;color:#e9eef7;font:16px system-ui,sans-serif;max-width:1180px;margin:auto;padding:28px}'
        'h1{font-size:30px}h2{font-size:22px;margin:0 0 12px}h4{margin:12px 0 5px}'
        'p{line-height:1.5}a{color:#8ed4fa}section{background:#172235;border:1px solid #394c62;'
        'border-radius:14px;margin:24px 0;padding:22px}'
        '.assets{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:15px}'
        '.asset{background:#101b2d;border:1px solid #35495b;border-radius:10px;padding:12px;overflow:hidden}'
        'img{width:100%;height:145px;object-fit:cover;background:#263449}'
        '.small,.id{color:#b0c4d4;font-size:12px;overflow-wrap:anywhere}'
        '.warning,.empty{color:#ffcb86;font-weight:600}'
        '.notice{padding:12px;border-left:4px solid #f0b45a;background:#33291f}'
        'blockquote{border-left:3px solid #81a2bd;margin:0;padding:8px 16px}'
        '</style></head><body>'
        f'<h1>Doku Visual Agent – Rechercheprüfung{h(demo)}</h1>'
        '<p class="notice">KEIN MATERIAL AUTOMATISCH FREIGEGEBEN. '
        'Relevanzscore basiert ausschließlich auf Textmetadaten; Bilder, Fakten und Rechte manuell prüfen.</p>'
        '<p>Stock-Material mit Bezug zu Unternehmen ist ggf. nur ein Symbolbild. '
        'Offizielle Pexels-API: <a href="https://www.pexels.com/">Pexels</a>.</p>'
        f'{"".join(parts)}'
        f'<h2>Suchwarnungen</h2><ul>{warnings or "<li>Keine vom Suchsystem gemeldet</li>"}</ul>'
        '</body></html>'
    )


def save_html(plan: dict, output: Path) -> None:
    (output / "review.html").write_text(render_html(plan), encoding="utf-8")
