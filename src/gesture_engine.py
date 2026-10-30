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

Stability rules (all tunable in config.py):
    * hand poses need a majority vote over the last GESTURE_VOTE_FRAMES
      frames (e.g. 8 of 10) AND a hold time before they fire
    * per-finger HYSTERESIS (FINGER_SCORE_ON/OFF) stops one borderline frame
      from flipping a finger and thus the whole pose
    * swipes need distance + speed + direction consistency - slow drifts and
      jittery back-and-forth motion are ignored
    * a blink is a full OPEN -> CLOSED -> OPEN cycle with min/max duration
    * a smile must hold SMILE_HOLD_SECONDS for SMILE_STABLE_FRAMES frames
    * every event respects its cooldown; nothing fires from a single frame
    * rejection_reason says WHY the current pose was not accepted (debug HUD)
"""
import math
import time
from collections import Counter, deque
from src import config
from src.geometry import distance
INDEX = (5, 6, 8)
MIDDLE = (9, 10, 12)
RING = (13, 14, 16)
PINKY = (17, 18, 20)

FINGER_NAMES = ("thumb", "index", "middle", "ring", "pinky")
class GestureEngine:
    """Recognizes hand poses, swipes, smiles and blinks - with debounce."""
    def __init__(self, clock=None):
        self._clock = clock or time.time
        self.recent = deque(maxlen=config.GESTURE_VOTE_FRAMES)
        self.stable_gesture = "NONE"
        self.previous_gesture = "NONE"     
        self.started_at = self._clock()
        self.has_fired = False
        self.last_event_time = 0.0
        self.last_event = "NONE"      
        self.rejection_reason = "no hand"   
        self._finger_up = {name: False for name in FINGER_NAMES}
        self.hand_missing_frames = 0     
        self.pose_note = ""              
        self.motion_history = deque()
        self.swipe_blocked_until = 0.0
        self.swipe_debug = {"state": "idle", "direction": "-", "dx": 0.0,
                            "dy": 0.0, "speed": 0.0, "path_ratio": 0.0}
        self.smile_started_at = None
        self.smile_has_fired = False
        self.smile_frames = 0         
        self.eyes_were_open = False    
        self.eyes_closed_at = None     
        self.last_blink_time = 0.0
        self.last_face_time = 0.0
    def update(self, landmarks, face_info=None):
        """Call once per frame. Returns the events that fired this frame."""
        events = []
        hand_event = self._hand_event(landmarks)
        if hand_event:
            self.last_event = hand_event
            self.rejection_reason = ""
            events.append(hand_event)
        for face_event in self._face_events(face_info):
            self.last_event = face_event
            events.append(face_event)
        return events

    def rearm(self):
        """Allow the current gesture to fire again (used when an action failed)."""
        self.has_fired = False
        self.started_at = self._clock()

    def reset_face_state(self):
        """Forget half-held smiles/blinks (called when a new order starts)."""
        self.smile_started_at = None
        self.smile_has_fired = False
        self.smile_frames = 0
        self.eyes_closed_at = None
        self.eyes_were_open = False

    def _reset_hand_state(self):
        """Forget everything learned from a hand that disappeared."""
        self.recent.clear()
        self.stable_gesture = "NONE"
        self.started_at = self._clock()
        self.has_fired = False
        self._finger_up = {name: False for name in FINGER_NAMES}
        self.motion_history.clear()
        self.swipe_debug.update(state="idle", direction="-", dx=0.0, dy=0.0,
                                speed=0.0, path_ratio=0.0)
        self.rejection_reason = "hand lost"

    @property
    def progress(self):
        """0.0 to 1.0: how close the held gesture is to firing (for the UI)."""
        if self.stable_gesture == "NONE" or self.has_fired:
            return 0.0
        hold = config.GESTURE_HOLD_SECONDS.get(self.stable_gesture, 0.7)
        return min(1.0, (self._clock() - self.started_at) / hold)

    @property
    def smile_progress(self):
        """0.0 to 1.0: how long the current smile has been held (for the UI)."""
        if self.smile_started_at is None:
            return 0.0
        return min(1.0, (self._clock() - self.smile_started_at) / config.SMILE_HOLD_SECONDS)

    @property
    def blink_progress(self):
        """0.0 to 1.0: how long the eyes have been closed (for the UI)."""
        if self.eyes_closed_at is None:
            return 0.0
        return min(1.0, (self._clock() - self.eyes_closed_at) / config.BLINK_MAX_SECONDS)
    @property
    def gesture_confidence(self):
        """Vote share of the current stable pose over the recent frames (0-1)."""
        if not self.recent or self.stable_gesture == "NONE":
            return 0.0
        votes = sum(1 for pose in self.recent if pose == self.stable_gesture)
        return votes / len(self.recent)

    @property
    def stability_streak(self):
        """How many frames in a row currently show the stable pose."""
        if not self.recent:
            return 0
        streak = 0
        for pose in reversed(self.recent):
            if pose != self.stable_gesture:
                break
            streak += 1
        return streak
    @property
    def vote_line(self):
        """Debug text like '9/10' - votes for the stable pose vs window size."""
        if not self.recent:
            return "0/0"
        votes = sum(1 for pose in self.recent if pose == self.stable_gesture)
        return f"{votes}/{len(self.recent)}"

    @property
    def cooldown_remaining(self):
        """Seconds until another hand-gesture event is allowed."""
        return max(0.0, self.last_event_time + config.GESTURE_COOLDOWN - self._clock())
    @property
    def face_cooldown_remaining(self):
        """Seconds until another BLINK is allowed."""
        return max(0.0, self.last_blink_time + config.BLINK_COOLDOWN - self._clock())
    def _hand_event(self, landmarks):
        if landmarks is None:
            self.hand_missing_frames += 1
            self.rejection_reason = "hand lost"
            if self.hand_missing_frames >= config.HAND_LOST_RESET_FRAMES:
                self._reset_hand_state()
            return None
        self.hand_missing_frames = 0
        raw, note = self._recognize_hand(landmarks)
        self.pose_note = note
        if raw.startswith("SWIPE"):
            return self._handle_swipe(raw)
        return self._stabilize(raw, note)

    def _recognize_hand(self, landmarks):
        """Name the hand pose of ONE frame (and detect swipes over time)."""
        gesture, note = self._classify_pose(landmarks)
        swipe = self._detect_swipe(landmarks, accept=gesture == "OPEN_PALM")
        if swipe:
            return swipe, note
        return gesture, note

    def _classify_pose(self, landmarks):
        """Return (gesture, note) from the per-finger hysteresis states.

        Each finger is measured with a two-cue score (PIP straightness +
        normalized reach) and smoothed by hysteresis, so one noisy frame
        cannot flip a finger - and with it the whole pose.
        """
        up = self._measure_fingers(landmarks)
        fingers_up = [name for name in ("index", "middle", "ring", "pinky")
                      if up[name]]

        if len(fingers_up) == 4:
            return "OPEN_PALM", ""
        if fingers_up == ["index", "middle"]:
            return "TWO_FINGERS", ""
        if fingers_up == ["index"]:
            return "POINTING", ""
        if not fingers_up:
            if up["thumb"] and self._is_thumb_up(landmarks):
                return "THUMBS_UP", ""
            return "FIST", ""
        shown = ", ".join(fingers_up + (["thumb"] if up["thumb"] else []))
        return "NONE", f"unclear: {shown}"
    def _measure_fingers(self, landmarks):
        """Update and return the per-finger up/down states for this frame."""
        return self._measure_into(landmarks, self._finger_up)

    @classmethod
    def _measure_into(cls, landmarks, state):
        """Apply one frame of finger scores to `state` (in place); return it.

        Used by the classifier (hysteresis kept across frames) and by the
        display path (fresh single-frame measurement).
        """
        cls._apply_into(state, "thumb", cls._thumb_score(landmarks))
        for name, joints in (("index", INDEX), ("middle", MIDDLE),
                             ("ring", RING), ("pinky", PINKY)):
            cls._apply_into(state, name, cls._finger_score(landmarks, joints))
        return state

    @staticmethod
    def _apply_into(state, name, score):
        """Hysteresis: only clear thresholds change the state."""
        if score >= config.FINGER_SCORE_ON:
            state[name] = True
        elif score <= config.FINGER_SCORE_OFF:
            state[name] = False
        return state[name]

    @classmethod
    def _finger_score(cls, landmarks, finger):
        """Extension score for one finger: > 0 extended, < 0 curled.

        Two rotation/scale-invariant cues are blended:
          * straightness - the angle at the PIP joint (180 deg = straight)
          * reach        - how far the tip sits beyond the pip, relative to
                           the palm size (positive when the finger sticks out)
        """
        mcp, pip, tip = finger
        straight = cls._angle_score(landmarks, mcp, pip, tip)
        palm = max(distance(landmarks[0], landmarks[9]), 1e-6)
        reach = (distance(landmarks[tip], landmarks[0])
                 - distance(landmarks[pip], landmarks[0])) / palm
        reach = max(-1.0, min(1.0, reach / config.FINGER_REACH_FULL))
        weight = config.FINGER_STRAIGHT_WEIGHT
        return weight * straight + (1.0 - weight) * reach

    @classmethod
    def _thumb_score(cls, landmarks):
        """Thumb extension score (same two cues, reach measured to the palm centre)."""
        straight = cls._angle_score(landmarks, 2, 3, 4)    
        palm = max(distance(landmarks[0], landmarks[9]), 1e-6)
        center = cls._palm_center(landmarks)
        reach = (distance(landmarks[4], center)
                 - distance(landmarks[3], center)) / palm
        reach = max(-1.0, min(1.0, reach / config.FINGER_REACH_FULL))
        weight = config.FINGER_STRAIGHT_WEIGHT
        return weight * straight + (1.0 - weight) * reach

    @staticmethod
    def _angle_score(landmarks, mcp_i, pip_i, tip_i):
        """1.0 = straight finger at the PIP joint, 0.0 = fully folded.
        Pure geometry - unaffected by hand rotation, distance to the camera
        or left/right handedness.
        """
        mcp, pip, tip = landmarks[mcp_i], landmarks[pip_i], landmarks[tip_i]
        a = distance(pip, mcp)
        b = distance(pip, tip)
        c = distance(mcp, tip)
        if a < 1e-6 or b < 1e-6:
            return 1.0 if (a + b + c) > 1e-6 else 0.0   
        cosine = (a * a + b * b - c * c) / (2.0 * a * b)
        cosine = max(-1.0, min(1.0, cosine))
        return math.acos(cosine) / math.pi

    @staticmethod
    def _palm_center(landmarks):
        """Centre of the palm: mean of the wrist and the four finger knuckles."""
        indexes = (0, 5, 9, 13, 17)
        x = sum(landmarks[i][0] for i in indexes) / len(indexes)
        y = sum(landmarks[i][1] for i in indexes) / len(indexes)
        return (x, y)

    def current_finger_states(self, landmarks):
        """Live hysteresis states for the camera panel (what the engine used).

        Returns a copy of the per-finger up/down states, or None when no hand
        is visible. update() must have run for this frame (main.py order).
        """
        if landmarks is None:
            return None
        return dict(self._finger_up)

    @staticmethod
    def finger_states(landmarks):
        """Fresh single-frame finger measurement, or None without a hand.

        Returns {"thumb": bool, "index": bool, "middle": bool, "ring": bool,
        "pinky": bool}. Used by tests and any caller that has no engine
        instance; main.py prefers current_finger_states() so the panel chips
        always match the classifier's hysteresis states.
        """
        if landmarks is None:
            return None
        return GestureEngine._measure_into(
            landmarks, {name: False for name in FINGER_NAMES})

    @staticmethod
    def _is_thumb_up(landmarks):
        """Thumb tip reaches beyond the index knuckle along the hand's own axis.

        The axis is wrist -> middle knuckle instead of screen "up", so the
        gesture works for every hand orientation (upright, sideways, tilted)
        and for left and right hands alike. Finger-foldedness is checked by
        the caller through the thumb score / finger states.
        """
        wrist, knuckle = landmarks[0], landmarks[9]
        axis_x = knuckle[0] - wrist[0]
        axis_y = knuckle[1] - wrist[1]
        axis_len = math.hypot(axis_x, axis_y)
        if axis_len < 1e-6:
            return False

        def along(point):
            return ((point[0] - wrist[0]) * axis_x
                    + (point[1] - wrist[1]) * axis_y) / axis_len

        thumb_tip = along(landmarks[4])
        index_knuckle = along(landmarks[5])
        return thumb_tip >= index_knuckle + config.THUMB_UP_OVER_KNUCKLE * axis_len
    def _detect_swipe(self, landmarks, accept):
        """Watch the palm centre move sideways FAST and return a swipe, or None.

        Tracking uses the palm CENTRE (mean of wrist + 4 knuckles), which is
        far less jittery than a single landmark. A swipe only fires when:
          * the current pose is an open palm (`accept`)
          * >= SWIPE_MIN_FRAMES of history inside SWIPE_TIME
          * distance >= SWIPE_DISTANCE, speed >= SWIPE_MIN_SPEED
          * mostly horizontal, and direction consistent (SWIPE_MIN_PATH_RATIO)
        Motion history survives 1-2 missing frames; it is cleared on a full
        hand-loss reset and after every accepted swipe.
        """
        now = self._clock()
        center = self._palm_center(landmarks)
        self.motion_history.append((now, center[0], center[1]))
        while self.motion_history and now - self.motion_history[0][0] > config.SWIPE_TIME:
            self.motion_history.popleft()

        start_time, start_x, start_y = self.motion_history[0]
        move_x = center[0] - start_x
        move_y = center[1] - start_y
        elapsed = max(now - start_time, 1e-6)
        speed = abs(move_x) / elapsed              
        path = self._path_length()
        ratio = math.hypot(move_x, move_y) / path if path > 1e-9 else 0.0
        self.swipe_debug.update(dx=move_x, dy=move_y, speed=speed,
                                path_ratio=ratio, direction=self._arrow(move_x, move_y))

        if now < self.swipe_blocked_until:
            self.swipe_debug["state"] = "cooldown"
            return None
        if not accept:
            self.swipe_debug["state"] = "not open palm"
            return None
        if len(self.motion_history) < config.SWIPE_MIN_FRAMES:
            self.swipe_debug["state"] = f"tracking {len(self.motion_history)}" \
                                        f"/{config.SWIPE_MIN_FRAMES}"
            return None

        is_wide_enough = abs(move_x) >= config.SWIPE_DISTANCE
        is_fast_enough = speed >= config.SWIPE_MIN_SPEED       
        is_mostly_horizontal = abs(move_y) < abs(move_x) * config.SWIPE_MAX_VERTICAL_RATIO
        is_consistent = ratio >= config.SWIPE_MIN_PATH_RATIO   
        if not is_wide_enough:
            self.swipe_debug["state"] = f"too short {abs(move_x):.2f}" \
                                        f"<{config.SWIPE_DISTANCE:.2f}"
            return None
        if not is_fast_enough:
            self.swipe_debug["state"] = f"too slow {speed:.2f}" \
                                        f"<{config.SWIPE_MIN_SPEED:.2f}"
            return None
        if not is_mostly_horizontal:
            self.swipe_debug["state"] = "too vertical"
            return None
        if not is_consistent:
            self.swipe_debug["state"] = f"jittery {ratio:.2f}" \
                                        f"<{config.SWIPE_MIN_PATH_RATIO:.2f}"
            return None
        self.motion_history.clear()
        self.swipe_blocked_until = now + config.SWIPE_COOLDOWN  
        self.swipe_debug["state"] = "fired"
        return "SWIPE_RIGHT" if move_x > 0 else "SWIPE_LEFT"

    def _path_length(self):
        """Total distance travelled by the palm centre in the current window."""
        path = 0.0
        previous = None
        for _time, x, y in self.motion_history:
            if previous is not None:
                path += math.hypot(x - previous[0], y - previous[1])
            previous = (x, y)
        return path
    @staticmethod
    def _arrow(move_x, move_y):
        """Movement direction as an arrow for the debug HUD."""
        if abs(move_x) < 1e-6 and abs(move_y) < 1e-6:
            return "-"
        if abs(move_x) >= abs(move_y):
            return "right" if move_x > 0 else "left"
        return "down" if move_y > 0 else "up"
    def _stabilize(self, raw_gesture, note=""):
        """Majority vote + confidence + hold + cooldown -> ONE event, or None.

        Every rejection path records rejection_reason so the debug HUD can
        explain WHY the current pose was not accepted.
        """
        now = self._clock()
        self.recent.append(raw_gesture)
        voted_gesture = Counter(self.recent).most_common(1)[0][0]

        if voted_gesture != self.stable_gesture:
            self.previous_gesture = self.stable_gesture
            self.stable_gesture = voted_gesture
            self.started_at = now           # a new pose must earn its full hold
            self.has_fired = False

        if voted_gesture == "NONE":
            self.rejection_reason = note or "pose unclear"
            return None
        if self.has_fired and not self._can_repeat(voted_gesture, now):
            self.rejection_reason = "already fired (latched)"
            return None
        votes = sum(1 for pose in self.recent if pose == voted_gesture)
        if votes < config.GESTURE_MIN_CONFIDENCE * len(self.recent):
            self.rejection_reason = (f"vote {votes}/{len(self.recent)} < "
                                     f"{config.GESTURE_MIN_CONFIDENCE:.0%}")
            return None
        hold = config.GESTURE_HOLD_SECONDS.get(voted_gesture, 0.7)
        held = now - self.started_at
        if held < hold:
            self.rejection_reason = f"holding {held:.1f}/{hold:.1f}s"
            return None
        if now - self.last_event_time < config.GESTURE_COOLDOWN:
            remaining = config.GESTURE_COOLDOWN - (now - self.last_event_time)
            self.rejection_reason = f"cooldown {remaining:.1f}s"
            return None

        self.has_fired = True
        self.last_event_time = now
        self.rejection_reason = ""
        return voted_gesture

    def _can_repeat(self, gesture, now):
        repeat_after = config.GESTURE_REPEAT_SECONDS.get(gesture)
        return repeat_after is not None and now - self.last_event_time >= repeat_after

    def _handle_swipe(self, swipe):
        now = self._clock()
        self.recent.append("OPEN_PALM")
        self.stable_gesture = "OPEN_PALM"
        self.has_fired = True    
        if now - self.last_event_time < config.GESTURE_COOLDOWN:
            return None
        self.last_event_time = now
        return swipe

    def _face_events(self, face_info):
        """Turn smile / eye measurements into SMILE and BLINK events."""
        now = self._clock()
        if face_info is None or not face_info.face_found:
            return self._face_lost(now)

        self.last_face_time = now
        events = []

        if face_info.is_smiling:
            self.smile_frames += 1
            if self.smile_started_at is None:
                self.smile_started_at = now
            if (not self.smile_has_fired
                    and self.smile_frames >= config.SMILE_STABLE_FRAMES
                    and now - self.smile_started_at >= config.SMILE_HOLD_SECONDS):
                self.smile_has_fired = True
                events.append("SMILE")
        else:
            self.smile_started_at = None
            self.smile_has_fired = False
            self.smile_frames = 0
        if face_info.is_eyes_closed:
            if self.eyes_closed_at is None and self.eyes_were_open:
                self.eyes_closed_at = now      # this closure counts
        else:
            self.eyes_were_open = True
            if self.eyes_closed_at is not None:
                duration = now - self.eyes_closed_at
                self.eyes_closed_at = None
                if (config.BLINK_MIN_SECONDS <= duration <= config.BLINK_MAX_SECONDS
                        and now - self.last_blink_time >= config.BLINK_COOLDOWN):
                    self.last_blink_time = now
                    events.append("BLINK")
        return events

    def _face_lost(self, now):
        """Face gone: forget the smile; keep a half-finished blink briefly."""
        self.smile_started_at = None
        self.smile_has_fired = False
        self.smile_frames = 0
        lost_for = now - self.last_face_time
        if self.eyes_closed_at is not None and lost_for <= config.FACE_LOST_GRACE_SECONDS:
            return []       
        self.eyes_closed_at = None
        self.eyes_were_open = False   
        return []