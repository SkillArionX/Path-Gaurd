"""Conversation memory: stores user/assistant turns per session."""

from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Deque

from ml_modules.memory_assistant.models.memory_models import ConversationTurn


class ConversationMemory:
    def __init__(self, max_messages: int = 20) -> None:
        self.max_messages = max_messages
        self._messages: dict[str, Deque[ConversationTurn]] = defaultdict(
            lambda: deque(maxlen=max_messages)
        )

    def add_turn(self, session_id: str, role: str, content: str, timestamp: datetime | None = None) -> ConversationTurn:
        ts = timestamp or datetime.now(timezone.utc)
        turn = ConversationTurn(role=role, content=content, timestamp=ts)
        self._messages[session_id].append(turn)
        return turn

    def get_recent_turns(self, session_id: str, count: int | None = None) -> list[ConversationTurn]:
        messages = list(self._messages[session_id])
        if count is not None:
            return messages[-count:]
        return messages

    def clear(self, session_id: str) -> None:
        self._messages.pop(session_id, None)

    @property
    def active_sessions(self) -> list[str]:
        return [sid for sid, msgs in self._messages.items() if msgs]


