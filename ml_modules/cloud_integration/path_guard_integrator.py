"""
Path Guard Integration Layer.

Connects independent Path Guard modules without modifying their internal implementations.

Connected modules:
    - Cloud Vision
    - Local Object Detection
    - Navigation
    - Memory Assistant
    - OCR
"""

import cv2
import threading
import time
import msvcrt
from typing import Any
from ultralytics import YOLO

# CLOUD / VISION

from ml_modules.cloud_integration.vision_provider import (
    ConfiguredVisionProvider,
)

from ml_modules.cloud_integration.scene_bridge import (
    parse_qwen_scene,
)

# NAVIGATION

from ml_modules.navigation.scene_adapter import (
    parse_scene_understanding_output,
)

from ml_modules.navigation.navigation_engine import (
    NavigationEngine,
    ObstacleReading,
)

# MEMORY ASSISTANT

from ml_modules.memory_assistant.assistant.conversation_engine import (
    ConversationEngine,
)

from ml_modules.memory_assistant.models.events import (
    parse_event,
)



class PathGuardIntegrator:

    # INITIALIZATION

    def __init__(self):
        """
        Initialize the independent Path Guard modules.

        Vision:
            Qwen / Gemini / Groq

        Local AI:
            YOLOv8n

        Navigation:
            Existing NavigationEngine

        Memory:
            Existing ConversationEngine
        """

        # Cloud Vision

        self.vision_provider = ConfiguredVisionProvider()

        # Local Object Detection

        self.local_detector = YOLO("yolov8n.pt")

        # Navigation

        self.navigation_engine = NavigationEngine(
            speak_enabled=False
        )

        # Memory Assistant

        self.memory_engine = ConversationEngine()

    # VISION / SCENE UNDERSTANDING

    def analyze_scene(
        self,
        frame: Any,
    ) -> dict[str, Any]:
        """
        Analyze a camera frame using the configured
        AI vision provider.
        """

        response = self.vision_provider.describe_scene(
            frame
        )

        return parse_qwen_scene(response)

    # VISION / QUESTION ANSWERING

    def answer_question(
        self,
        frame: Any,
        question: str,
    ) -> str:
        """
        Ask a question about the current camera frame.
        """

        return self.vision_provider.answer_question(
            frame,
            question,
        )

    # PROCESS EXISTING SCENE RESPONSE

    def process_scene(
        self,
        scene_response: str | dict[str, Any],
    ) -> dict[str, Any]:
        """
        Normalize a scene response into the common
        Path Guard scene representation.
        """

        return parse_qwen_scene(
            scene_response
        )

    # LOCAL OBJECT DETECTION

    def detect_local_objects(
        self,
        frame: Any,
    ) -> dict[str, Any]:
        """
        Detect objects locally using YOLOv8n.

        YOLO provides:
            - object label
            - confidence
            - approximate direction
            - bounding-box size

        Bounding-box size is used only for qualitative proximity estimation.

        It does NOT represent physical distance in meters.
        """

        results = self.local_detector(
            frame,
            conf=0.5,
            verbose=False,
        )

        height, width = frame.shape[:2]

        frame_area = width * height

        detections = []

        for box in results[0].boxes:

            # Bounding box coordinates

            x1, y1, x2, y2 = (
                box.xyxy[0].tolist()
            )

            # Object center

            center_x = (
                (x1 + x2) / 2
            )

            # Direction

            if center_x < width / 3:

                direction = "left"

            elif center_x > (2 * width / 3):

                direction = "right"

            else:

                direction = "front"

            # Bounding box size

            box_width = x2 - x1
            box_height = y2 - y1

            box_area = (
                box_width * box_height
            )

            area_ratio = (
                box_area / frame_area
            )

            # Qualitative proximity

            if area_ratio >= 0.35:

                proximity = "very_close"

            elif area_ratio >= 0.15:

                proximity = "close"

            elif area_ratio >= 0.05:

                proximity = "medium"

            else:

                proximity = "far"

            # Class information

            class_id = int(
                box.cls.item()
            )

            # Store detection

            detections.append(
                {
                    "label": self.local_detector.names[
                        class_id
                    ],
                    "direction": direction,
                    "distance": None,
                    "proximity": proximity,
                    "is_obstacle": True,
                    "confidence": round(
                        box.conf.item(),
                        2,
                    ),
                }
            )

        return {
            "objects": detections
        }


    # LOCAL SAFETY DECISION

    def evaluate_local_safety(
        self,
        local_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Evaluate locally detected obstacles using qualitative proximity.
        """

        objects = local_result.get(
            "objects",
            []
        )

        alerts = []

        for obj in objects:

            if not obj.get(
                "is_obstacle",
                False
            ):
                continue

            direction = obj.get(
                "direction"
            )

            proximity = obj.get(
                "proximity"
            )

            label = obj.get(
                "label",
                "obstacle"
            )

            # Very close obstacle

            if (
                proximity == "very_close"
                and direction == "front"
            ):

                alerts.append(
                    {
                        "level": "stop",
                        "message": (
                            f"Stop. {label} "
                            "very close ahead."
                        ),
                    }
                )

            # Close obstacle

            elif proximity == "close":

                if direction == "front":

                    alerts.append(
                        {
                            "level": "caution",
                            "message": (
                                f"Caution. {label} "
                                "ahead."
                            ),
                        }
                    )

                elif direction == "left":

                    alerts.append(
                        {
                            "level": "caution",
                            "message": (
                                f"Caution. {label} "
                                "on your left."
                            ),
                        }
                    )

                elif direction == "right":

                    alerts.append(
                        {
                            "level": "caution",
                            "message": (
                                f"Caution. {label} "
                                "on your right."
                            ),
                        }
                    )

        # No immediate obstacle

        if not alerts:

            return {
                "level": "clear",
                "alerts": [],
            }


        return {
            "level": alerts[0]["level"],
            "alerts": alerts,
        }

    # LOCAL + CLOUD PROCESSING

    def process_frame(
        self,
        frame: Any,
        question: str | None = None,
    ) -> dict[str, Any]:
        """
        Process a camera frame using the hybrid Local AI + Cloud AI architecture.

        Local AI:
            YOLOv8n handles basic object detection.

        Cloud AI:
            Qwen / Gemini / Groq handles deeper scene understanding or user questions.
        """

        # Local AI

        local_result = self.detect_local_objects(
            frame
        )

        # Question â†’ Cloud Vision

        if question and question.strip():

            cloud_response = self.answer_question(
                frame,
                question,
            )

            return {
                "mode": "cloud",
                "local": local_result,
                "answer": cloud_response,
            }

        # No question â†’ Local

        return {
            "mode": "local",
            "local": local_result,
        }

    # REAL-TIME PATH GUARD

    def run_realtime(
        self,
        inference_interval: float = 0.4,
    ):
        """
        Run Path Guard in continuous real-time mode.

        Camera:
            Continuously captures frames.

        Local AI:
            YOLO processes the latest available frame.

        Cloud:
            Not called automatically.

        This is currently a runtime test for continuous local processing.
        """

        # Open camera

        camera = cv2.VideoCapture(0)

        if not camera.isOpened():

            raise RuntimeError(
                "Could not open webcam"
            )

        # Shared camera state

        latest_frame = None
        running = True

        lock = threading.Lock()

        # Camera capture thread

        def capture_loop():

            nonlocal latest_frame
            nonlocal running

            while running:

                success, frame = camera.read()

                if not success:

                    continue

                with lock:

                    latest_frame = frame

        # Start camera capture

        capture_thread = threading.Thread(
            target=capture_loop,
            daemon=True,
        )

        capture_thread.start()

        # Startup information

        print(
            "PATH GUARD REAL-TIME MODE STARTED"
        )

        print(
            "Camera: ON"
        )

        print(
            "Local AI: YOLOv8n"
        )

        print(
            "Cloud AI: ON-DEMAND"
        )

        print(
            "Press Q to stop"
        )

        # Processing loop

        try:

            while running:

                # Get newest frame

                with lock:

                    if latest_frame is None:

                        frame = None

                    else:

                        frame = latest_frame.copy()

                # Wait for camera

                if frame is None:

                    time.sleep(0.01)

                    continue

                # Process frame through the integration pipeline

                frame_result = self.process_frame(frame)
                local_result = frame_result["local"]
                safety_result = self.evaluate_local_safety(local_result)

                # Print results

                print(
                    "LOCAL:",
                    local_result,
                )

                print(
                    "SAFETY:",
                    safety_result,
                )

                # Stop with Q

                if msvcrt.kbhit():

                    key = msvcrt.getch().lower()

                    if key == b'q':
                        running = False
                        break

                # Control inference frequency

                time.sleep(
                    inference_interval
                )

        finally:

            running = False

            capture_thread.join(
                timeout=1
            )

            camera.release()

            cv2.destroyAllWindows()

            print(
                "PATH GUARD REAL-TIME MODE STOPPED"
            )

    # NAVIGATION DETECTIONS

    def get_navigation_detections(
        self,
        scene: dict[str, Any],
    ):
        """
        Convert the normalized Path Guard scene into the format expected by the existing Navigation adapter.
        """

        navigation_scene = dict(
            scene
        )

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

        return parse_scene_understanding_output(
            navigation_scene
        )

    # UPDATE NAVIGATION FROM VISION

    def update_navigation_detections(
        self,
        scene: dict[str, Any],
    ):
        """
        Send vision-derived detections to the existing NavigationEngine.
        """

        detections = (
            self.get_navigation_detections(
                scene
            )
        )

        self.navigation_engine.update_detections(
            detections
        )

        return detections

    # UPDATE NAVIGATION FROM SENSOR

    def update_navigation_sensor(
        self,
        distance_m: float,
        position: Any = None,
    ):
        """
        Send an ultrasonic / ToF sensor reading to the existing NavigationEngine.
        No sensor hardware is currently connected.
        """

        if position is None:

            reading = ObstacleReading(
                distance_m=distance_m
            )

        else:

            reading = ObstacleReading(
                distance_m=distance_m,
                position=position,
            )

        self.navigation_engine.update_obstacle_distance(
            reading
        )

        return reading

    # GET NAVIGATION INSTRUCTION

    def get_navigation_instruction(
        self,
    ):
        """
        Ask the existing NavigationEngine for the current navigation decision.
        """

        return self.navigation_engine.decide()

    # OCR â†’ MEMORY

    def send_ocr_to_memory(
        self,
        detected_text: str,
        confidence: float,
        bounding_box: dict[str, Any],
        timestamp: float,
        session_id: str,
    ):
        """
        Send OCR information to the existing Memory Assistant.
        """

        if (
            not detected_text
            or not detected_text.strip()
        ):

            return None

        event = parse_event(
            {
                "event_type": "ocr_scan",
                "timestamp": timestamp,
                "session_id": session_id,
                "payload": {
                    "detected_text": detected_text,
                    "confidence": confidence,
                    "bounding_box": bounding_box,
                },
            }
        )

        return self.memory_engine.process_event(
            event
        )

    # GENERIC MEMORY EVENT

    def send_memory_event(
        self,
        event_data: dict[str, Any] | Any,
    ):
        """
        Send an already structured event to the existing Memory Assistant.
        """

        if isinstance(event_data, dict):
            event = parse_event(event_data)
        else:
            event = event_data

        return self.memory_engine.process_event(
            event
        )

    # BUILD MEMORY EVENT

    def build_memory_event(
        self,
        event_type: str,
        timestamp: float,
        session_id: str,
        payload: dict[str, Any],
    ):
      
        return parse_event(
            {
                "event_type": event_type,
                "timestamp": timestamp,
                "session_id": session_id,
                "payload": payload,
            }
        )

