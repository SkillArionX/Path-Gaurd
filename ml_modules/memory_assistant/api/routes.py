"""API routes for the AI Memory & Conversation module."""

import base64
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from ml_modules.memory_assistant.api.schemas import (
    AudioChatRequest,
    AudioChatResponse,
    ChatRequest,
    ChatResponse,
    EventRequest,
    EventResponse,
    SessionResponse,
    TranscriptionResponse,
)
from ml_modules.memory_assistant.assistant.conversation_engine import ConversationEngine
from ml_modules.memory_assistant.models.events import parse_event

logger = logging.getLogger(__name__)

router = APIRouter()

engine = ConversationEngine()


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """Send a text message and receive a text reply."""
    if not request.session_id.strip():
        raise HTTPException(status_code=400, detail="session_id cannot be empty")
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    reply = engine.generate_reply(
        session_id=request.session_id,
        message=request.message,
    )
    return ChatResponse(session_id=request.session_id, reply=reply)


@router.post("/chat/audio", response_model=AudioChatResponse)
async def chat_audio(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
) -> AudioChatResponse:
    """Send an audio message, receive text + audio reply."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    mime_type = audio.content_type or "audio/webm"
    transcription = engine.transcribe_audio(audio_bytes, mime_type)
    if transcription is None:
        raise HTTPException(status_code=422, detail="Could not transcribe audio")

    text_reply, audio_reply = engine.generate_reply_with_audio(session_id, transcription)

    audio_b64 = base64.b64encode(audio_reply).decode() if audio_reply else None
    audio_format = engine.tts.get_audio_format() if audio_reply else None

    return AudioChatResponse(
        session_id=session_id,
        text=text_reply,
        audio_base64=audio_b64,
        audio_format=audio_format,
    )


@router.post("/events", response_model=EventResponse)
def ingest_event(request: EventRequest) -> EventResponse:
    """Ingest an OCR, object, location, or navigation event."""
    try:
        event = parse_event(request.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    engine.process_event(event)
    return EventResponse(status="accepted", session_id=event.session_id)


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_audio(
    session_id: str = Form(...),
    audio: UploadFile = File(...),
) -> TranscriptionResponse:
    """Transcribe audio to text without generating a reply."""
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    mime_type = audio.content_type or "audio/webm"
    text = engine.transcribe_audio(audio_bytes, mime_type)

    return TranscriptionResponse(
        session_id=session_id,
        text=text,
        success=text is not None,
    )


@router.post("/sessions/{session_id}/end", response_model=SessionResponse)
def end_session(session_id: str) -> SessionResponse:
    """End a session and clear its memory."""
    engine.end_session(session_id)
    return SessionResponse(session_id=session_id, status="ended")


@router.get("/sessions/{session_id}/status", response_model=SessionResponse)
def session_status(session_id: str) -> SessionResponse:
    """Check if a session is active."""
    active = engine.is_session_active(session_id)
    return SessionResponse(
        session_id=session_id,
        status="active" if active else "inactive",
    )


