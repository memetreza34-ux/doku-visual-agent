"""Opt-in natural narration via Google Gemini's documented audio Interactions API.

No API keys are stored in files or logs. This module does not claim that generated
speech perfectly reproduces the transcript; editorial listening is mandatory.
"""
from __future__ import annotations

import base64
import binascii
import json
from pathlib import Path
import re
import urllib.error
import urllib.request
from typing import Any

TTS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
SUPPORTED_MODELS = {"gemini-3.8-flash-tts", "gemini-3.8-flash-lite-tts"}
MAX_RESPONSE_BYTES = 35_000_000
MAX_AUDIO_BYTES = 24_000_000


class TTSError(ValueError):
    pass


def build_tts_request(transcript: str, voice: str, model: str) -> dict[str, Any]:
    if model not in SUPPORTED_MODELS:
        raise TTSError("Nicht unterstütztes TTS-Modell.")
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{1,60}", voice):
        raise TTSError("Ungültiger Stimmname.")
    if not isinstance(transcript, str) or not 25 <= len(transcript.strip()) <= 6500:
        raise TTSError("Sprechertext benötigt 25–6500 Zeichen.")
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", transcript):
        raise TTSError("Sprechertext enthält ungültige Steuerzeichen.")
    return {
        "model": model,
        "input": [{"type": "user_input", "content": [{
            "type": "text", "text": transcript.strip(),
            "annotations": [{"type": "speech_metadata",
                             "style": ("Professional German documentary narration: "
                                       "natural, calm, clear, engaging; do not add or "
                                       "omit words, no dramatization.")}],
        }]}],
        "response_format": {"type": "audio", "mime_type": "audio/wav"},
        "generation_config": {"speech_config": [{"voice": voice}]},
    }


def extract_wav(data: dict[str, Any]) -> bytes:
    if not isinstance(data, dict):
        raise TTSError("Gemini-TTS lieferte ungültiges JSON.")
    audios = []
    for step in data.get("steps", []):
        if not isinstance(step, dict) or step.get("type") != "model_output":
            continue
        for part in step.get("content", []):
            if isinstance(part, dict) and part.get("type") == "audio" and part.get("data"):
                audios.append(part["data"])
    if not audios:
        raise TTSError("Gemini-TTS lieferte keine Audiodaten.")
    try:
        decoded = base64.b64decode(audios[-1], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise TTSError("Gemini-TTS lieferte ungültiges Base64.") from exc
    if len(decoded) > MAX_AUDIO_BYTES or len(decoded) < 1024:
        raise TTSError("Gemini-TTS-Audio außerhalb des erlaubten Rahmens.")
    if decoded[:4] != b"RIFF" or decoded[8:12] != b"WAVE":
        raise TTSError("Gemini-TTS lieferte keine WAV-Datei.")
    return decoded


def tts_gemini(transcript: str, api_key: str, *,
               voice: str = "Kore", model: str = "gemini-3.8-flash-tts") -> bytes:
    if not api_key.strip():
        raise TTSError("GEMINI_API_KEY fehlt.")
    payload = build_tts_request(transcript, voice, model)
    req = urllib.request.Request(
        TTS_URL, method="POST", data=json.dumps(payload).encode("utf-8"),
        headers={"x-goog-api-key": api_key.strip(),
                 "Content-Type": "application/json",
                 "User-Agent": "DokuVisualAgent/0.3; opt-in TTS"},
    )
    try:
        with urllib.request.urlopen(req, timeout=100) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise TTSError("Gemini-TTS-Antwort zu groß.")
        parsed = json.loads(raw)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        # Important: don't echo request headers or remote response data containing sensitive info.
        raise TTSError("TTS-Anfrage fehlgeschlagen; API-Schlüssel, Modell und Kontingent prüfen.") from exc
    except (ValueError, TypeError) as exc:
        raise TTSError("TTS-Anfrage lieferte ungültiges JSON.") from exc
    return extract_wav(parsed)


def save_tts(transcript_path: Path, output: Path, api_key: str, *,
             voice: str = "Kore", model: str = "gemini-3.8-flash-tts") -> Path:
    if output.suffix.lower() != ".wav":
        raise TTSError("Ziel muss auf .wav enden.")
    content = transcript_path.read_text(encoding="utf-8")
    raw = tts_gemini(content, api_key, voice=voice, model=model)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return output
