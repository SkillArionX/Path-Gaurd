"""Prompt builder: constructs prompts with only relevant context for Gemini."""

from ml_modules.memory_assistant.models.memory_models import ConversationContext

SYSTEM_PROMPT = """You are the Path Guard voice assistant for visually impaired users.
Answer using the provided context.
Be concise, natural, and easy to understand when spoken aloud.
If the required information is not available in the current context, say that clearly.
Do not invent information.
Keep responses short and suitable for text-to-speech output.
Do not use markdown, JSON, bullet points, or special formatting."""


class PromptBuilder:
    """Builds prompts containing only the relevant session context."""

    def build_system_prompt(self) -> str:
        return SYSTEM_PROMPT

    def build_user_prompt(
        self,
        context: ConversationContext,
        message: str,
        relevance: dict[str, bool] | None = None,
    ) -> str:
        """Build user prompt with only relevant context sections."""
        sections: list[str] = []

        if relevance is None:
            relevance = {
                "ocr": True,
                "objects": True,
                "location": True,
                "navigation": True,
                "conversation": True,
            }

        if relevance.get("conversation") and context.recent_messages:
            recent = context.recent_messages[-6:]
            turns = []
            for t in recent:
                prefix = "User" if t.role == "user" else "Assistant"
                turns.append(f"{prefix}: {t.content}")
            sections.append("Recent conversation:\n" + "\n".join(turns))

        if relevance.get("ocr"):
            if context.last_ocr:
                sections.append(
                    f"Latest scanned text: \"{context.last_ocr.detected_text}\" "
                    f"(confidence: {context.last_ocr.confidence:.0%})"
                )
            if context.recent_ocr_history:
                prior = context.recent_ocr_history[-3:-1]
                if prior:
                    items = [f"\"{o.detected_text}\"" for o in prior]
                    sections.append("Earlier scanned texts: " + ", ".join(items))

        if relevance.get("objects") and context.recent_objects:
            descs = []
            for obj in context.recent_objects[-5:]:
                descs.append(
                    f"{obj.label} at {obj.clock_position}, "
                    f"{obj.distance_meters}m away"
                )
            sections.append("Detected objects: " + "; ".join(descs))

        if relevance.get("navigation") and context.last_navigation:
            nav = context.last_navigation
            sections.append(
                f"Latest navigation: \"{nav.instruction}\" "
                f"(reason: {nav.reason}, direction: {nav.direction}, "
                f"distance: {nav.distance_meters}m)"
            )

        if relevance.get("location") and context.last_location:
            loc = context.last_location
            loc_parts = [f"place: \"{loc.place_label}\""]
            if loc.hazard_zone:
                loc_parts.append("WARNING: hazard zone")
            sections.append("Current location: " + ", ".join(loc_parts))

        context_block = "\n\n".join(sections) if sections else "No relevant context available."

        return f"CONTEXT:\n{context_block}\n\nUSER QUESTION:\n{message}"


