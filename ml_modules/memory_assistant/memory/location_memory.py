"""Location memory: stores the latest GPS location per session."""

from collections import defaultdict, deque
from datetime import datetime, timezone

from app.models.events import LocationPayload
from app.models.memory_models import StoredLocation


class LocationMemory:
    def __init__(self, max_history: int = 5) -> None:
        self._max_history = max_history
        self._last: dict[str, StoredLocation] = {}
        self._history: dict[str, deque[StoredLocation]] = defaultdict(
            lambda: deque(maxlen=max_history)
        )

    def store(self, session_id: str, payload: LocationPayload, timestamp: datetime | None = None) -> StoredLocation:
        ts = timestamp or datetime.now(timezone.utc)
        stored = StoredLocation(
            lat=payload.coordinates.lat,
            lng=payload.coordinates.lng,
            accuracy_m=payload.coordinates.accuracy_m,
            place_label=payload.place_label,
            hazard_zone=payload.hazard_zone,
            timestamp=ts,
        )
        self._last[session_id] = stored
        self._history[session_id].append(stored)
        return stored

    def get_last(self, session_id: str) -> StoredLocation | None:
        return self._last.get(session_id)

    def get_history(self, session_id: str) -> list[StoredLocation]:
        return list(self._history.get(session_id, []))

    def clear(self, session_id: str) -> None:
        self._last.pop(session_id, None)
        self._history.pop(session_id, None)
