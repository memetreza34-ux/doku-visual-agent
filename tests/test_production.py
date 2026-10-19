"""Render preparation tests: no external APIs and no unapproved asset exports."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from doku_visual_agent.core import Asset
from doku_visual_agent.pipeline import build_plan, save_plan
from doku_visual_agent.production import (
    allocate_frames, checked_media, prepare_render, _verified_chart,
)


def sample_asset():
    return Asset(id="commons:101", provider="commons", kind="photo",
        title="Volkswagen Wolfsburg Werk", description="Volkswagen factory Wolfsburg",
        creator="Archiv", source_url="https://commons.wikimedia.org/wiki/File:Werk.jpg",
        preview_url="", media_url="", license_name="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/", attribution="Archiv")


def fixture_plan():
    plan = build_plan("Das Volkswagen Werk in Wolfsburg wird vorgestellt.",
                      fixture=[sample_asset().__dict__])
    assert plan["scenes"][0]["candidates"]
    return plan


def live_setup(path: Path, *, approved=True, rejected=False):
    plan = fixture_plan()
    plan["mode"] = "LIVE_SEARCH_UNREVIEWED"
    if rejected:
        plan["scenes"][0]["candidates"][0]["review_status"] = "rejected_by_vision"
    save_plan(plan, path)
    approval = [{
        "scene_id": "S01", "asset_id": "commons:101", "role": "exakt",
        "source_url": "https://commons.wikimedia.org/wiki/File:Werk.jpg",
        "license_name": "CC BY 4.0",
        "visual_evidence": "Das konkrete Werk wurde manuell geprüft",
        "license_evidence": "Urheber und Lizenz wurden manuell geprüft",
    }]
    if approved:
        (path / "approvals.json").write_text(json.dumps(approval), encoding="utf-8")
    else:
        (path / "approvals.json").write_text("[]", encoding="utf-8")
    media = path / "input"
    media.mkdir()
    (media / "approved.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 300)
    (media / "voice.wav").write_bytes(b"RIFF" + b"\x00" * 400)
    bindings = path / "bindings.json"
    bindings.write_text(json.dumps({
        "S01": {"asset_id": "commons:101", "file": "approved.jpg"}
    }), encoding="utf-8")
    return media, bindings


class TimelineTests(unittest.TestCase):
    def test_allocate_total_frames_exactly(self):
        scenes = [{"narration": "Drei Worte hier"},
                  {"narration": "Sehr viele Wörter für den zweiten Abschnitt hier."}]
        times = allocate_frames(scenes, total=327, fps=30, timings=None)
        self.assertEqual(sum(times), 327)
        self.assertGreater(times[1], times[0])

    def test_reject_inconsistent_timings(self):
        with self.assertRaisesRegex(ValueError, "Audiodauer"):
            allocate_frames([{"narration": "A"}], 90, 30, [12.0])

    def test_reject_too_short_audio(self):
        with self.assertRaisesRegex(ValueError, "zu kurz"):
            allocate_frames([{"narration": "a"}] * 4, 20, 30, None)


class PrepareRenderTests(unittest.TestCase):
    def test_demo_is_explicitly_watermarked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            save_plan(fixture_plan(), root / "demo")
            output = root / "demo" / "render"
            result = prepare_render(root / "demo", None, None, output, demo=True)
            self.assertTrue(result["demo"])
            self.assertEqual(result["scenes"][0]["kind"], "graphic")
            self.assertIn("DEMO", result["scenes"][0]["label"])
            self.assertEqual(result["durationInFrames"], 90)
            self.assertTrue((output / "props.json").is_file())
            self.assertTrue((output / "credits.json").is_file())

    def test_cannot_export_fixture_as_real(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            save_plan(fixture_plan(), root / "demo")
            with self.assertRaisesRegex(ValueError, "Live-Recherche"):
                prepare_render(root / "demo", root, root / "assets.json",
                               root / "render", voiceover=root / "voice.wav")

    @patch("doku_visual_agent.production.media_probe")
    def test_live_approved_image_and_voiceover_staged(self, probe):
        probe.side_effect = lambda p, audio=False: (
            {"duration": 8.0, "width": 0, "height": 0} if audio
            else {"duration": 0.0, "width": 1920, "height": 1080})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            media,bindings = live_setup(root)
            out=root/"render"
            result=prepare_render(root,media,bindings,out,voiceover=media/"voice.wav")
            self.assertFalse(result["demo"])
            self.assertEqual(result["durationInFrames"], 240)
            self.assertEqual(result["scenes"][0]["kind"], "image")
            self.assertEqual(result["scenes"][0]["label"], "GEPRÜFTE QUELLENAUFNAHME")
            self.assertEqual(result["voiceover"], "media/voiceover.wav")
            self.assertTrue((out/"public"/"media"/"S01.jpg").is_file())
            self.assertTrue((out/"public"/"media"/"voiceover.wav").is_file())
            self.assertTrue(result["scenes"][0]["media_sha256"])

    @patch("doku_visual_agent.production.media_probe")
    def test_missing_approval_blocks_real_video(self, probe):
        probe.return_value={"duration": 8.0, "width": 1920, "height": 1080}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            media,bindings=live_setup(root,approved=False)
            with self.assertRaisesRegex(ValueError, "manuelle Medienfreigabe"):
                prepare_render(root,media,bindings,root/"render",voiceover=media/"voice.wav")

    @patch("doku_visual_agent.production.media_probe")
    def test_vision_rejected_blocks_real_video(self, probe):
        probe.return_value={"duration": 8.0, "width": 1920, "height": 1080}
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            media,bindings=live_setup(root,rejected=True)
            with self.assertRaisesRegex(ValueError, "KI-abgelehnt"):
                prepare_render(root,media,bindings,root/"render",voiceover=media/"voice.wav")

    def test_path_escape_and_symlinks_are_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            root=base/"input"
            root.mkdir()
            (base/"private.jpg").write_bytes(b"\xff\xd8\xff")
            with self.assertRaisesRegex(ValueError, "Unsicherer"):
                checked_media(root, "../private.jpg", {".jpg"}, 1000)
            (root/"unsafe.jpg").symlink_to(base/"private.jpg")
            with self.assertRaises(ValueError):
                checked_media(root, "unsafe.jpg", {".jpg"}, 1000)

    def test_bad_charts_rejected(self):
        scene={"id":"S01","visual_type":"data_graphic"}
        chart={"reviewed":True,"title":"Test","source_url":"https://example.org/report",
               "evidence":"Geschäftsbericht mit Einheiten geprüft",
               "values":[{"label":"2024","value":2},{"label":"2025","value":3}]}
        self.assertEqual(len(_verified_chart(scene,chart)["values"]),2)
        with self.assertRaisesRegex(ValueError,"Quellen"):
            _verified_chart(scene,{**chart,"reviewed":False})
        with self.assertRaisesRegex(ValueError,"ungültige"):
            _verified_chart(scene,{**chart,"values":[
                {"label":"2024","value":-1},{"label":"2025","value":2}]})

    @patch("doku_visual_agent.production.media_probe")
    def test_too_short_broll_rejected(self, probe):
        probe.side_effect=lambda p,audio=False: (
            {"duration":8.0,"width":0,"height":0} if audio else
            {"duration":1.5,"width":1920,"height":1080})
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            media,bindings=live_setup(root)
            (media/"short.mp4").write_bytes(b"\x00"*1000)
            bindings.write_text(json.dumps({"S01":{
                "asset_id":"commons:101","file":"short.mp4"}}))
            with self.assertRaisesRegex(ValueError,"kürzer"):
                prepare_render(root,media,bindings,root/"render",voiceover=media/"voice.wav")

    def test_demo_rejects_real_voiceover(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            save_plan(fixture_plan(),root/"demo")
            with self.assertRaisesRegex(ValueError,"kein echtes Audio"):
                prepare_render(root/"demo",None,None,root/"out",demo=True,
                               voiceover=root/"voice.wav")


if __name__ == "__main__":
    unittest.main()
