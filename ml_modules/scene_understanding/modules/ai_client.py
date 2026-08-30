import os
from dotenv import load_dotenv

load_dotenv()

provider = os.getenv("AI_PROVIDER", "qwen").lower()

if provider == "gemini":
    from modules.gemini_client import (
        describe_scene,
        answer_question,
        analyze_scene
    )

elif provider == "qwen":
    from modules.qwen_client import (
        describe_scene,
        answer_question,
        analyze_scene
    )

elif provider == "grok":
    from modules.grok_client import (
        describe_scene,
        answer_question,
        analyze_scene
    )

else:
    raise ValueError(f"Unsupported AI provider: {provider}")