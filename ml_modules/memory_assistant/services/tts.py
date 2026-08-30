"""Text-to-Speech service interface."""

import logging
from abc import ABC, abstractmethod

from app.config import settings

logger = logging.getLogger(__name__)


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    @abstractmethod
    def synthesize(self, text: str) -> bytes | None:
        """Convert text to audio bytes. Returns None on failure."""
        ...

    @abstractmethod
    def get_audio_format(self) -> str:
        """Return the MIME type of the audio output."""
        ...


class GeminiTTS(TTSProvider):
    """Uses Gemini API for text-to-speech via TTS model."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or settings.gemini_api_key

    def synthesize(self, text: str) -> bytes | None:
        import base64
        import json

        import httpx

        if not self.api_key:
            logger.warning("Gemini API key not configured for TTS")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_tts_model}:generateContent"
        payload = {
            "contents": [
                {"parts": [{"text": text}]}
            ],
            "generationConfig": {
                "responseModalities": ["audio"],
                "audioConfig": {
                    "audioEncoding": "MP3",
                },
            },
        }

        try:
            response = httpx.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    audio_data = part.get("inlineData", {}).get("data", "")
                    if audio_data:
                        return base64.b64decode(audio_data)
            logger.warning("TTS returned no audio data")
            return None
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError) as e:
            logger.error("TTS synthesis failed: %s", e)
            return None

    def get_audio_format(self) -> str:
        return "audio/mpeg"


class EdgeTTS(TTSProvider):
    """Uses edge-tts library for text-to-speech (free, no API key)."""

    def __init__(self, voice: str | None = None) -> None:
        self.voice = voice or settings.tts_voice

    def synthesize(self, text: str) -> bytes | None:
        import asyncio
        import io

        try:
            import edge_tts
        except ImportError:
            logger.error("edge-tts not installed")
            return None

        try:
            communicate = edge_tts.Communicate(text, self.voice)
            audio_buffer = io.BytesIO()

            async def _synthesize():
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_buffer.write(chunk["data"])

            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_synthesize())
            finally:
                loop.close()

            audio_bytes = audio_buffer.getvalue()
            return audio_bytes if audio_bytes else None
        except Exception as e:
            logger.error("Edge TTS synthesis failed: %s", e)
            return None

    def get_audio_format(self) -> str:
        return "audio/mpeg"


class Pyttsx3TTS(TTSProvider):
    """Uses pyttsx3 for local text-to-speech (no API key needed)."""

    def __init__(self, rate: int = 160, volume: float = 1.0) -> None:
        self.rate = rate
        self.volume = volume
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.rate)
            self._engine.setProperty("volume", self.volume)
        return self._engine

    def synthesize(self, text: str) -> bytes | None:
        try:
            engine = self._get_engine()
            engine.say(text)
            engine.runAndWait()
            return None  # pyttsx3 plays audio directly, no bytes returned
        except Exception as e:
            logger.error("pyttsx3 synthesis failed: %s", e)
            return None

    def get_audio_format(self) -> str:
        return "text/plain"


class TextOnlyTTS(TTSProvider):
    """No-op TTS that returns text only (for text-only response mode)."""

    def synthesize(self, text: str) -> bytes | None:
        logger.info("TTS disabled; returning text only")
        return None

    def get_audio_format(self) -> str:
        return "text/plain"


def create_tts_provider() -> TTSProvider:
    """Factory to create the appropriate TTS provider based on config."""
    provider = settings.tts_provider.lower()
    if provider == "gemini":
        return GeminiTTS()
    elif provider == "edge":
        return EdgeTTS()
    elif provider == "pyttsx3":
        return Pyttsx3TTS()
    elif provider == "text_only":
        return TextOnlyTTS()
    else:
        logger.warning("Unknown TTS provider '%s', using text-only", provider)
        return TextOnlyTTS()
