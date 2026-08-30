"""
Path Guard - Scene Understanding Adapter
Owner: Muskan Shaikh

WHY THIS FILE EXISTS
--------------------
Amrutha's Scene Understanding module does NOT output the flat
{label, confidence, position, distance_m} schema originally proposed on
27 Jul. Instead, after team discussion, she is outputting a richer,
narrative-style JSON (summary + categorized object lists + warnings).

Rather than bending navigation_engine.py's internal DetectedObject contract
to match one teammate's exact JSON shape (which would break again the next
time anyone's output format changes), this file is a dedicated ADAPTER:
it translates Amrutha's real JSON into the DetectedObject objects that
NavigationEngine already expects. If her format changes again, only this
file needs updating -- navigation_engine.py and its decision logic stay
completely untouched.

CONFIRMED FORMAT (from team chat, 27 Jul 2026, Amrutha's actual sample):
{
  "summary": "A person is walking ahead in an indoor corridor. A chair is
              placed slightly to the right side, while the left side of
              the path appears clear.",
  "walkable_path": "left",
  "obstacles": [
    {"label": "chair", "direction": "front-right", "distance": "2 meters"}
  ],
  "people": [
    {"count": 1, "direction": "front"}
  ],
  "vehicles": [],
  "doors": [
    {"direction": "right"}
  ],
  "stairs": [],
  "warnings": [
    "Obstacle present on the right side. Move towards the left side."
  ]
}

OPEN DISCUSSION POINT FOR THE TEAM MEETING (with Ishan):
---------------------------------------------------------
"walkable_path" is Scene Understanding's OWN suggested direction. My
module's whole job (per the mentor's brief) is to independently decide
the safest direction using object detections + obstacle distance + GPS.
Having two modules each propose a direction risks them disagreeing.
For now, this adapter reads walkable_path and warnings for reference/
logging only -- it does NOT feed them into NavigationEngine.decide().
Worth explicitly agreeing as a team who has final authority on direction.

CONFIDENCE NOTE:
Amrutha's format does not include a per-object confidence score. This is
fine -- NavigationEngine.decide() does not currently use confidence for
any filtering decision (only distance and position drive the logic), so
a fixed placeholder value is used here purely to satisfy the DetectedObject
dataclass shape.
"""

import json
import re
from typing import Optional, List, Tuple, Union

from navigation_engine import DetectedObject, Position

DEFAULT_CONFIDENCE = 0.85  # placeholder -- see CONFIDENCE NOTE above


# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------

def _direction_to_position(direction: Optional[str]) -> Position:
    """
    Amrutha's directions aren't always just 'left'/'center'/'right' --
    e.g. 'front-right', 'front'. This matches on substring so any of
    'left', 'front-left', 'back-left', etc. all map correctly, and
    anything with no left/right mention (e.g. 'front') defaults to CENTER.
    """
    if not direction:
        return Position.CENTER
    d = direction.lower()
    if "left" in d:
        return Position.LEFT
    if "right" in d:
        return Position.RIGHT
    return Position.CENTER


def _parse_distance_meters(distance: Optional[Union[str, int, float]]) -> Optional[float]:
    """Handles '2 meters' (string), a raw number, or None (not all categories report distance)."""
    if distance is None:
        return None
    if isinstance(distance, (int, float)):
        return float(distance)
    match = re.search(r"(\d+(?:\.\d+)?)", str(distance))
    return float(match.group(1)) if match else None


def _load(json_data: Union[str, dict]) -> dict:
    return json.loads(json_data) if isinstance(json_data, str) else json_data


# ---------------------------------------------------------------------------
# Main adapter functions
# ---------------------------------------------------------------------------

def parse_scene_understanding_output(json_data: Union[str, dict]) -> List[DetectedObject]:
    """
    Converts one Scene Understanding module response into a list of
    DetectedObject instances, ready for NavigationEngine.update_detections().
    Defensive against missing/empty keys, since not every frame will have
    obstacles, people, vehicles, doors, and stairs all at once.
    """
    data = _load(json_data)
    detections: List[DetectedObject] = []

    # --- obstacles: {"label", "direction", "distance"} ---
    for obs in data.get("obstacles") or []:
        detections.append(DetectedObject(
            label=obs.get("label", "obstacle"),
            confidence=DEFAULT_CONFIDENCE,
            position=_direction_to_position(obs.get("direction")),
            distance_m=_parse_distance_meters(obs.get("distance")),
        ))

    # --- people: {"count", "direction"} -- grouped, no per-person distance ---
    for grp in data.get("people") or []:
        count = grp.get("count", 1)
        label = "person" if count == 1 else f"{count} people"
        detections.append(DetectedObject(
            label=label,
            confidence=DEFAULT_CONFIDENCE,
            position=_direction_to_position(grp.get("direction")),
            distance_m=_parse_distance_meters(grp.get("distance")),  # usually None
        ))

    # --- vehicles: shape not yet confirmed with Amrutha (was empty in her sample) ---
    # Handled defensively for either an obstacle-like shape or a people-like (count) shape.
    for veh in data.get("vehicles") or []:
        if "count" in veh:
            count = veh.get("count", 1)
            label = "vehicle" if count == 1 else f"{count} vehicles"
        else:
            label = veh.get("label", "vehicle")
        detections.append(DetectedObject(
            label=label,
            confidence=DEFAULT_CONFIDENCE,
            position=_direction_to_position(veh.get("direction")),
            distance_m=_parse_distance_meters(veh.get("distance")),
        ))

    # --- doors: {"direction"} only, no distance given ---
    for door in data.get("doors") or []:
        detections.append(DetectedObject(
            label="door",
            confidence=DEFAULT_CONFIDENCE,
            position=_direction_to_position(door.get("direction")),
            distance_m=None,
        ))

    # --- stairs: assumed same shape as doors (was empty in her sample) ---
    for stair in data.get("stairs") or []:
        detections.append(DetectedObject(
            label="stairs",
            confidence=DEFAULT_CONFIDENCE,
            position=_direction_to_position(stair.get("direction")),
            distance_m=None,
        ))

    return detections


def scene_context(json_data: Union[str, dict]) -> Tuple[Optional[str], Optional[str], List[str]]:
    """
    Pulls out the natural-language summary, Scene Understanding's own
    walkable_path suggestion, and warnings -- for logging/debugging only.
    NOT currently fed into NavigationEngine.decide() -- see the "OPEN
    DISCUSSION POINT" note at the top of this file.
    """
    data = _load(json_data)
    return data.get("summary"), data.get("walkable_path"), data.get("warnings", [])
