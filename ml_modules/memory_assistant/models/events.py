"""Event models for incoming module events (OCR, Object, Location, Navigation)."""

from datetime import datetime

from pydantic import BaseModel, Field


class BoundingBox(BaseModel):
    x: int
    y: int
    w: int
    h: int


class OCRPayload(BaseModel):
    detected_text: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    bounding_box: BoundingBox | None = None


class DetectedObject(BaseModel):
    object_id: str
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    distance_meters: float = Field(..., ge=0.0)
    clock_position: str


class ObjectPayload(BaseModel):
    objects: list[DetectedObject] = Field(default_factory=list)


class Coordinates(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    accuracy_m: float = Field(default=0.0, ge=0.0)


class LocationPayload(BaseModel):
    coordinates: Coordinates
    place_label: str = ""
    hazard_zone: bool = False


class NavigationPayload(BaseModel):
    instruction: str
    direction: str
    reason: str
    distance_meters: float = Field(..., ge=0.0)


class BaseEvent(BaseModel):
    event_type: str
    timestamp: datetime
    session_id: str = Field(..., min_length=1)


class OCREvent(BaseEvent):
    event_type: str = Field(default="ocr_scan", pattern="^ocr_scan$")
    payload: OCRPayload


class ObjectEvent(BaseEvent):
    event_type: str = Field(default="object_stream", pattern="^object_stream$")
    payload: ObjectPayload


class LocationEvent(BaseEvent):
    event_type: str = Field(default="location_update", pattern="^location_update$")
    payload: LocationPayload


class NavigationEvent(BaseEvent):
    event_type: str = Field(default="navigation_instruction", pattern="^navigation_instruction$")
    payload: NavigationPayload


EVENT_REGISTRY: dict[str, type[BaseEvent]] = {
    "ocr_scan": OCREvent,
    "object_stream": ObjectEvent,
    "location_update": LocationEvent,
    "navigation_instruction": NavigationEvent,
}


def parse_event(data: dict) -> BaseEvent:
    """Parse raw dict into the correct event model based on event_type."""
    event_type = data.get("event_type", "")
    model = EVENT_REGISTRY.get(event_type)
    if model is None:
        raise ValueError(f"Unknown event type: {event_type}")
    return model.model_validate(data)


