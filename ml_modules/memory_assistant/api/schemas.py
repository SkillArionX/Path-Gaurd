"""API request/response schemas."""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    session_id: str
    reply: str


class AudioChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1)


class AudioChatResponse(BaseModel):
    session_id: str
    text: str
    audio_base64: str | None = None
    audio_format: str | None = None


class EventRequest(BaseModel):
    event_type: str = Field(..., min_length=1)
    timestamp: str
    session_id: str = Field(..., min_length=1)
    payload: dict


class EventResponse(BaseModel):
    status: str = "accepted"
    session_id: str


class SessionResponse(BaseModel):
    session_id: str
    status: str


class TranscriptionResponse(BaseModel):
    session_id: str
    text: str | None
    success: bool
