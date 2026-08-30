import sys
import json
import re
import uuid
from pathlib import Path
from datetime import datetime, timezone

import pyttsx3


project_root = Path(__file__).resolve().parent.parent
scene_understanding = project_root / "scene_understanding"

sys.path.insert(0, str(scene_understanding))

from modules.qwen_client import _send_request


class OCREngine:

    def __init__(self):
        pass

    def extract_text(self, image):

        if image is None or image.size == 0:
            return self.create_result(
                "",
                0,
                self.empty_box()
            )

        prompt = """
You are the OCR module of Path Guard for a blind or visually impaired person.

Analyze the ENTIRE camera frame.

The user cannot see the camera image and cannot know where text is located.

DO NOT require the user to center, align, crop, or point the camera at text.

Search the COMPLETE image for readable and useful text.

Prioritize:
- road signs
- traffic signs
- warning signs
- shop names
- building names
- room names
- directions
- notices
- labels
- medicine names
- medicine instructions
- numbers
- public information
- important instructions
- signboards

Ignore:
- random shapes
- decorative patterns
- meaningless symbols
- logos without readable text
- objects
- unclear text

DO NOT GUESS OR INVENT TEXT.

If multiple important text regions exist, combine the readable text.

Return ONLY the JSON object.
Do NOT return markdown.
Do NOT return ```json.
Do NOT add explanations.

Return EXACTLY:

{
  "text": "readable important text",
  "confidence": 0.0,
  "box": {"x": 0, "y": 0, "w": 0, "h": 0}
}

The original camera frame is 640x480 pixels.

The bounding box must cover the main detected text area.

If there is no confidently readable important text, return:

{
  "text": "",
  "confidence": 0.0,
  "box": {"x": 0, "y": 0, "w": 0, "h": 0}
}
"""

        try:

            raw_response = _send_request(
                image,
                prompt
            )

            data = self.parse_json(
                raw_response
            )

            if data is None:
                return self.create_result(
                    "",
                    0,
                    self.empty_box()
                )

            text = str(
                data.get(
                    "text",
                    ""
                )
            ).strip()

            try:

                confidence = float(
                    data.get(
                        "confidence",
                        0
                    )
                )

            except:

                confidence = 0

            box = self.validate_box(
                data.get(
                    "box",
                    self.empty_box()
                ),
                image.shape[1],
                image.shape[0]
            )

            if not text:

                return self.create_result(
                    "",
                    0,
                    self.empty_box()
                )

            return self.create_result(
                text,
                round(
                    confidence,
                    2
                ),
                box
            )

        except Exception as e:

            print(
                "QWEN OCR ERROR:",
                e
            )

            return self.create_result(
                "",
                0,
                self.empty_box()
            )

    def speak(self, text):

        if not text:
            return

        try:

            engine = pyttsx3.init()

            engine.setProperty(
                "rate",
                150
            )

            engine.setProperty(
                "volume",
                1.0
            )

            engine.say(
                text
            )

            engine.runAndWait()

            engine.stop()

            del engine

        except Exception as e:

            print(
                "TTS ERROR:",
                e
            )

    def parse_json(
        self,
        response
    ):

        if not response:
            return None

        response = str(
            response
        ).strip()

        response = re.sub(
            r"```json",
            "",
            response,
            flags=re.IGNORECASE
        )

        response = re.sub(
            r"```",
            "",
            response
        )

        response = response.strip()

        try:

            return json.loads(
                response
            )

        except:

            pass

        match = re.search(
            r"\{.*\}",
            response,
            re.DOTALL
        )

        if not match:
            return None

        try:

            return json.loads(
                match.group(0)
            )

        except:

            return None

    def validate_box(
        self,
        box,
        width,
        height
    ):

        if not isinstance(
            box,
            dict
        ):
            return self.empty_box()

        try:

            x = int(
                box.get(
                    "x",
                    0
                )
            )

            y = int(
                box.get(
                    "y",
                    0
                )
            )

            w = int(
                box.get(
                    "w",
                    0
                )
            )

            h = int(
                box.get(
                    "h",
                    0
                )
            )

        except:

            return self.empty_box()

        x = max(
            0,
            min(
                x,
                width
            )
        )

        y = max(
            0,
            min(
                y,
                height
            )
        )

        w = max(
            0,
            min(
                w,
                width - x
            )
        )

        h = max(
            0,
            min(
                h,
                height - y
            )
        )

        return {
            "x": x,
            "y": y,
            "w": w,
            "h": h
        }

    def empty_box(self):

        return {
            "x": 0,
            "y": 0,
            "w": 0,
            "h": 0
        }

    def create_result(
        self,
        text,
        confidence,
        bounding_box
    ):

        return {
            "event_type": "ocr_scan",
            "timestamp": datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
            "session_id":
                "sess_usr_" +
                str(uuid.uuid4())[:5],
            "payload": {
                "detected_text": text,
                "confidence": confidence,
                "bounding_box": bounding_box
            }
        }