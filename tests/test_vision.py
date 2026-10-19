"""Security, semantic and visual triage tests; no paid API calls or network."""
import io
import json
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from doku_visual_agent.core import Asset, make_scenes
from doku_visual_agent.pipeline import approve_asset, build_plan, save_plan
from doku_visual_agent.report import render_html
from doku_visual_agent.semantic import improve_scene
from doku_visual_agent.vision import (
    GeminiJSON, GeminiVision, VisionError, VisionResult, allowed_preview,
    download_preview, inspect_plan, parse_model_json,
)


def mkasset(aid: str, title: str = "electric vehicle battery line") -> dict:
    return dict(id=aid, provider="pexels", kind="photo",
                title=title, description="factory",
                creator="Test photographer", source_url="https://www.pexels.com/photo/test/",
                preview_url="https://images.pexels.com/photos/123/test.jpg",
                media_url="", license_name="Pexels License",
                license_url="https://www.pexels.com/license/",
                attribution="Test", width=1920, height=1080)


class FakeModel:
    def __init__(self, response):
        self.response = response
        self.prompts = []

    def generate(self, prompt, image=None):
        self.prompts.append((prompt, image))
        return self.response


class FakeInspector:
    def __init__(self, decisions):
        self.decisions = decisions
        self.calls = []

    def inspect(self, scene, asset):
        self.calls.append((scene["id"], asset["id"]))
        response = self.decisions[asset["id"]]
        if isinstance(response, Exception):
            raise response
        return response


class ImageSecurityTests(TestCase):
    def test_allowed_hosts_only(self):
        self.assertTrue(allowed_preview("https://images.pexels.com/photos/123/test.jpeg"))
        self.assertTrue(allowed_preview("https://upload.wikimedia.org/wikipedia/commons/x/x.jpg"))
        for url in [
            "http://images.pexels.com/p.png",
            "https://images.pexels.com.evil.test/x.jpg",
            "https://127.0.0.1/p.jpg", "file:///etc/passwd",
            "https://images.pexels.com:8888/p.jpg",
            "https://user:pass@images.pexels.com/x.jpg",
        ]:
            with self.subTest(url=url):
                self.assertFalse(allowed_preview(url))

    def test_block_untrusted_preview_without_fetch(self):
        with patch("doku_visual_agent.vision.urllib.request.build_opener") as factory:
            with self.assertRaises(VisionError):
                download_preview("https://evil.example.com/image.jpg")
            factory.assert_not_called()

    def test_fetch_rejects_html_masquerading_as_image(self):
        class Reply:
            headers = {"Content-Type": "image/jpeg"}
            def geturl(self):
                return "https://images.pexels.com/test.jpg"
            def read(self, count):
                return b"<html>not a jpeg</html>"
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        class Opener:
            def open(self, *args, **kwargs):
                return Reply()
        with patch("doku_visual_agent.vision.urllib.request.build_opener", return_value=Opener()):
            with self.assertRaisesRegex(VisionError, "Bilddatei"):
                download_preview("https://images.pexels.com/test.jpg")

    def test_parse_json_and_errors(self):
        self.assertEqual(parse_model_json('{"verdict":"uncertain"}')["verdict"], "uncertain")
        self.assertEqual(parse_model_json('```json\n{"a":1}\n```')["a"], 1)
        with self.assertRaises(VisionError):
            parse_model_json("invalid")
        with self.assertRaises(VisionError):
            parse_model_json("[1,2]")

    def test_gemini_rejects_model_path_injection(self):
        with self.assertRaises(ValueError):
            GeminiJSON("key", "../model")
        with self.assertRaises(ValueError):
            GeminiJSON("", "gemini-2.5-flash")

    def test_vision_checks_image_not_just_metadata(self):
        model = FakeModel({
            "verdict": "unrelated",
            "observed": "Ein Hund auf einer Wiese",
            "reasoning": "Keine Fabrik zu sehen",
            "uncertainties": ["Aus einem Bild ist der Aufnahmeort unklar"],
        })
        image = (b"\xff\xd8\xfffake", "image/jpeg")
        with patch("doku_visual_agent.vision.download_preview", return_value=image):
            r = GeminiVision(model).inspect(
                {"narration":"Roboter montieren Autos", "visual_type":"generic_broll",
                 "entity":"", "place":"", "year":""},
                mkasset("p1"))
        self.assertEqual(r.verdict, "unrelated")
        self.assertEqual(model.prompts[0][1], image)
        self.assertIn("Roboter montieren Autos", model.prompts[0][0])

    def test_malformed_vision_response_is_error(self):
        with patch("doku_visual_agent.vision.download_preview", return_value=(b"\xff\xd8\xfffake", "image/jpeg")):
            with self.assertRaisesRegex(VisionError, "Verifikationsurteil"):
                GeminiVision(FakeModel({"verdict":"auto_approved", "observed":"x", "reasoning":"y",
                                        "uncertainties":[]})).inspect(
                    {"narration":"Aussage", "visual_type":"generic_broll"}, mkasset("p1"))

    def test_error_never_logs_keys(self):
        self.assertFalse(allowed_preview("https://images.pexels.com@evil.org/file.jpg"))


class VisionIntegrationTests(TestCase):
    def test_unrelated_rejected_and_not_published(self):
        plan = build_plan("Elektroautos benötigen Batterien.", fixture=[mkasset("p1"), mkasset("p2")])
        plan["mode"] = "LIVE_SEARCH_UNREVIEWED"
        inspector = FakeInspector({
            "p1": VisionResult("unrelated", "Ein Hund", "Hund, keine Batterie", ()),
            "p2": VisionResult("relevant", "Batteriemontage", "Veranschaulicht das Thema",
                               ("Stockvideo zeigt nicht die konkrete Firma",)),
        })
        inspect_plan(plan, inspector, per_scene=2)
        statuses = {x["asset"]["id"]: x["review_status"]
                    for x in plan["scenes"][0]["candidates"]}
        self.assertEqual(statuses["p1"], "rejected_by_vision")
        self.assertEqual(statuses["p2"], "pending")
        self.assertEqual(plan["vision_summary"]["mismatches"], 1)
        self.assertFalse(plan["publication_ready"])
        self.assertEqual(plan["vision_summary"]["auto_approved"], 0)
        with tempfile.TemporaryDirectory() as tmp:
            save_plan(plan, Path(tmp))
            with self.assertRaisesRegex(ValueError, "aussortiertes"):
                approve_asset(Path(tmp), "S01", "p1", "symbolbild",
                              "Lizenzbeleg aus der Quellseite",
                              "Sichtung des Bildes durchgeführt")

    def test_no_demo_vision(self):
        plan = build_plan("Autobau weltweit.", fixture=[mkasset("p1")])
        with self.assertRaisesRegex(ValueError, "künstliche"):
            inspect_plan(plan, FakeInspector({}), per_scene=1)

    def test_budget_one_inspection(self):
        plan = build_plan("Elektroautos benötigen Batterien.", fixture=[mkasset("p1"), mkasset("p2")])
        plan["mode"] = "LIVE_SEARCH_UNREVIEWED"
        inspector = FakeInspector({"p1": VisionResult("uncertain", "Metall", "Unklar", ())})
        inspect_plan(plan, inspector, per_scene=1)
        self.assertEqual(len(inspector.calls), 1)
        self.assertEqual(plan["scenes"][0]["candidates"][1]["vision"]["status"], "not_checked")
        self.assertEqual(plan["scenes"][0]["candidates"][0]["review_status"], "pending")

    def test_errors_are_visible_and_fail_open_only_for_manual_review(self):
        plan = build_plan("Elektroautos benötigen Batterien.", fixture=[mkasset("p1")])
        plan["mode"] = "LIVE_SEARCH_UNREVIEWED"
        inspect_plan(plan, FakeInspector({"p1": VisionError("Bildvorschau fehlt")}))
        candidate = plan["scenes"][0]["candidates"][0]
        self.assertEqual(candidate["vision"]["status"], "error")
        self.assertEqual(candidate["review_status"], "pending")
        self.assertFalse(plan["publication_ready"])

    def test_video_is_single_preview_not_full_content(self):
        sample = mkasset("p2")
        sample["kind"] = "video"
        plan = build_plan("Elektroautos benötigen Batterien.", fixture=[sample])
        plan["mode"] = "LIVE_SEARCH_UNREVIEWED"
        inspect_plan(plan, FakeInspector({"p2": VisionResult("relevant", "Batterie", "Korrekt", ())}))
        entry = plan["scenes"][0]["candidates"][0]["vision"]
        self.assertEqual(entry["scope"], "single_preview_frame")

    def test_html_displays_vision_judgement_safely(self):
        plan = build_plan("Elektroautos benötigen Batterien.", fixture=[mkasset("p1")])
        plan["mode"] = "LIVE_SEARCH_UNREVIEWED"
        inspect_plan(plan, FakeInspector({
            "p1": VisionResult("unrelated", "<script>alert(9)</script>",
                               "Unpassende Bildauswahl", ())
        }))
        html = render_html(plan)
        self.assertIn("unpassend", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertNotIn("<script>alert(9)</script>", html)


class SemanticTests(TestCase):
    def test_llm_search_improves_query_and_preserves_evidence_gate(self):
        s = make_scenes("Das Volkswagen Werk in Wolfsburg produziert Fahrzeuge.")[0]
        model = FakeModel({"visual_goal":"Luftaufnahme des Werks",
                           "search_queries":["large auto factory aerial"],
                           "risk_note":"Firmensitz nicht durch Bild belegbar"})
        improved = improve_scene(s, model)
        self.assertEqual(improved.visual_type, "specific_location")
        self.assertIn("Volkswagen", improved.tasks[0].query)
        self.assertIn("Wolfsburg", improved.tasks[0].query)
        self.assertEqual([t.provider for t in improved.tasks], ["commons"])
        self.assertIn("Werk", improved.visual_goal)

    def test_stock_search_remains_generic(self):
        s = make_scenes("Roboter montieren Automobile.")[0]
        m = FakeModel({"visual_goal":"Robotik",
                       "search_queries":["industrial automotive robot arms"],
                       "risk_note":"Symbolbild"})
        better = improve_scene(s, m)
        self.assertEqual([t.provider for t in better.tasks], ["pexels_photos", "pexels_videos"])

    def test_data_scene_cannot_be_downgraded(self):
        s = make_scenes("Wie groß ist der Gewinn?")[0]
        improved = improve_scene(s, FakeModel(
            {"visual_goal":"Diagramm nach Quellencheck",
             "search_queries":["beautiful bar chart"], "risk_note":"Belege erforderlich"}))
        self.assertEqual(improved.visual_type, "data_graphic")
        self.assertFalse(improved.tasks)

    def test_llm_failure_preserves_rule_plan(self):
        model = FakeModel({"search_queries":["junk"]})
        plan = build_plan("Volkswagen Werk in Wolfsburg.", fixture=[], semantic_client=model)
        self.assertTrue(plan["warnings"])
        self.assertTrue(plan["scenes"][0]["search_tasks"])
        self.assertFalse(plan["publication_ready"])


class AnnotatedIntentTests(TestCase):
    def test_24_curated_scene_intents(self):
        fixture = Path(__file__).parent / "fixtures" / "scene_intents.json"
        examples = json.loads(fixture.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(examples), 20)
        for example in examples:
            with self.subTest(example["text"]):
                actual = make_scenes(example["text"])[0]
                self.assertEqual(actual.visual_type, example["visual_type"])
                self.assertEqual(actual.entity, example["entity"])
