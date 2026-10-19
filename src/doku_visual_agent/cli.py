"""CLI for evidence-first documentary shotlist research."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .pipeline import approve_asset, build_plan, save_plan
from .report import save_html


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doku-visual-agent",
                                     description="Doku-Bildsuche mit manueller Fakten-/Lizenzkontrolle.")
    subs = parser.add_subparsers(dest="command", required=True)
    plan = subs.add_parser("plan", help="Suchplan + HTML-Sichtung erzeugen")
    plan.add_argument("--script", type=Path, required=True)
    plan.add_argument("--output", type=Path, required=True)
    plan.add_argument("--fixture", type=Path,
                      help="Nur Test/Demo: lokale künstliche Bilddaten statt Internet.")
    approve = subs.add_parser("approve", help="Manuell geprüften Treffer protokollieren")
    approve.add_argument("--run", type=Path, required=True)
    approve.add_argument("--scene", required=True)
    approve.add_argument("--asset", required=True)
    approve.add_argument("--role", choices=["exakt", "symbolbild"], required=True)
    approve.add_argument("--license-evidence", required=True)
    approve.add_argument("--visual-evidence", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    try:
        if args.command == "plan":
            script = args.script.read_text(encoding="utf-8")
            fixture = json.loads(args.fixture.read_text(encoding="utf-8")) if args.fixture else None
            if fixture is not None and not isinstance(fixture, list):
                raise ValueError("Fixture muss eine JSON-Liste von Asset-Objekten sein.")
            report = build_plan(script, pexels_key=os.getenv("PEXELS_API_KEY", ""),
                                fixture=fixture)
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
        path = approve_asset(args.run, args.scene, args.asset, args.role,
                             args.license_evidence, args.visual_evidence)
        print(f"Manuell dokumentiert: {path}")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
