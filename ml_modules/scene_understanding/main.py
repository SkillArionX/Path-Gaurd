import json

from modules.camera import capture_image
from modules.ai_client import describe_scene
from modules.qwen_client import answer_question

input("Press ENTER to analyze your surroundings...")

frame = capture_image()

response = describe_scene(frame)

scene_data = json.loads(response)

print(json.dumps(scene_data, indent=4))

question = "What is in front of me?"

response = answer_question(frame, question)

print(response)