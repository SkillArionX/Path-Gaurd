"""
Path Guard Integration Layer.

Connects independent Path Guard modules without modifying
their internal implementations.

Connected modules:
    - Cloud Vision
    - Navigation
    - Memory Assistant
    - OCR

IMPORTANT:
    This file is only the integration layer.

    Navigation files are NOT modified.
    Memory Assistant files are NOT modified.
    OCR files are NOT modified.
"""


from typing import Any


# ============================================================
# CLOUD / VISION
# ============================================================

from ml_modules.cloud_integration.vision_provider import (
    ConfiguredVisionProvider,
)

from ml_modules.cloud_integration.scene_bridge import (
    parse_qwen_scene,
)


# ============================================================
# NAVIGATION
# ============================================================

# Existing Navigation adapter.
# We only use it here.
from ml_modules.navigation.scene_adapter import (
    parse_scene_understanding_output,
)

# Existing NavigationEngine.
# We only call its public methods.
from ml_modules.navigation.navigation_engine import (
    NavigationEngine,
    ObstacleReading,
)


# ============================================================
# MEMORY ASSISTANT
# ============================================================

# Existing Memory Assistant.
# Its internal implementation remains unchanged.
from ml_modules.memory_assistant.assistant.conversation_engine import (
    ConversationEngine,
)

# Existing Memory event parser.
# This validates events using the Memory Assistant's
# existing schema.
from ml_modules.memory_assistant.models.events import (
    parse_event,
)


class PathGuardIntegrator:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):
        """
        Initialize the independent Path Guard modules.

        Vision:
            Qwen / Gemini / Groq

        Navigation:
            Existing NavigationEngine

        Memory:
            Existing ConversationEngine
        """

        # ----------------------------------------------------
        # Cloud Vision
        # ----------------------------------------------------
        # AI_PROVIDER controls which vision provider is used.
        #
        # Examples:
        #
        # AI_PROVIDER=groq
        # AI_PROVIDER=qwen
        # AI_PROVIDER=gemini
        #
        self.vision_provider = ConfiguredVisionProvider()

        # ----------------------------------------------------
        # Navigation
        # ----------------------------------------------------
        # Create the existing NavigationEngine.
        #
        # speak_enabled=False prevents speech during
        # integration testing.
        self.navigation_engine = NavigationEngine(
            speak_enabled=False
        )

        # ----------------------------------------------------
        # Memory Assistant
        # ----------------------------------------------------
        # Create the existing Memory Assistant.
        #
        # We do NOT modify its internal Gemini,
        # memory, context, or conversation logic.
        self.memory_engine = ConversationEngine()

    # ========================================================
    # VISION / SCENE UNDERSTANDING
    # ========================================================

    def analyze_scene(
        self,
        frame: Any,
    ) -> dict[str, Any]:
        """
        Analyze a camera frame using the configured
        AI vision provider.

        Flow:

            Camera frame
                  ↓
            Qwen / Gemini / Groq
                  ↓
            Scene response
                  ↓
            Standardized scene JSON
        """

        # Ask the configured vision provider to analyze
        # the camera frame.
        scene_response = self.vision_provider.describe_scene(
            frame
        )

        # Convert the provider response into the common
        # Path Guard scene format.
        return parse_qwen_scene(
            scene_response
        )

    # ========================================================
    # VISION QUESTION ANSWERING
    # ========================================================

    def answer_question(
        self,
        frame: Any,
        question: str,
    ) -> str:
        """
        Ask the configured vision provider a question
        about the current camera frame.
        """

        return self.vision_provider.answer_question(
            frame,
            question,
        )

    # ========================================================
    # PROCESS EXISTING SCENE RESPONSE
    # ========================================================

    def process_scene(
        self,
        scene_response: str | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize an already-existing scene response.
        """

        return parse_qwen_scene(
            scene_response
        )

    # ========================================================
    # NAVIGATION
    # ========================================================

    def get_navigation_detections(
        self,
        scene: dict[str, Any],
    ):
        """
        Convert Scene Understanding output into the format
        expected by the existing Navigation module.

        Scene Understanding provides:

            objects

        Navigation expects:

            obstacles
            people
            vehicles
            doors
            stairs

        We create the obstacles field here so that the
        existing Navigation adapter does not need to change.
        """

        # Make a copy so the original scene is not modified.
        navigation_scene = dict(
            scene
        )

        # Only objects explicitly marked as obstacles
        # are sent as navigation obstacles.
        navigation_scene["obstacles"] = [
            obj
            for obj in scene.get(
                "objects",
                []
            )
            if obj.get(
                "is_obstacle"
            ) is True
        ]

        # Use the existing Navigation adapter.
        return parse_scene_understanding_output(
            navigation_scene
        )

    # ========================================================
    # SEND VISION DETECTIONS TO NAVIGATION
    # ========================================================

    def update_navigation_detections(
        self,
        scene: dict[str, Any],
    ) -> None:
        """
        Send Scene Understanding detections to
        NavigationEngine.

        Flow:

            Scene JSON
                ↓
            Navigation adapter
                ↓
            DetectedObject list
                ↓
            NavigationEngine
        """

        # Convert scene data to Navigation's format.
        detections = self.get_navigation_detections(
            scene
        )

        # Send detections to NavigationEngine.
        self.navigation_engine.update_detections(
            detections
        )

    # ========================================================
    # SEND SENSOR DATA TO NAVIGATION
    # ========================================================

    def update_navigation_sensor(
        self,
        distance_m: float,
        position,
    ) -> None:
        """
        Send an ultrasonic / ToF sensor reading
        to NavigationEngine.

        This method does NOT generate sensor data.

        It only provides the connection point for the
        actual hardware sensor.
        """

        # Create NavigationEngine's expected
        # ObstacleReading object.
        reading = ObstacleReading(
            distance_m=distance_m,
            position=position,
        )

        # Send the reading to NavigationEngine.
        self.navigation_engine.update_obstacle_distance(
            reading
        )

    # ========================================================
    # GET NAVIGATION DECISION
    # ========================================================

    def get_navigation_instruction(self):
        """
        Ask NavigationEngine for the current safety decision.
        """

        return self.navigation_engine.decide()

    # ========================================================
    # OCR → MEMORY
    # ========================================================

    def send_ocr_to_memory(
        self,
        ocr_result: dict[str, Any],
    ) -> None:
        """
        Send a valid OCR result to Memory Assistant.

        The existing OCR module produces:

            {
                "event_type": "ocr_scan",
                "timestamp": "...",
                "session_id": "...",
                "payload": {
                    "detected_text": "...",
                    "confidence": ...,
                    "bounding_box": ...
                }
            }

        IMPORTANT:

        OCR can return an empty result when the OCR model
        fails to read anything.

        Memory Assistant requires detected_text to contain
        at least one character.

        Therefore:

            Valid text
                ↓
            Send to Memory

            Empty text
                ↓
            Ignore safely
        """

        # Get the OCR payload safely.
        payload = ocr_result.get(
            "payload",
            {}
        )

        # Extract detected text.
        detected_text = str(
            payload.get(
                "detected_text",
                ""
            )
        ).strip()

        # ----------------------------------------------------
        # IMPORTANT GUARD
        # ----------------------------------------------------
        # Do not send an empty OCR result to Memory.
        #
        # This prevents the Memory Assistant's Pydantic
        # validation error:
        #
        # "String should have at least 1 character"
        #
        if not detected_text:
            return

        # Validate the existing OCR event using the
        # Memory Assistant's own event schema.
        event = parse_event(
            ocr_result
        )

        # Store the validated event in Memory Assistant.
        self.memory_engine.process_event(
            event
        )

    # ========================================================
    # GENERIC MEMORY EVENT
    # ========================================================

    def send_memory_event(
        self,
        event_type: str,
        session_id: str,
        timestamp: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Send a valid event to Memory Assistant.

        Supported event types depend on the existing
        Memory Assistant event registry.

        Examples:

            ocr_scan
            location_update
            navigation_instruction
            object_stream
        """

        # Build the standard event structure.
        event_data = {
            "event_type": event_type,
            "timestamp": timestamp,
            "session_id": session_id,
            "payload": payload,
        }

        # Validate the event using the existing
        # Memory Assistant parser.
        event = parse_event(
            event_data
        )

        # Send the validated event to Memory.
        self.memory_engine.process_event(
            event
        )

    # ========================================================
    # BUILD MEMORY EVENT
    # ========================================================

    def build_memory_event(
        self,
        event_type: str,
        session_id: str,
        payload: dict[str, Any],
        timestamp: str,
    ) -> dict[str, Any]:
        """
        Build a standard Memory Assistant event.

        This method only creates the dictionary.
        It does not send the event.
        """

        return {
            "event_type": event_type,
            "timestamp": timestamp,
            "session_id": session_id,
            "payload": payload,
        }