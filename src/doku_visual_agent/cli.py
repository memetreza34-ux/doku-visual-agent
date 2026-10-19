"""CLI for evidence-first documentary shotlist research."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .pipeline import approve_asset, build_plan, save_plan
from .production import prepare_render
from .scriptwriter import generate_script, save_draft
from .pilot import write_narration, prepare_pilot
from .report import save_html
from .vision import GeminiJSON, GeminiVision, inspect_plan


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doku-visual-agent",
                                     description="Doku-Bildsuche mit manueller Fakten-/Lizenzkontrolle.")
    subs = parser.add_subparsers(dest="command", required=True)
    plan = subs.add_parser("plan", help="Suchplan + HTML-Sichtung erzeugen")
    plan.add_argument("--script", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--vision", action="store_true", help="Echte Bilder mit Gemini prüfen (API-Kosten möglich)")
    plan.add_argument("--semantic", action="store_true", help="LLM-gestützte Szenensuche (API-Kosten möglich)")
    plan.add_argument("--vision-per-scene", type=int, default=3)
    plan.add_argument("--max-vision-total", type=int, default=20,
                      help="Maximale Gemini-Bildanfragen insgesamt (1-100)")
    plan.add_argument("--gemini-model", default="gemini-2.5-flash")
    plan.add_argument("--fixture", type=Path,
                      help="Nur Test/Demo: lokale künstliche Bilddaten statt Internet.")
    approve = subs.add_parser("approve", help="Manuell geprüften Treffer protokollieren")
    approve.add_argument("--run", type=Path, required=True)
    approve.add_argument("--scene", required=True)
    approve.add_argument("--asset", required=True)
    approve.add_argument("--role", choices=["exakt", "symbolbild"], required=True)
    approve.add_argument("--license-evidence", required=True)
    approve.add_argument("--visual-evidence", required=True)
    production = subs.add_parser("prepare-render", help="Freigegebene Visuals und Stimme für Remotion aufbereiten")
    production.add_argument("--run", type=Path, required=True)
    production.add_argument("--output", type=Path, required=True)
    production.add_argument("--assets", type=Path, help="JSON Bindings aus Szenen-ID -> freigegebenes Asset")
    production.add_argument("--media-root", type=Path, help="Lokaler Ordner rechtmäßig verfügbarer Mediendateien")
    production.add_argument("--voiceover", type=Path, help="Sprecherdatei (MP3, WAV, M4A)")
    production.add_argument("--timings", type=Path, help="Optionale geprüfte Szenendauern in Sekunden als JSON")
    production.add_argument("--demo", action="store_true", help="Nur Offline-Fixture: grafische DEMO ohne reale Medien")
    production.add_argument("--fps", type=int, default=30)
    draft = subs.add_parser("draft-script", help="Quellengebundenen KI-Skriptentwurf erstellen")
    draft.add_argument("--brief", type=Path, required=True, help="Textdatei mit Thema und Story-Winkel")
    draft.add_argument("--sources", type=Path, required=True, help="Manuell geprüfte Faktennotizen als JSON")
    draft.add_argument("--output", type=Path, required=True)
    draft.add_argument("--gemini-model", default="gemini-2.5-flash")
    pilot_script = subs.add_parser("pilot-script", help="Quellenkuratiertes Wolfsburg-Demo-Skript ausgeben")
    pilot_script.add_argument("--manifest", type=Path, required=True)
    pilot_script.add_argument("--output", type=Path, required=True)
    pilot_build = subs.add_parser("pilot-prepare", help="Echte Commons-Fotos und Audiostimme in einen Pilot-Render packen")
    pilot_build.add_argument("--manifest", type=Path, required=True)
    pilot_build.add_argument("--output", type=Path, required=True)
    pilot_build.add_argument("--voiceover", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        if args.command == "plan":
            script = args.script.read_text(encoding="utf-8")
            fixture = json.loads(args.fixture.read_text(encoding="utf-8")) if args.fixture else None
            if fixture is not None and not isinstance(fixture, list):
                raise ValueError("Fixture muss eine JSON-Liste von Asset-Objekten sein.")
            if args.vision and fixture is not None:
                raise ValueError("Visionanalyse ist für künstliche Demo-Assets gesperrt.")
            api_key = os.getenv("GEMINI_API_KEY", "")
            gemini = GeminiJSON(api_key, args.gemini_model) if (args.vision or args.semantic) else None
            report = build_plan(script, pexels_key=os.getenv("PEXELS_API_KEY", ""),
                                fixture=fixture,
                                semantic_client=gemini if args.semantic else None,
                                vision_enabled=args.vision)
            if args.vision:
                report = inspect_plan(report, GeminiVision(gemini), args.vision_per_scene, args.max_vision_total)
            save_plan(report, args.output)
            save_html(report, args.output)
            print(f"Erstellt: {args.output / 'plan.json'}")
            print(f"Erstellt: {args.output / 'review.html'}")
            print(f"Modus: {report['mode']}; Szenen: {len(report['scenes'])}")
            print(f"Offene Szenen: {sum(s['state'] != 'manual_review_needed' for s in report['scenes'])}")
            if report["warnings"]:
                print("Hinweise:")
                for warning in report["warnings"]:
                    print(f" - {warning}")
            return 0
        if args.command == "pilot-script":
            path = write_narration(args.manifest, args.output)
            print(f"Sprechskript: {path}")
            print("PILOT: historische Quellen, keine aktuellen Unternehmensnachrichten.")
            return 0
        if args.command == "pilot-prepare":
            props = prepare_pilot(args.manifest, args.output, args.voiceover)
            print(f"Bild-Timeline: {args.output / 'props.json'}")
            print(f"Rechtejournal: {args.output / 'credits.json'}")
            print(f"Gesamtdauer (geschätzt): {props['durationInFrames'] / props['fps']:.1f} s")
            print("NICHT VERÖFFENTLICHEN: Bildrechte und exakte Zuordnung nicht abschließend geprüft.")
            return 0
        if args.command == "draft-script":
            key = os.getenv("GEMINI_API_KEY", "")
            writer = GeminiJSON(key, args.gemini_model, max_output_tokens=3600)
            brief = args.brief.read_text(encoding="utf-8")
            sources = json.loads(args.sources.read_text(encoding="utf-8"))
            draft = generate_script(brief, sources, writer)
            save_draft(draft, args.output)
            print(f"Entwurf: {args.output / 'draft_script.txt'}")
            print(f"Quellenmappe: {args.output / 'draft_evidence.json'}")
            print("WICHTIG: Fakten und Originalquellen redaktionell prüfen.")
            return 0
        if args.command == "prepare-render":
            manifest = prepare_render(
                args.run, args.media_root, args.assets, args.output,
                voiceover=args.voiceover, timings_file=args.timings,
                demo=args.demo, fps=args.fps)
            print(f"Timeline: {args.output / 'props.json'}")
            print(f"Media: {args.output / 'public'}")
            print(f"Szenen: {len(manifest['scenes'])}; Bilder/Rechte: {'Demo' if args.demo else 'Manuell geprüft'}")
            print(f"Synchronisation: {manifest['timing_quality']}")
            return 0
        path = approve_asset(args.run, args.scene, args.asset, args.role,
                             args.license_evidence, args.visual_evidence)
        print(f"Manuell dokumentiert: {path}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
