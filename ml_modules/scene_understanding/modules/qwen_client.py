import os
import cv2
import base64
from openai import OpenAI
from dotenv import load_dotenv

from modules.prompt import SCENE_PROMPT, QUESTION_PROMPT

load_dotenv()

client = OpenAI(
    api_key=os.getenv("QWEN_API_KEY"),
    base_url=os.getenv("QWEN_BASE_URL")
)


def _send_request(frame, prompt):

    _, buffer = cv2.imencode(".jpg", frame)
    image_base64 = base64.b64encode(buffer).decode("utf-8")

    response = client.chat.completions.create(
        model="qwen/qwen2.5-vl-72b-instruct",
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
        max_tokens=100,
        temperature=0.2,
    )

    return response.choices[0].message.content


def describe_scene(frame):
    """
    Automatic Scene Understanding
    Returns JSON using SCENE_PROMPT
    """
    return _send_request(frame, SCENE_PROMPT)


def answer_question(frame, question):
    """
    AI Assistant
    Returns a natural language answer to the user's question.
    """

    prompt = f"""
{QUESTION_PROMPT}

User Question:
{question}
"""

    return _send_request(frame, prompt)


# Backward compatibility
def analyze_scene(frame, question):
    return _send_request(frame, question)

def answer_ocr_text(text, question):
    prompt = f"""
The following text was extracted from an image using OCR.

OCR Text:
{text}

User Question:
{question}

Answer the user's question based only on the OCR text.
If the OCR text is unclear or incomplete, mention that.
Keep the answer concise and suitable for text-to-speech.
"""

    response = client.chat.completions.create(
        model="qwen/qwen2.5-vl-72b-instruct",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=100,
        temperature=0.2,
    )

    return response.choices[0].message.content
