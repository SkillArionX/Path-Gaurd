"""
Path Guard - Intelligent Navigation Module
Owner: Muskan Shaikh

PURPOSE
-------
Fuses three input streams:
    1. Object detection results   (from the Scene Understanding module)
    2. Obstacle distance readings (from an ultrasonic / ToF sensor)
    3. GPS position               (+ optional compass heading)

...into ONE safety-first spoken instruction per decision cycle. This module
does not just announce "person detected" or "pole detected" -- it decides
what the user should actually DO: stop, redirect around it, or keep
following the planned route.

DECISION PRIORITY (highest always wins, never overridden):
    1. Immediate obstacle safety   -- "Stop."
    2. Nearby obstacle + redirect  -- "Move slightly right."
    3. Missing/unreliable sensor data -- "Proceed carefully" (never a false
       "path clear" when we simply don't have data)
    4. Route guidance              -- only spoken when the path is confirmed clear

INTEGRATION CONTRACT (for the rest of the team)
------------------------------------------------
Other modules feed this engine data through simple update_*() calls:

    engine.update_detections([DetectedObject(...), ...])   # from Amrutha's module
    engine.update_obstacle_distance(ObstacleReading(...))   # from ultrasonic sensor
    engine.update_gps(GPSFix(...))                          # from GPS module
    engine.update_heading(compass_degrees)                  # optional, from IMU/compass

Then, on a loop (every 200-500ms is reasonable):

    instruction = engine.decide()
    engine.announce(instruction)
"""

import math
import time
from dataclasses import dataclass, field
from typing import Optional, List, Tuple
from enum import Enum


# ---------------------------------------------------------------------------
# Shared vocabulary / data contracts
# ---------------------------------------------------------------------------

class Position(Enum):
    """Roughly where in the user's field of view something is."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


class ThreatLevel(Enum):
    NONE = "none"          # confirmed clear
    UNKNOWN = "unknown"    # no reliable sensor data right now
    CAUTION = "caution"    # obstacle nearby, redirect suggested
    URGENT = "urgent"      # obstacle very close, stop


@dataclass
class DetectedObject:
    """One object detected by the Scene Understanding module."""
    label: str                          # e.g. "person", "pole", "car", "pothole"
    confidence: float                   # 0.0 - 1.0
    position: Position = Position.CENTER
    distance_m: Optional[float] = None  # vision-estimated distance, if available


@dataclass
class ObstacleReading:
    """One reading from a dedicated distance sensor (ultrasonic / ToF)."""
    distance_m: float
    position: Position = Position.CENTER
    timestamp: float = field(default_factory=time.time)


@dataclass
class GPSFix:
    latitude: float
    longitude: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class Waypoint:
    latitude: float
    longitude: float
    name: str = ""


@dataclass
class NavigationInstruction:
    spoken_text: str
    threat_level: ThreatLevel
    suggested_direction: Optional[Position] = None


# ---------------------------------------------------------------------------
# Geo helper functions (no external dependencies needed)
# ---------------------------------------------------------------------------

EARTH_RADIUS_M = 6371000


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two GPS points, in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compass bearing (0-360, 0=North) from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    theta = math.atan2(x, y)
    return (math.degrees(theta) + 360) % 360


def relative_turn_instruction(current_heading_deg: float, target_bearing_deg: float) -> str:
    """Translate an absolute compass bearing into a relative, spoken turn instruction."""
    diff = (target_bearing_deg - current_heading_deg + 360) % 360
    if diff <= 20 or diff >= 340:
        return "continue straight"
    elif diff <= 70:
        return "veer slightly right"
    elif diff <= 160:
        return "turn right"
    elif diff <= 200:
        return "you are facing away from your destination, turn around"
    elif diff <= 290:
        return "turn left"
    else:
        return "veer slightly left"


# ---------------------------------------------------------------------------
# Core engine
# ---------------------------------------------------------------------------

class NavigationEngine:
    """
    The single entry point the rest of the Path Guard app talks to.
    Thread-safe enough for one producer thread (sensors) + one consumer
    thread (decision loop) -- for higher concurrency, wrap update_* calls
    with an external lock.
    """

    URGENT_DISTANCE_M = 1.0
    CAUTION_DISTANCE_M = 3.0
    WAYPOINT_ARRIVAL_RADIUS_M = 5.0
    SENSOR_STALE_SECONDS = 2.0
    MIN_GPS_MOVEMENT_M = 3.0  # below this, treat GPS movement as noise, not real motion
    MIN_CONFIDENCE = 0.5      # detections below this confidence are ignored for safety decisions

    def __init__(self, speak_enabled: bool = True, tts_rate: int = 170):
        self._detections: List[DetectedObject] = []
        self._detections_updated_at: float = 0.0
        self._obstacle: Optional[ObstacleReading] = None
        self._gps: Optional[GPSFix] = None
        self._heading_deg: float = 0.0
        self._route: List[Waypoint] = []
        self._route_index: int = 0
        self._last_spoken_text: str = ""
        self._last_bearing_fix: Optional[GPSFix] = None
        self._last_turn_instruction: Optional[str] = None

        self.speak_enabled = speak_enabled
        self._tts_engine = None
        if speak_enabled:
            try:
                import pyttsx3
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty('rate', tts_rate)
                self._tts_engine.setProperty('volume', 1.0)
            except Exception as exc:
                # Don't crash the whole navigation stack just because there's
                # no audio device available (e.g. running in a test/CI env).
                print(f"[NavigationEngine] TTS unavailable, falling back to text-only: {exc}")
                self.speak_enabled = False

    # ---- Data ingestion (called by other modules / sensor threads) --------

    def update_detections(self, detections: List[DetectedObject]) -> None:
        self._detections = detections
        self._detections_updated_at = time.time()

    def update_obstacle_distance(self, reading: ObstacleReading) -> None:
        self._obstacle = reading

    def update_gps(self, fix: GPSFix) -> None:
        self._gps = fix

    def update_heading(self, heading_deg: float) -> None:
        self._heading_deg = heading_deg % 360

    def set_route(self, waypoints: List[Waypoint]) -> None:
        self._route = waypoints
        self._route_index = 0

    # ---- Internal decision helpers ----------------------------------------

    def _sensors_are_fresh(self) -> bool:
        now = time.time()
        obstacle_fresh = self._obstacle is not None and (now - self._obstacle.timestamp) < self.SENSOR_STALE_SECONDS
        detections_recent = (now - self._detections_updated_at) < self.SENSOR_STALE_SECONDS if self._detections_updated_at else False
        if not detections_recent:
            return obstacle_fresh
        # An empty list (vision system actively saw nothing) is still
        # trustworthy fresh data. But if every detection this frame was
        # below the confidence bar, that's an ambiguous frame -- not the
        # same as a confirmed-clear one -- unless the ultrasonic sensor
        # backs it up.
        only_low_confidence = (
            len(self._detections) > 0
            and all(obj.confidence < self.MIN_CONFIDENCE for obj in self._detections)
        )
        if only_low_confidence and not obstacle_fresh:
            return False
        return True

    def _closest_threat(self) -> Optional[Tuple[float, Position, str]]:
        """
        Combine the dedicated obstacle sensor with vision-based detections
        and return the single closest, most urgent obstacle.

        Sensor fusion rule: when both an ultrasonic/ToF reading and a vision
        detection agree on position and roughly agree on distance, they are
        treated as the SAME physical object -- we use the ultrasonic distance
        (more accurate at close range) but keep the vision label (ultrasonic
        can tell you something is there, but not what it is). If only one
        sensor sees something, we use whatever we've got.
        """
        now = time.time()
        obstacle_fresh = self._obstacle is not None and (now - self._obstacle.timestamp) < self.SENSOR_STALE_SECONDS

        candidates: List[Tuple[float, Position, str]] = []
        obstacle_matched = False

        for obj in self._detections:
            if obj.distance_m is None:
                continue
            if obj.confidence < self.MIN_CONFIDENCE:
                # Low-confidence guesses shouldn't trigger a stop/redirect --
                # better to fall through to the ultrasonic reading (if any)
                # or "unknown" than to react confidently to a shaky detection.
                continue
            if (obstacle_fresh and obj.position == self._obstacle.position
                    and abs(obj.distance_m - self._obstacle.distance_m) <= 1.0):
                # Same physical object seen by both sensors -- fuse identity + distance.
                candidates.append((self._obstacle.distance_m, obj.position, obj.label))
                obstacle_matched = True
            else:
                candidates.append((obj.distance_m, obj.position, obj.label))

        if obstacle_fresh and not obstacle_matched:
            candidates.append((self._obstacle.distance_m, self._obstacle.position, "obstacle"))

        if not candidates:
            return None

        candidates.sort(key=lambda c: c[0])
        return candidates[0]

    def _suggest_clear_side(self, blocked_position: Position) -> Position:
        """If the center is blocked, check which side (if any) is free."""
        blocked_positions = {blocked_position}
        for obj in self._detections:
            if obj.distance_m is not None and obj.distance_m < self.CAUTION_DISTANCE_M:
                blocked_positions.add(obj.position)

        for side in (Position.RIGHT, Position.LEFT):
            if side not in blocked_positions:
                return side
        return Position.CENTER  # neither side is clear -- caller should stop, not redirect

    def _route_guidance(self) -> Optional[str]:
        if not self._route or not self._gps:
            return None

        target = self._route[self._route_index]
        dist = haversine_distance_m(self._gps.latitude, self._gps.longitude,
                                     target.latitude, target.longitude)

        if dist <= self.WAYPOINT_ARRIVAL_RADIUS_M:
            self._route_index += 1
            self._last_bearing_fix = None  # new leg -- old bearing no longer applies
            if self._route_index >= len(self._route):
                return f"You have arrived at {target.name or 'your destination'}."
            target = self._route[self._route_index]
            dist = haversine_distance_m(self._gps.latitude, self._gps.longitude,
                                         target.latitude, target.longitude)

        # GPS noise guard: a phone's GPS is typically accurate to only 5-15m,
        # and a walking pedestrian moves roughly 1-2m per second. Two fixes
        # closer together than MIN_GPS_MOVEMENT_M are more likely to reflect
        # GPS jitter than real movement -- recomputing bearing from noise
        # causes the classic "turn left, turn right, turn left" flicker.
        # Reuse the last confident turn instruction instead of chasing noise.
        if self._last_bearing_fix is not None:
            moved = haversine_distance_m(self._gps.latitude, self._gps.longitude,
                                          self._last_bearing_fix.latitude,
                                          self._last_bearing_fix.longitude)
            if moved < self.MIN_GPS_MOVEMENT_M and self._last_turn_instruction is not None:
                name = f" toward {target.name}" if target.name else ""
                return f"{self._last_turn_instruction}{name}, {int(dist)} meters."

        target_bearing = bearing_deg(self._gps.latitude, self._gps.longitude,
                                      target.latitude, target.longitude)
        turn = relative_turn_instruction(self._heading_deg, target_bearing)
        self._last_bearing_fix = self._gps
        self._last_turn_instruction = turn.capitalize()
        name = f" toward {target.name}" if target.name else ""
        return f"{turn.capitalize()}{name}, {int(dist)} meters."

    # ---- Public decision API -----------------------------------------------

    def decide(self) -> NavigationInstruction:
        """
        Call this every 200-500ms in the main loop. Returns the single
        instruction that should be spoken right now.
        """
        threat = self._closest_threat()

        if threat:
            distance, position, label = threat

            if distance < self.URGENT_DISTANCE_M:
                where = "directly ahead" if position == Position.CENTER else f"to your {position.value}"
                text = f"Stop. {label.capitalize()} {where}, {distance:.1f} meters."
                return NavigationInstruction(text, ThreatLevel.URGENT, None)

            if distance < self.CAUTION_DISTANCE_M and position == Position.CENTER:
                clear_side = self._suggest_clear_side(position)
                if clear_side == Position.CENTER:
                    text = (f"Caution. {label.capitalize()} ahead, {distance:.1f} meters. "
                            f"Path is blocked on both sides. Stop and reassess.")
                    return NavigationInstruction(text, ThreatLevel.URGENT, None)
                text = f"{label.capitalize()} ahead, {distance:.1f} meters. Move slightly {clear_side.value}."
                return NavigationInstruction(text, ThreatLevel.CAUTION, clear_side)

            if distance < self.CAUTION_DISTANCE_M:
                text = f"{label.capitalize()} to your {position.value}, {distance:.1f} meters. Path ahead is clear."
                return NavigationInstruction(text, ThreatLevel.CAUTION, None)

        # No obstacle within range. But before declaring the path clear,
        # make sure we actually HAVE working sensor data -- never claim
        # "clear" just because we heard nothing.
        if not self._sensors_are_fresh():
            text = "No obstacle data currently available. Proceed carefully."
            return NavigationInstruction(text, ThreatLevel.UNKNOWN, None)

        route_text = self._route_guidance()
        if route_text:
            return NavigationInstruction(route_text, ThreatLevel.NONE, None)

        return NavigationInstruction("Path clear. Continue straight.", ThreatLevel.NONE, None)

    # ---- Output --------------------------------------------------------------

    def announce(self, instruction: NavigationInstruction, force: bool = False) -> None:
        """
        Speak (or print) the instruction. Urgent safety messages always
        repeat if still true; non-urgent messages are de-duplicated so the
        user isn't hearing "path clear, continue straight" every 300ms.
        """
        should_speak = (
            force
            or instruction.threat_level == ThreatLevel.URGENT
            or instruction.spoken_text != self._last_spoken_text
        )
        if not should_speak:
            return

        print(f"[{instruction.threat_level.value.upper()}] {instruction.spoken_text}")
        self._last_spoken_text = instruction.spoken_text

        if self.speak_enabled and self._tts_engine is not None:
            self._speak(instruction.spoken_text)

    def _speak(self, text: str) -> None:
        # Deliberately synchronous, on the calling thread -- NOT backgrounded
        # in a new thread. On Windows, pyttsx3's SAPI5 engine is tied to the
        # thread that created it; calling it from a different thread (as a
        # naive background-thread approach does) can hang indefinitely
        # rather than raise an error. Speaking synchronously blocks briefly
        # but is reliable. (A production app that must keep a camera feed
        # rendering while speaking would instead run this on a dedicated,
        # single persistent worker thread with pythoncom.CoInitialize()
        # called on that thread -- not needed for this module's own use.)
        try:
            self._tts_engine.say(text)
            self._tts_engine.runAndWait()
        except Exception as exc:
            print(f"[NavigationEngine] Speech playback failed: {exc}")
