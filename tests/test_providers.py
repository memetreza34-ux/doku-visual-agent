import unittest
from unittest.mock import patch

from doku_visual_agent.providers import Commons, Pexels, FixtureSource, ProviderError, plain
from doku_visual_agent.report import render_html, safe_https


class ProviderTests(unittest.TestCase):
    def test_pexels_no_key(self):
        with self.assertRaises(ProviderError):
            Pexels("").search("factory", "pexels_photos")

    @patch("doku_visual_agent.providers.get_json")
    def test_pexels_photo_parsing(self, get_json):
        get_json.return_value = {"photos": [{
            "id": 5, "url": "https://www.pexels.com/photo/robot-5/",
            "alt": "automotive factory robot", "photographer": "Test Photographer",
            "src": {"medium": "https://images.pexels.com/5.jpg",
                    "original": "https://images.pexels.com/original.jpg"},
            "width": 1920, "height": 1080,
        }]}
        pictures = Pexels("token").search("factory", "pexels_photos")
        self.assertEqual(len(pictures), 1)
        self.assertEqual(pictures[0].creator, "Test Photographer")
        self.assertEqual(pictures[0].license_name, "Pexels License")

    @patch("doku_visual_agent.providers.get_json")
    def test_pexels_new_video_endpoint(self, get_json):
        get_json.return_value = {"videos": [{
            "id": 8, "url": "https://www.pexels.com/video/car-factory-8/",
            "video_pictures": [{"picture": "https://images.pexels.com/thumbnail.jpg"}],
            "video_files": [{"quality": "hd", "link": "https://video.pexels.com/8.mp4"}]
        }]}
        video = Pexels("token").search("car production", "pexels_videos")[0]
        self.assertEqual(video.kind, "video")
        self.assertEqual(video.media_url, "https://video.pexels.com/8.mp4")

    @patch("doku_visual_agent.providers.get_json")
    def test_commons_metadata(self, get_json):
        get_json.return_value = {"query": {"pages": [{
            "title": "File:Volkswagen factory 1960.jpg", "pageid": 12,
            "imageinfo": [{
                "url": "https://upload.wikimedia.org/factory.jpg",
                "thumburl": "https://upload.wikimedia.org/thumb.jpg",
                "descriptionurl": "https://commons.wikimedia.org/wiki/File:Volkswagen_factory_1960.jpg",
                "width": 1000, "height": 700,
                "extmetadata": {
                    "Artist": {"value": "<span>Jane &amp; John</span>"},
                    "LicenseShortName": {"value": "CC BY-SA 4.0"},
                    "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"}
                }
            }]
        }]}}
        a = Commons().search("Volkswagen 1960")[0]
        self.assertEqual(a.creator, "Jane & John")
        self.assertEqual(a.license_name, "CC BY-SA 4.0")
        self.assertTrue(a.extra["license_review_required"])

    def test_html_injection_escaped(self):
        plan = {"mode": "LIVE_SEARCH_UNREVIEWED", "warnings": [],
                "scenes": [{"id": "S01", "visual_type": "<script>alert(1)</script>",
                            "narration": "<img src=x onerror=alert(1)>",
                            "guidance": "", "search_tasks": [], "candidates": []}]}
        html = render_html(plan)
        self.assertNotIn("<script>alert(1)</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertEqual(safe_https("javascript:alert(1)"), "")

    def test_plain_html(self):
        self.assertEqual(plain("<div>CC&nbsp;BY</div>"), "CC BY")


if __name__ == "__main__":
    unittest.main()
