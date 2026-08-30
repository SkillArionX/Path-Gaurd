import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
scene_understanding = project_root / "scene_understanding"

sys.path.insert(0, str(scene_understanding))

from modules.qwen_client import answer_ocr_text


def intelligent_reading(text, question):
    return answer_ocr_text(text, question)