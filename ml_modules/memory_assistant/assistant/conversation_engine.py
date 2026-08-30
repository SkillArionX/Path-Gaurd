"""ConversationEngine: orchestrates STT, context, Gemini, and TTS pipeline."""

import logging

from ml_modules.memory_assistant.assistant.gemini_client import GeminiClient
from ml_modules.memory_assistant.assistant.prompt_builder import PromptBuilder
from ml_modules.memory_assistant.context.context_manager import ContextManager
from ml_modules.memory_assistant.memory.session_memory import SessionMemory
from ml_modules.memory_assistant.services.stt import STTProvider, create_stt_provider
from ml_modules.memory_assistant.services.tts import TTSProvider, create_tts_provider

logger = logging.getLogger(__name__)

FALLBACK_REPLY = "Sorry, I don't have enough context to answer that."


class ConversationEngine:
    """End-to-end conversation pipeline."""

    def __init__(
        self,
        context_manager: ContextManager | None = None,
        gemini_client: GeminiClient | None = None,
        stt_provider: STTProvider | None = None,
        tts_provider: TTSProvider | None = None,
    ) -> None:
        self.session_memory = SessionMemory()
        self.context_manager = context_manager or ContextManager(self.session_memory)
        self.gemini = gemini_client or GeminiClient()
        self.prompt_builder = PromptBuilder()
        self.stt = stt_provider or create_stt_provider()
        self.tts = tts_provider or create_tts_provider()

    def process_event(self, event) -> None:
        """Ingest an incoming event into session memory."""
        self.context_manager.ingest_event(event)

    def generate_reply(self, session_id: str, message: str) -> str:
        """Generate a text reply for the user's message using relevant context."""
        try:
            context = self.context_manager.get_context(session_id)
            relevance = self.context_manager.classify_query(session_id, message)
            system_prompt = self.prompt_builder.build_system_prompt()
            user_prompt = self.prompt_builder.build_user_prompt(context, message, relevance)

            reply = self.gemini.generate(system_prompt, user_prompt)

            self.context_manager.remember_exchange(session_id, message, reply)
            return reply
        except Exception as e:
            logger.error("Failed to generate reply for session %s: %s", session_id, e)
            return FALLBACK_REPLY

    def generate_reply_with_audio(self, session_id: str, message: str) -> tuple[str, bytes | None]:
        """Generate text reply and optional audio output."""
        text_reply = self.generate_reply(session_id, message)
        audio = self.tts.synthesize(text_reply)
        return text_reply, audio

    def transcribe_audio(self, audio_data: bytes, mime_type: str = "audio/webm") -> str | None:
        """Transcribe audio to text using the configured STT provider."""
        try:
            return self.stt.transcribe(audio_data, mime_type)
        except Exception as e:
            logger.error("STT transcription failed: %s", e)
            return None

    def end_session(self, session_id: str) -> None:
        """Clear all memory for a session."""
        self.context_manager.end_session(session_id)

    def is_session_active(self, session_id: str) -> bool:
        return self.session_memory.is_active(session_id)


