"""SessionMemory: aggregates all sub-memories per session with isolation."""

from app.memory.conversation_memory import ConversationMemory
from app.memory.location_memory import LocationMemory
from app.memory.navigation_memory import NavigationMemory
from app.memory.object_memory import ObjectMemory
from app.memory.ocr_memory import OCRMemory
from app.models.events import (
    BaseEvent,
    LocationEvent,
    NavigationEvent,
    ObjectEvent,
    OCREvent,
)


class SessionMemory:
    """Central session store. Each session_id gets isolated memory."""

    def __init__(self) -> None:
        self.ocr = OCRMemory(max_history=10)
        self.objects = ObjectMemory(max_history=10)
        self.location = LocationMemory(max_history=5)
        self.navigation = NavigationMemory(max_history=5)
        self.conversation = ConversationMemory(max_messages=20)
        self._active_sessions: set[str] = set()

    def is_active(self, session_id: str) -> bool:
        return session_id in self._active_sessions

    def activate(self, session_id: str) -> None:
        self._active_sessions.add(session_id)

    def deactivate(self, session_id: str) -> None:
        self._active_sessions.discard(session_id)
        self.clear(session_id)

    def clear(self, session_id: str) -> None:
        self.ocr.clear(session_id)
        self.objects.clear(session_id)
        self.location.clear(session_id)
        self.navigation.clear(session_id)
        self.conversation.clear(session_id)

    def ingest_event(self, event: BaseEvent) -> None:
        """Route an event to the correct sub-memory."""
        session_id = event.session_id
        self.activate(session_id)
        match event:
            case OCREvent():
                self.ocr.store(session_id, event.payload, event.timestamp)
            case ObjectEvent():
                self.objects.store(session_id, event.payload, event.timestamp)
            case LocationEvent():
                self.location.store(session_id, event.payload, event.timestamp)
            case NavigationEvent():
                self.navigation.store(session_id, event.payload, event.timestamp)

    def get_all_sessions(self) -> list[str]:
        return list(self._active_sessions)
