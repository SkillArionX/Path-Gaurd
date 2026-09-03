"""Adapter for normalizing Qwen scene-understanding output."""

import json
from typing import Any


def parse_qwen_scene(response: str | dict[str, Any]) -> dict[str, Any]:
    """Parse and normalize a Qwen scene response."""

    if isinstance(response, str):
        try:
            scene = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid Qwen JSON response: {exc}") from exc
    elif isinstance(response, dict):
        scene = response
    else:
        raise TypeError("Qwen response must be a JSON string or dictionary")

    if not isinstance(scene, dict):
        raise ValueError("Qwen response must be a JSON object")

    return {
        "summary": scene.get("summary", ""),
        "walkable_path": scene.get("walkable_path", ""),
        "objects": scene.get("objects", []),
        "people": scene.get("people", []),
        "vehicles": scene.get("vehicles", []),
        "doors": scene.get("doors", []),
        "stairs": scene.get("stairs", []),
        "warnings": scene.get("warnings", []),
    }
