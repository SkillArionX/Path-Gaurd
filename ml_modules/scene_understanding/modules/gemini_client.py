import os
import cv2
import json
import time
from PIL import Image
from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

MODEL_NAME = "gemini-2.0-flash"


def analyze_scene(frame, question, max_retries=5):
    """
    Analyze the given camera frame using Gemini Vision.

    Returns:
        JSON string containing:
        {
            "path_clear": bool,
            "summary": "...",
            "objects": [...]
        }
    """

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)

    retries = 0
    backoff_time = 2

    while retries < max_retries:
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[
                    question,
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

    return json.dumps(fallback, indent=4)