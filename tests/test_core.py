import unittest

from doku_visual_agent.core import Asset, inspect_candidate, make_scenes, select_candidates, tokens
from doku_visual_agent.pipeline import approve_asset, build_plan, save_plan
from pathlib import Path
import tempfile


def asset(asset_id="commons:1", provider="commons", kind="photo", title="Volkswagen Werk Wolfsburg 1960"):
    return Asset(
        id=asset_id, provider=provider, kind=kind, title=title, description="factory",
        creator="Test", source_url="https://example.org/item", preview_url="",
        media_url="", license_name="CC BY 4.0", license_url="https://creativecommons.org/licenses/by/4.0/",
    )


class PlanningTests(unittest.TestCase):
    def test_normalization(self):
        self.assertIn("volkswagen", tokens("VW und Volkswagen"))
        self.assertIn("factory", tokens("Autofabrik und Werke"))

    def test_scene_types(self):
        scenes = make_scenes("Volkswagen Werk in Wolfsburg.\n\nDie Produktion nutzt Industrieroboter.\n\n"
                             "Im Jahr 1960 war die Produktion anders.\n\nUmsatz und Gewinn.")
        self.assertEqual([s.visual_type for s in scenes],
                         ["specific_location", "generic_broll", "archive", "data_graphic"])
        self.assertEqual(scenes[0].entity, "Volkswagen")
        self.assertEqual(len(scenes[-1].tasks), 0)

    def test_cannot_use_bmw_to_represent_vw(self):
        scene = make_scenes("Das Volkswagen Werk in Wolfsburg produziert Fahrzeuge.")[0]
        self.assertIsNone(inspect_candidate(scene, asset(title="BMW factory Munich")))
        self.assertIsNotNone(inspect_candidate(scene, asset()))

    def test_no_generic_stock_for_specific_location(self):
        scene = make_scenes("Das Volkswagen Werk in Wolfsburg produziert Fahrzeuge.")[0]
        self.assertIsNone(inspect_candidate(scene, asset("pexels:4", "pexels", "photo",
                                                          "Volkswagen Wolfsburg factory")))

    def test_no_assets_for_unverified_graph(self):
        scene = make_scenes("Volkswagen verzeichnet Gewinne und Umsätze.")[0]
        self.assertIsNone(inspect_candidate(scene, asset()))

    def test_invalid_source_url_is_rejected(self):
        scene = make_scenes("Das Volkswagen Werk in Wolfsburg produziert Fahrzeuge.")[0]
        candidate = asset()
        candidate = candidate.__class__(**{**candidate.__dict__, "source_url": "javascript:alert(1)"})
        self.assertIsNone(inspect_candidate(scene, candidate))

    def test_dedupe(self):
        scene = make_scenes("Volkswagen betreibt das Werk Wolfsburg.")[0]
        seen = set()
        self.assertEqual(len(select_candidates(scene, [asset(), asset()], already_seen=seen)), 1)
        self.assertEqual(len(select_candidates(scene, [asset()], already_seen=seen)), 0)

    def test_demo_flag_and_absence_of_publication(self):
        example = asset()
        plan = build_plan("Volkswagen Werk in Wolfsburg.", fixture=[example.__dict__])
        self.assertEqual(plan["mode"], "OFFLINE_DEMO_NOT_REAL_MEDIA")
        self.assertFalse(plan["publication_ready"])
        self.assertEqual(plan["scenes"][0]["candidates"][0]["review_status"], "pending")

    def test_no_demo_approval(self):
        plan = build_plan("Volkswagen Werk in Wolfsburg.", fixture=[asset().__dict__])
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            save_plan(plan, run)
            with self.assertRaisesRegex(ValueError, "Offline"):
                approve_asset(run, "S01", "commons:1", "exakt",
                              "License documented in source",
                              "Verified in original photograph")

    def test_specific_scene_blocks_symbol_photo_approval(self):
        # No network access in unit tests: simulate live-mode data from a local fixture.
        plan = build_plan("Volkswagen Werk in Wolfsburg.", fixture=[asset().__dict__])
        plan["mode"] = "LIVE_SEARCH_UNREVIEWED"
        plan["scenes"][0]["candidates"] = [
            {"asset": asset().__dict__, "review_status": "pending"}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            save_plan(plan, run)
            with self.assertRaisesRegex(ValueError, "Konkrete"):
                approve_asset(run, "S01", "commons:1", "symbolbild",
                              "License documented in source",
                              "Verified in original photograph")

    def test_empty_input(self):
        with self.assertRaises(ValueError):
            make_scenes(" \n  ")


if __name__ == "__main__":
    unittest.main()
