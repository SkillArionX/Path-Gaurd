"""Object memory: stores recent detected objects per session."""

from collections import defaultdict, deque
from datetime import datetime, timezone

from app.models.events import ObjectPayload
from app.models.memory_models import StoredObject


class ObjectMemory:
    def __init__(self, max_history: int = 10) -> None:
        self._max_history = max_history
        self._recent: dict[str, list[StoredObject]] = {}
        self._history: dict[str, deque[StoredObject]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )

    def store(self, session_id: str, payload: ObjectPayload, timestamp: datetime | None = None) -> list[StoredObject]:
        ts = timestamp or datetime.now(timezone.utc)
        stored_objects = [
            StoredObject(
                object_id=obj.object_id,
                label=obj.label,
                confidence=obj.confidence,
                distance_meters=obj.distance_meters,
                clock_position=obj.clock_position,
                timestamp=ts,
            )
            for obj in payload.objects
        ]
        self._recent[session_id] = stored_objects
        for obj in stored_objects:
            self._history[session_id].append(obj)
        return stored_objects

    def get_recent(self, session_id: str) -> list[StoredObject]:
        return list(self._recent.get(session_id, []))

    def get_history(self, session_id: str) -> list[StoredObject]:
        return list(self._history.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._recent.pop(session_id, None)
        self._history.pop(session_id, None)
