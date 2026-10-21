"""GestureEngine - turns tracking data into clean, one-time gesture events.

Input for every frame:
    landmarks - 21 (x, y) hand points from HandTracker, or None
    face_info - a FaceInfo from FaceTracker, or None

Output: a list of events such as ["POINTING"] or ["SMILE"] - usually empty.
Debounce + cooldown make sure a held gesture fires only ONCE, so an
action never repeats every frame.

Supported gestures:
    OPEN_PALM   -> open the menu          POINTING -> select coffee
    SWIPE_RIGHT -> next page/screen       SWIPE_LEFT -> previous page/screen
    TWO_FINGERS -> quantity +1            THUMBS_UP -> confirm
    FIST        -> cancel / clear         BLINK     -> back
    SMILE       -> 10% discount
"""
import time
from collections import Counter, deque

from src import config
from src.geometry import distance

# MediaPipe point numbers: (tip, middle joint) for each of the four fingers
INDEX = (8, 6)
MIDDLE = (12, 10)
RING = (16, 14)
PINKY = (20, 18)


class GestureEngine:
    """Recognizes hand poses, swipes, smiles and blinks - with debounce."""

    def __init__(self, clock=None):
        # The clock is injectable so tests can control time exactly.
        self._clock = clock or time.time
        # hand pose stability (majority vote + hold time)
        self.recent = deque(maxlen=5)
        self.stable_gesture = "NONE"
        self.started_at = self._clock()
        self.has_fired = False
        self.last_event_time = 0.0
        # swipe tracking (positions of the palm over time)
        self.motion_history = deque()
        self.swipe_blocked_until = 0.0
        # face events (deliberate smile / blink)
        self.smile_started_at = None
        self.smile_has_fired = False
        self.eyes_closed_at = None
        self.blink_has_fired = False
        self.last_blink_time = 0.0

    # ============================================================ main entry
    def update(self, landmarks, face_info=None):
        """Call once per frame. Returns the events that fired this frame."""
        events = []
        hand_event = self._hand_event(landmarks)
        if hand_event:
            events.append(hand_event)
        events.extend(self._face_events(face_info))
        return events

    def rearm(self):
        """Allow the current gesture to fire again (used when an action failed)."""
        self.has_fired = False
        self.started_at = self._clock()

    @property
    def progress(self):
        """0.0 to 1.0: how close the held gesture is to firing (for the UI)."""
        if self.stable_gesture == "NONE" or self.has_fired:
            return 0.0
        hold = config.GESTURE_HOLD_SECONDS.get(self.stable_gesture, 0.7)
        return min(1.0, (self._clock() - self.started_at) / hold)

    # ============================================================ hand poses
    def _hand_event(self, landmarks):
        raw = self._recognize_hand(landmarks)
        if raw.startswith("SWIPE"):
            return self._handle_swipe(raw)
        return self._stabilize(raw)

    def _recognize_hand(self, landmarks):
        """Name the hand pose of ONE frame (and detect swipes over time)."""
        if landmarks is None:
            self.motion_history.clear()
            return "NONE"
        gesture = self._classify_pose(landmarks)
        if gesture == "OPEN_PALM":
            swipe = self._detect_swipe(landmarks)
            if swipe:
                return swipe
        else:
            self.motion_history.clear()
        return gesture

    def _classify_pose(self, landmarks):
        index_up = self._is_finger_extended(landmarks, INDEX)
        middle_up = self._is_finger_extended(landmarks, MIDDLE)
        ring_up = self._is_finger_extended(landmarks, RING)
        pinky_up = self._is_finger_extended(landmarks, PINKY)

        if index_up and middle_up and ring_up and pinky_up:
            return "OPEN_PALM"
        if index_up and middle_up and not ring_up and not pinky_up:
            return "TWO_FINGERS"
        if index_up and not middle_up and not ring_up and not pinky_up:
            return "POINTING"
        if not (index_up or middle_up or ring_up or pinky_up):
            # All four fingers are curled: thumb up, or a plain fist
            return "THUMBS_UP" if self._is_thumb_up(landmarks) else "FIST"
        return "NONE"

    @staticmethod
    def _is_finger_extended(landmarks, finger):
        """A straight finger has its tip farther from the wrist than its middle joint."""
        tip, middle_joint = finger
        wrist = landmarks[0]
        return distance(landmarks[tip], wrist) > distance(landmarks[middle_joint], wrist) * 1.1

    @staticmethod
    def _is_thumb_up(landmarks):
        """Thumb points upward and its tip is clearly above the index knuckle."""
        palm_size = distance(landmarks[0], landmarks[9])
        thumb_tip, thumb_joint, thumb_base = landmarks[4], landmarks[3], landmarks[2]
        index_knuckle = landmarks[5]
        points_up = thumb_tip[1] < thumb_joint[1] < thumb_base[1]   # smaller y = higher
        above_knuckle = thumb_tip[1] < index_knuckle[1] - 0.3 * palm_size
        return points_up and above_knuckle

    # ============================================================== swipes
    def _detect_swipe(self, landmarks):
        """Watch the open palm move sideways and return a swipe, or None."""
        now = self._clock()
        palm_x, palm_y = landmarks[9]
        self.motion_history.append((now, palm_x, palm_y))

        # Forget positions older than SWIPE_TIME
        while self.motion_history and now - self.motion_history[0][0] > config.SWIPE_TIME:
            self.motion_history.popleft()

        if now < self.swipe_blocked_until or len(self.motion_history) < 4:
            return None

        _, start_x, start_y = self.motion_history[0]
        move_x = palm_x - start_x
        move_y = palm_y - start_y
        is_wide_enough = abs(move_x) >= config.SWIPE_DISTANCE
        is_mostly_horizontal = abs(move_y) < abs(move_x) * 0.7
        if not (is_wide_enough and is_mostly_horizontal):
            return None

        self.motion_history.clear()
        self.swipe_blocked_until = now + config.SWIPE_COOLDOWN   # prevents repeated swipes
        # The camera image is already mirrored, so moving right on screen = user's right
        return "SWIPE_RIGHT" if move_x > 0 else "SWIPE_LEFT"

    # ============================================================ debounce
    def _stabilize(self, raw_gesture):
        """Majority vote + hold time + cooldown -> ONE event, or None."""
        now = self._clock()
        self.recent.append(raw_gesture)
        voted_gesture = Counter(self.recent).most_common(1)[0][0]

        if voted_gesture != self.stable_gesture:
            self.stable_gesture = voted_gesture
            self.started_at = now
            self.has_fired = False

        if voted_gesture == "NONE":
            return None
        if self.has_fired and not self._can_repeat(voted_gesture, now):
            return None
        hold = config.GESTURE_HOLD_SECONDS.get(voted_gesture, 0.7)
        if now - self.started_at < hold:
            return None
        if now - self.last_event_time < config.GESTURE_COOLDOWN:
            return None

        self.has_fired = True
        self.last_event_time = now
        return voted_gesture

    def _can_repeat(self, gesture, now):
        repeat_after = config.GESTURE_REPEAT_SECONDS.get(gesture)
        return repeat_after is not None and now - self.last_event_time >= repeat_after

    def _handle_swipe(self, swipe):
        now = self._clock()
        self.recent.append("OPEN_PALM")
        self.stable_gesture = "OPEN_PALM"
        self.has_fired = True    # holding the palm after a swipe must not open anything
        if now - self.last_event_time < config.GESTURE_COOLDOWN:
            return None
        self.last_event_time = now
        return swipe

    # ============================================================ face events
    def _face_events(self, face_info):
        """Turn smile / eye measurements into SMILE and BLINK events."""
        if face_info is None or not face_info.face_found:
            self.smile_started_at = None
            self.smile_has_fired = False
            self.eyes_closed_at = None
            self.blink_has_fired = False
            return []

        events = []
        now = self._clock()

        # SMILE: the smile must be held briefly, then fires once
        if face_info.is_smiling:
            if self.smile_started_at is None:
                self.smile_started_at = now
            if not self.smile_has_fired and now - self.smile_started_at >= config.SMILE_HOLD_SECONDS:
                self.smile_has_fired = True
                events.append("SMILE")
        else:
            self.smile_started_at = None
            self.smile_has_fired = False

        # BLINK: only a deliberate blink (eyes closed ~half a second) counts
        if face_info.is_eyes_closed:
            if self.eyes_closed_at is None:
                self.eyes_closed_at = now
            long_enough = now - self.eyes_closed_at >= config.BLINK_HOLD_SECONDS
            cooled_down = now - self.last_blink_time >= config.BLINK_COOLDOWN
            if long_enough and cooled_down and not self.blink_has_fired:
                self.blink_has_fired = True
                self.last_blink_time = now
                events.append("BLINK")
        else:
            self.eyes_closed_at = None
            self.blink_has_fired = False

        return events
