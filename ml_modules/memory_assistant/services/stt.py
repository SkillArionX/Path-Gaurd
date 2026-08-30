"""Speech-to-Text service interface."""

import logging
from abc import ABC, abstractmethod

from ml_modules.memory_assistant.config import settings

logger = logging.getLogger(__name__)


class STTProvider(ABC):
    """Abstract base class for STT providers."""

    @abstractmethod
    def transcribe(self, audio_data: bytes, mime_type: str = "audio/webm") -> str | None:
        """Transcribe audio bytes to text. Returns None on failure."""
        ...


class GeminiSTT(STTProvider):
    """Uses Gemini API for speech-to-text via audio understanding."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_stt_model

    def transcribe(self, audio_data: bytes, mime_type: str = "audio/webm") -> str | None:
        """Transcribe audio using Gemini's multimodal capabilities."""
        import base64
        import json

        import httpx

        if not self.api_key:
            logger.warning("Gemini API key not configured for STT")
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
        audio_b64 = base64.b64encode(audio_data).decode("utf-8")
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": audio_b64,
                            }
                        },
                        {"text": "Transcribe this audio exactly as spoken. Return only the transcription text, nothing else."},
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.0,
                "maxOutputTokens": 1024,
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
                if parts:
                    text = parts[0].get("text", "").strip()
                    if text:
                        logger.info("STT transcription successful")
                        return text
            logger.warning("STT returned empty transcription")
            return None
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError) as e:
            logger.error("STT transcription failed: %s", e)
            return None


class LocalSTT(STTProvider):
    """Fallback STT that wraps any local whisper-like model."""

    def __init__(self, model_name: str = "base") -> None:
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                import whisper
                self._model = whisper.load_model(self.model_name)
            except ImportError:
                logger.error("whisper not installed; local STT unavailable")
                raise
        return self._model

    def transcribe(self, audio_data: bytes, mime_type: str = "audio/webm") -> str | None:
        import tempfile
        import os

        try:
            model = self._load_model()
            suffix = ".webm" if "webm" in mime_type else ".wav"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            try:
                result = model.transcribe(tmp_path)
                text = result.get("text", "").strip()
                return text if text else None
            finally:
                os.unlink(tmp_path)
        except Exception as e:
            logger.error("Local STT failed: %s", e)
            return None


def create_stt_provider() -> STTProvider:
    """Factory to create the appropriate STT provider based on config."""
    provider = settings.stt_provider.lower()
    if provider == "gemini":
        return GeminiSTT()
    elif provider == "local":
        return LocalSTT(model_name=settings.stt_local_model)
    else:
        logger.warning("Unknown STT provider '%s', falling back to Gemini", provider)
        return GeminiSTT()


