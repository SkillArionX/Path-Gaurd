"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Path Guard AI Memory"
    api_prefix: str = "/api"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_stt_model: str = "gemini-2.5-flash"
    gemini_tts_model: str = "gemini-2.5-flash-preview-tts"
    gemini_timeout: float = 15.0

    stt_provider: str = "gemini"
    stt_local_model: str = "base"

    tts_provider: str = "edge"
    tts_voice: str = "en-US-GuyNeural"

    max_conversation_turns: int = 20
    max_ocr_history: int = 10
    max_object_history: int = 10
    max_location_history: int = 5
    max_navigation_history: int = 5

    model_config = {"env_prefix": "PATHGUARD_", "env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
