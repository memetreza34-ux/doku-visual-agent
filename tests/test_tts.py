import base64
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from doku_visual_agent.tts import TTSError, build_tts_request, extract_wav, save_tts, tts_gemini


def fake_wav():
    return b"RIFF" + b"\x00" * 4 + b"WAVE" + b"\x00" * 2028


class TTSTests(unittest.TestCase):
    def test_request_uses_exact_text_and_style_separately(self):
        text="Dies ist eine überprüfte deutsche Dokumentation mit klarer Stimme."
        p=build_tts_request(text, "Kore", "gemini-3.8-flash-tts")
        assert p["input"][0]["content"][0]["text"] == text
        assert p["response_format"]["mime_type"] == "audio/wav"
        self.assertIn("speech_metadata",str(p))

    def test_blocks_invalid_voice_model_and_text(self):
        with self.assertRaisesRegex(TTSError,"Modell"):
            build_tts_request("X"*60,"Kore","../../something")
        with self.assertRaisesRegex(TTSError,"Stimmname"):
            build_tts_request("X"*60,"../../secret","gemini-3.8-flash-tts")
        with self.assertRaisesRegex(TTSError,"25"):
            build_tts_request("short","Kore","gemini-3.8-flash-tts")

    def test_missing_audio_and_wrong_container_fail(self):
        with self.assertRaisesRegex(TTSError,"keine Audiodaten"):
            extract_wav({"steps":[]})
        payload={"steps":[{"type":"model_output",
            "content":[{"type":"audio","data":base64.b64encode(b"RIFF" + b"\x00"*1100).decode()}]}]}
        with self.assertRaisesRegex(TTSError,"keine WAV"):
            extract_wav(payload)

    def test_extracts_latest_model_audio(self):
        payload={"steps":[{"type":"model_output",
            "content":[{"type":"audio","data":base64.b64encode(fake_wav()).decode()}]}]}
        self.assertEqual(extract_wav(payload),fake_wav())

    def test_api_key_not_echoed_on_network_error(self):
        import urllib.error
        with patch("doku_visual_agent.tts.urllib.request.urlopen",
                   side_effect=urllib.error.URLError("something failed")):
            with self.assertRaises(TTSError) as exc:
                tts_gemini("Ein deutscher Testtext mit ausreichender Länge zum Vertonen.",
                           "sk-private-secret")
            self.assertNotIn("sk-private-secret",str(exc.exception))

    def test_mocked_full_tts_and_save(self):
        data=json.dumps({"steps":[{"type":"model_output",
            "content":[{"type":"audio","data":base64.b64encode(fake_wav()).decode()}]}]}).encode()
        class Resp:
            def __enter__(self): return self
            def __exit__(self,*a): return False
            def read(self,n): return data
        with patch("doku_visual_agent.tts.urllib.request.urlopen",return_value=Resp()):
            with tempfile.TemporaryDirectory() as d:
                p=Path(d)/"script.txt";p.write_text("Das ist eine korrekt vertonte deutsche Doku.",encoding="utf-8")
                target=save_tts(p,Path(d)/"voice.wav","temporary-key")
                self.assertEqual(target.read_bytes(),fake_wav())


if __name__=="__main__":
    unittest.main()
