import os
from abc import ABC, abstractmethod
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class VisionProvider(ABC):

    @abstractmethod
    def describe_scene(self, frame: Any) -> str:
        pass

    @abstractmethod
    def answer_question(self, frame: Any, question: str) -> str:
        pass


class ConfiguredVisionProvider(VisionProvider):

    def __init__(self):
        provider = os.getenv("AI_PROVIDER", "qwen").lower()

        if provider == "qwen":
            from ml_modules.scene_understanding.modules import qwen_client
            self.client = qwen_client

        elif provider == "gemini":
            from ml_modules.scene_understanding.modules import gemini_client
            self.client = gemini_client

        elif provider == "groq":
            from ml_modules.scene_understanding.modules import groq_client
            self.client = groq_client

        else:
            raise ValueError(
                f"Unsupported AI_PROVIDER: {provider}. "
                f"Use 'qwen', 'gemini', or 'groq'."
            )

        self.provider = provider

    def describe_scene(self, frame: Any) -> str:
        return self.client.describe_scene(frame)

    def answer_question(self, frame: Any, question: str) -> str:
        return self.client.answer_question(frame, question)
