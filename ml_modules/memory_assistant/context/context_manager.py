"""Context manager: builds relevant context and resolves references."""

from app.memory.session_memory import SessionMemory
from app.models.memory_models import ConversationContext, ConversationTurn


# Reference words that imply the user is pointing to something in context
REFERENCE_WORDS = {
    "it", "this", "that", "there", "here", "that one",
}

CONTEXTUAL_PHRASES = {
    "the medicine": "ocr",
    "the drug": "ocr",
    "the text": "ocr",
    "what did you see": "ocr",
    "where was it": "ocr",
    "the object": "objects",
    "what is around": "objects",
    "what is nearby": "objects",
    "the object": "objects",
    "what is that": "any",
    "where am i": "location",
    "where am i?": "location",
    "my location": "location",
    "the location": "location",
    "hazard": "location",
    "move": "navigation",
    "why did you tell me": "navigation",
    "navigate": "navigation",
    "direction": "navigation",
    "go left": "navigation",
    "go right": "navigation",
    "what should i do": "navigation",
}


class ContextManager:
    def __init__(self, session_memory: SessionMemory | None = None) -> None:
        self.session_memory = session_memory or SessionMemory()

    def ingest_event(self, event) -> None:
        """Forward events to session memory."""
        self.session_memory.ingest_event(event)

    def get_context(self, session_id: str) -> ConversationContext:
        """Build the full conversation context for a session."""
        sm = self.session_memory
        last_ocr = sm.ocr.get_last(session_id)
        recent_ocr = sm.ocr.get_history(session_id)
        recent_objects = sm.objects.get_recent(session_id)
        last_location = sm.location.get_last(session_id)
        last_navigation = sm.navigation.get_last(session_id)
        recent_turns = sm.conversation.get_recent_turns(session_id)

        return ConversationContext(
            session_id=session_id,
            recent_messages=recent_turns,
            last_ocr=last_ocr,
            recent_ocr_history=recent_ocr,
            recent_objects=recent_objects,
            last_location=last_location,
            last_navigation=last_navigation,
        )

    def classify_query(self, session_id: str, message: str) -> dict[str, bool]:
        """Determine which context sources are relevant for this query."""
        lower = message.lower().strip()
        relevance = {
            "ocr": False,
            "objects": False,
            "location": False,
            "navigation": False,
            "conversation": True,
        }

        for phrase, source in CONTEXTUAL_PHRASES.items():
            if phrase in lower:
                if source == "any":
                    relevance["ocr"] = True
                    relevance["objects"] = True
                    relevance["location"] = True
                    relevance["navigation"] = True
                else:
                    relevance[source] = True

        words = set(lower.split())
        if words & REFERENCE_WORDS:
            relevance["conversation"] = True
            if last_ocr_text := self.session_memory.ocr.get_last(session_id):
                relevance["ocr"] = True
            if self.session_memory.objects.get_recent(session_id):
                relevance["objects"] = True

        if not any(v for k, v in relevance.items() if k != "conversation"):
            relevance["ocr"] = True
            relevance["objects"] = True
            relevance["location"] = True
            relevance["navigation"] = True

        return relevance

    def remember_exchange(self, session_id: str, user_message: str, assistant_reply: str) -> None:
        """Store a conversation turn."""
        self.session_memory.conversation.add_turn(session_id, "user", user_message)
        self.session_memory.conversation.add_turn(session_id, "assistant", assistant_reply)

    def end_session(self, session_id: str) -> None:
        """Clear all memory for a session."""
        self.session_memory.deactivate(session_id)
