import os
import cv2
import json
import time
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import errors

from ml_modules.scene_understanding.modules.prompt import (
    SCENE_PROMPT,
    QUESTION_PROMPT
)

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-3.6-flash"


def _send_request(frame, prompt, max_retries=5):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)

    retries = 0
    backoff_time = 2

    while retries < max_retries:
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    prompt,
                    image
                ]
            )

            return response.text

        except errors.APIError as e:

            if e.code in [429, 503]:
                print(
                    f"[Gemini] API busy ({e.code}). "
                    f"Retrying in {backoff_time}s "
                    f"({retries + 1}/{max_retries})..."
                )

                time.sleep(backoff_time)

                retries += 1
                backoff_time *= 2

            else:
                raise e

    fallback = {
        "path_clear": False,
        "summary": "Scene analysis unavailable.",
        "objects": [],
        "status": "failed",
        "provider": "gemini"
    }

    return json.dumps(fallback)


def describe_scene(frame):
    """
    Automatic Scene Understanding using Gemini.
    Returns the standardized scene JSON.
    """
    return _send_request(frame, SCENE_PROMPT)


def answer_question(frame, question):
    """
    Answer a user's question about the current camera frame.
    """
    prompt = f"""
{QUESTION_PROMPT}

User Question:
{question}
"""

    return _send_request(frame, prompt)


def analyze_scene(frame, question):
    """
    Backward-compatible function used by existing modules.
    """
    return _send_request(frame, question)
