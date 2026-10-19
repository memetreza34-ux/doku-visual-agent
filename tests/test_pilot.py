"""No-network tests for the Volkswagen Commons pilot and its safety gates."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from doku_visual_agent.pilot import (
    PilotError, validate_manifest, verify_metadata,
    write_narration, prepare_pilot, download_photo,
)

MANIFEST = json.loads((Path(__file__).resolve().parent.parent / "examples" /
                       "vw_wolfsburg_pilot.json").read_text(encoding="utf-8"))


def fake_info(scene):
    name = scene["expected_license"]
    license_slug = {
        "CC BY 4.0": "by/4.0",
        "CC BY-SA 4.0": "by-sa/4.0",
        "CC BY-SA 2.0": "by-sa/2.0",
    }[name]
    return {
        "width": 1600, "height": 900,
        "descriptionurl": ("https://commons.wikimedia.org/wiki/" +
                           scene["commons_title"].replace(" ", "_")),
        "thumburl": "https://upload.wikimedia.org/wikipedia/commons/thumb/foo/bar.jpg/1600px-bar.jpg",
        "extmetadata": {
            "LicenseShortName": {"value": name},
            "LicenseUrl": {"value": "https://creativecommons.org/licenses/" + license_slug + "/"},
            "Artist": {"value": "<a>" + scene["expected_author"] + "</a>"},
        }
    }


class PilotTests(unittest.TestCase):
    def test_curated_manifest_is_valid(self):
        self.assertEqual(len(validate_manifest(MANIFEST)["scenes"]), 6)
        self.assertEqual(sum(s["kind"] == "photo" for s in MANIFEST["scenes"]), 4)

    def test_no_fictitious_or_duplicate_files(self):
        copy_m = copy.deepcopy(MANIFEST)
        copy_m["scenes"][2]["commons_title"] = copy_m["scenes"][0]["commons_title"]
        with self.assertRaisesRegex(PilotError, "nicht eindeutig"):
            validate_manifest(copy_m)

    def test_source_required_for_every_line(self):
        copy_m = copy.deepcopy(MANIFEST)
        copy_m["scenes"][1]["fact_source_urls"] = []
        with self.assertRaisesRegex(PilotError, "Faktenquellen"):
            validate_manifest(copy_m)

    def test_unknown_licenses_rejected(self):
        copy_m = copy.deepcopy(MANIFEST)
        copy_m["scenes"][0]["expected_license"] = "Copyright-free"
        with self.assertRaisesRegex(PilotError, "Creative-Commons"):
            validate_manifest(copy_m)

    def test_voice_script_from_real_source_notes(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "manifest.json"
            src.write_text(json.dumps(MANIFEST, ensure_ascii=False), encoding="utf-8")
            path = write_narration(src, Path(td) / "pilot")
            text = path.read_text(encoding="utf-8")
            self.assertIn("Stammwerk", text)
            self.assertIn("Käferproduktion", text)
            self.assertIn("zweitausendvierundzwanzig", text)

    def test_photo_metadata_checks_author_and_license(self):
        scene = MANIFEST["scenes"][0]
        verified = verify_metadata(scene, fake_info(scene))
        self.assertEqual(verified["author"], "Jorge Franganillo")
        self.assertIn("commons.wikimedia.org", verified["source_page"])
        wrong = fake_info(scene)
        wrong["extmetadata"]["LicenseShortName"]["value"] = "All rights reserved"
        with self.assertRaisesRegex(PilotError, "Lizenzangabe"):
            verify_metadata(scene, wrong)
        wrong = fake_info(scene)
        wrong["extmetadata"]["Artist"]["value"] = "Unknown"
        with self.assertRaisesRegex(PilotError, "Autorennachweis"):
            verify_metadata(scene, wrong)

    def test_bogus_media_host_blocked(self):
        scene = MANIFEST["scenes"][0]
        bogus = fake_info(scene)
        bogus["thumburl"] = "https://localhost/secret.jpg"
        with self.assertRaisesRegex(PilotError, "Wikimedia CDN"):
            verify_metadata(scene, bogus)

    def test_photo_download_rejects_non_image(self):
        class Resp:
            headers = {"Content-Length": "200"}
            def geturl(self):
                return "https://upload.wikimedia.org/wikipedia/commons/test.jpg"
            def read(self, n):
                return b"<html>blocked</html>"
            def __enter__(self): return self
            def __exit__(self, *args): return False
        class Opener:
            def open(self, *a, **kw): return Resp()
        with patch("doku_visual_agent.pilot.urllib.request.build_opener",
                   return_value=Opener()):
            with self.assertRaisesRegex(PilotError, "kein JPEG"):
                download_photo("https://upload.wikimedia.org/wikipedia/commons/test.jpg")

    @patch("doku_visual_agent.pilot.media_probe")
    @patch("doku_visual_agent.pilot.download_photo")
    @patch("doku_visual_agent.pilot.commons_imageinfo")
    def test_real_photo_staging_keeps_publication_gate(self, metadata, image, probe):
        lookup = {s["commons_title"]: s for s in MANIFEST["scenes"]
                  if s["kind"] == "photo"}
        metadata.side_effect = lambda title: fake_info(lookup[title])
        image.return_value = b"\xff\xd8\xff" + b"\x00" * 1024
        probe.return_value = {"duration": 60.0}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            manifest = root / "manifest.json"
            manifest.write_text(json.dumps(MANIFEST, ensure_ascii=False), encoding="utf-8")
            audio = root / "narration.wav"
            audio.write_bytes(b"RIFF" + b"\x00" * 100)
            output = root / "render"
            props = prepare_pilot(manifest, output, audio)
            self.assertTrue(props["demo"])
            self.assertFalse(props["publication_ready"])
            self.assertTrue(props["rights_review_required"])
            self.assertEqual(props["durationInFrames"], 1800)
            self.assertEqual(len(props["scenes"]), 6)
            credits = json.loads((output / "credits.json").read_text())
            self.assertEqual(len(credits), 4)
            self.assertTrue(all(x["manual_license_review_complete"] is False
                                for x in credits))
            self.assertTrue((output / "public" / "media" / "S01.jpg").exists())
            self.assertTrue((output / "public" / "media" / "narration.wav").exists())

    def test_will_not_use_wrong_file_type_as_narration(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / "manifest.json"
            path.write_text(json.dumps(MANIFEST, ensure_ascii=False), encoding="utf-8")
            (root / "narration.mp3").write_bytes(b"fake")
            with self.assertRaisesRegex(PilotError, "Sprachdatei"):
                prepare_pilot(path, root / "render", root / "narration.mp3")


if __name__ == "__main__":
    unittest.main()
