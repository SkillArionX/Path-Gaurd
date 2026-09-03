import os
import cv2
import base64

from groq import Groq
from dotenv import load_dotenv

from ml_modules.scene_understanding.modules.prompt import (
    SCENE_PROMPT,
    QUESTION_PROMPT
)

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

MODEL_NAME = "qwen/qwen3.6-27b"


def _send_request(frame, prompt):

    _, buffer = cv2.imencode(".jpg", frame)
    image_base64 = base64.b64encode(buffer).decode("utf-8")

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        temperature=0,
        max_completion_tokens=1024,
        reasoning_effort="none",
        response_format={"type": "json_object"},
    )

    return response.choices[0].message.content


def describe_scene(frame):
    return _send_request(frame, SCENE_PROMPT)


def answer_question(frame, question):
    prompt = f"""
{QUESTION_PROMPT}

User Question:
{question}
"""
    return _send_request(frame, prompt)


def analyze_scene(frame, question):
    return _send_request(frame, question)
