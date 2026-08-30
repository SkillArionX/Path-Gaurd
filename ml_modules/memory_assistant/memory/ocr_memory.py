"""OCR memory: stores detected text results per session."""

from collections import defaultdict, deque
from datetime import datetime, timezone

from app.models.events import OCRPayload
from app.models.memory_models import StoredOCR


class OCRMemory:
    def __init__(self, max_history: int = 10) -> None:
        self._max_history = max_history
        self._last: dict[str, StoredOCR] = {}
        self._history: dict[str, deque[StoredOCR]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )

    def store(self, session_id: str, payload: OCRPayload, timestamp: datetime | None = None) -> StoredOCR:
        ts = timestamp or datetime.now(timezone.utc)
        stored = StoredOCR(
            detected_text=payload.detected_text,
            confidence=payload.confidence,
            timestamp=ts,
        )
        self._last[session_id] = stored
        self._history[session_id].append(stored)
        return stored

    def get_last(self, session_id: str) -> StoredOCR | None:
        return self._last.get(session_id)

    def get_history(self, session_id: str) -> list[StoredOCR]:
        return list(self._history.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._last.pop(session_id, None)
        self._history.pop(session_id, None)
