"""Memory and context models used across the module."""

from datetime import datetime

from pydantic import BaseModel, Field


class StoredOCR(BaseModel):
    detected_text: str
    confidence: float
    timestamp: datetime


class StoredObject(BaseModel):
    object_id: str
    label: str
    confidence: float
    distance_meters: float
    clock_position: str
    timestamp: datetime


class StoredLocation(BaseModel):
    lat: float
    lng: float
    accuracy_m: float
    place_label: str
    hazard_zone: bool
    timestamp: datetime


class StoredNavigation(BaseModel):
    instruction: str
    direction: str
    reason: str
    distance_meters: float
    timestamp: datetime


class ConversationTurn(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime


class ConversationContext(BaseModel):
    session_id: str
    recent_messages: list[ConversationTurn] = Field(default_factory=list)
    last_ocr: StoredOCR | None = None
    recent_ocr_history: list[StoredOCR] = Field(default_factory=list)
    recent_objects: list[StoredObject] = Field(default_factory=list)
    last_location: StoredLocation | None = None
    last_navigation: StoredNavigation | None = None


