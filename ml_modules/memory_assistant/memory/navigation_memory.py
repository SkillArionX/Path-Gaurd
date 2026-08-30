"""Navigation memory: stores the latest navigation instruction per session."""

from collections import defaultdict, deque
from datetime import datetime, timezone

from ml_modules.memory_assistant.models.events import NavigationPayload
from ml_modules.memory_assistant.models.memory_models import StoredNavigation


class NavigationMemory:
    def __init__(self, max_history: int = 5) -> None:
        self._max_history = max_history
        self._last: dict[str, StoredNavigation] = {}
        self._history: dict[str, deque[StoredNavigation]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )

    def store(self, session_id: str, payload: NavigationPayload, timestamp: datetime | None = None) -> StoredNavigation:
        ts = timestamp or datetime.now(timezone.utc)
        stored = StoredNavigation(
            instruction=payload.instruction,
            direction=payload.direction,
            reason=payload.reason,
            distance_meters=payload.distance_meters,
            timestamp=ts,
        )
        self._last[session_id] = stored
        self._history[session_id].append(stored)
        return stored

    def get_last(self, session_id: str) -> StoredNavigation | None:
        return self._last.get(session_id)

    def get_history(self, session_id: str) -> list[StoredNavigation]:
        return list(self._history.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._last.pop(session_id, None)
        self._history.pop(session_id, None)


