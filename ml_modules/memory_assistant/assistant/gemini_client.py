"""Gemini API client for generating context-aware responses."""

import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

FALLBACK_REPLY = "Sorry, I'm unable to process that right now. Please try again."

MAX_RETRIES = 3
RETRY_DELAY = 2.0


class GeminiClient:
    """Calls Gemini API to generate conversational responses."""

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key or settings.gemini_api_key
        self.model = model or settings.gemini_model
        self.timeout = settings.gemini_timeout

    def _call_api(self, payload: dict) -> dict:
        """Make API call with retry on 429."""
        url = GEMINI_API_URL.format(model=self.model)
        for attempt in range(MAX_RETRIES):
            response = httpx.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=self.timeout,
            )
            if response.status_code == 429:
                wait = RETRY_DELAY * (attempt + 1)
                logger.warning("Rate limited, retrying in %.1fs...", wait)
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        response.raise_for_status()
        return {}

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Send prompt to Gemini and return the text response."""
        if not self.api_key:
            logger.warning("Gemini API key not configured; returning fallback")
            return FALLBACK_REPLY

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 256,
            },
        }

        try:
            data = self._call_api(payload)
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    return parts[0].get("text", FALLBACK_REPLY).strip()
            return FALLBACK_REPLY
        except httpx.HTTPStatusError as e:
            logger.error("Gemini API HTTP error: %s", e.response.status_code)
            return FALLBACK_REPLY
        except (httpx.RequestError, json.JSONDecodeError, KeyError) as e:
            logger.error("Gemini API call failed: %s", e)
            return FALLBACK_REPLY

    def generate_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Send prompt to Gemini expecting JSON output."""
        if not self.api_key:
            logger.warning("Gemini API key not configured; returning fallback")
            return {"error": "API key not configured"}

        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": user_prompt}]}
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 512,
                "responseMimeType": "application/json",
            },
        }

        try:
            data = self._call_api(payload)
            candidates = data.get("candidates", [])
            if candidates:
                content = candidates[0].get("content", {})
                parts = content.get("parts", [])
                if parts:
                    text = parts[0].get("text", "{}")
                    return json.loads(text)
            return {"error": "No response from Gemini"}
        except (httpx.HTTPStatusError, httpx.RequestError, json.JSONDecodeError, KeyError) as e:
            logger.error("Gemini API JSON call failed: %s", e)
            return {"error": str(e)}
