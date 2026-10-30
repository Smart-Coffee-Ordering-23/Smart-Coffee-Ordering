"""Hand and face tracking with MediaPipe.

This file ONLY tracks what the camera sees. It does not decide what a
gesture means - that is the job of gesture_engine.py.

    HandTracker.find_hand(frame) -> 21 (x, y) hand points, or None
    FaceTracker.detect(frame)    -> FaceInfo with measurements + states
"""
from collections import deque
from dataclasses import dataclass

from src import config
from src.geometry import distance

try:
    import mediapipe as mp
except ImportError:          # MediaPipe is not installed
    mp = None


def mediapipe_problem():
    """None when MediaPipe is usable, otherwise a friendly error message.

    Shared by HandTracker and FaceTracker so the check exists only once.
    """
    if mp is None or not hasattr(mp, "solutions"):
        return ("MediaPipe is missing or the wrong version. "
                "Run: python -m pip install -r requirements.txt")
    return None


def _connection_pairs(*set_names):
    """Flatten MediaPipe connection sets into plain (a, b) tuples.

    Used by the renderer to draw face landmarks in DEBUG_MODE. Returns an
    empty tuple when MediaPipe is unavailable.
    """
    if mp is None or not hasattr(mp, "solutions"):
        return ()
    face_mesh = getattr(mp.solutions, "face_mesh", None)
    if face_mesh is None:
        return ()
    pairs = set()
    for name in set_names:
        for connection in getattr(face_mesh, name, ()):
            pairs.add(tuple(sorted(connection)))
    return tuple(sorted(pairs))


# Debug-only face outline: oval + eyes + lips (MediaPipe's own definitions)
FACE_DEBUG_LINES = _connection_pairs("FACEMESH_FACE_OVAL", "FACEMESH_LEFT_EYE",
                                     "FACEMESH_RIGHT_EYE", "FACEMESH_LIPS")


@dataclass
class FaceInfo:
    """Simple measurements taken from one camera frame."""
    face_found: bool = False
    is_smiling: bool = False        # True while the person is smiling
    is_eyes_closed: bool = False    # True while the eyes are closed
    smile_ratio: float = 0.0        # mouth width / face width (debug view)
    eye_ratio: float = 0.0          # Eye Aspect Ratio (debug view)
    smile_lift: float = 0.0         # nose-tip -> mouth-corner gap / face height
    smile_threshold: float = 0.0    # effective width threshold this frame
    eye_open: bool = False          # explicit OPEN/CLOSED for the debug HUD


class HandTracker:
    """Finds the clearest hand in a camera frame using MediaPipe Hands.

    MediaPipe landmark indices are ANATOMICAL (thumb tip is always 4, index
    tip always 8, ...) for both left and right hands, so every distance/angle
    rule in GestureEngine is handedness-neutral. The handedness label is only
    used for display and for picking the clearest of several detected hands.
    """

    def __init__(self):
        self.hands = None
        self.error_message = ""
        self.last_confidence = 0.0     # MediaPipe score of the selected hand
        self.last_handedness = "-"     # "Left" / "Right" of the selected hand
        self.last_palm_size = 0.0      # normalized wrist->knuckle distance

        problem = mediapipe_problem()
        if problem:
            self.error_message = problem
            print(f"[HandTracker] {self.error_message}")
            return

        try:
            self.hands = mp.solutions.hands.Hands(  # type: ignore[union-attr,attr-defined]
                static_image_mode=False,
                max_num_hands=config.HAND_MAX_NUM_HANDS,   # 2 = we can pick the clearest
                model_complexity=0,         # 0 = fastest model
                min_detection_confidence=config.HAND_MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=config.HAND_MIN_TRACKING_CONFIDENCE,
            )
        except Exception as error:          # never crash on a broken machine setup
            self.error_message = f"Could not start hand tracking: {error}"
            print(f"[HandTracker] {self.error_message}")

    @property
    def is_available(self):
        return self.hands is not None

    def find_hand(self, rgb_frame):
        """Look for the clearest hand in an RGB frame (MediaPipe's format).

        Returns a list of 21 (x, y) points (values from 0 to 1), or None.
        Several safeguards run before a hand is accepted:
          * MediaPipe confidence (handedness score) >= HAND_MIN_SCORE
          * plausible landmarks (all near the frame, palm not tiny/cut off)
          * when several hands are seen, the clearest one is kept
        """
        if self.hands is None or rgb_frame is None:
            self._forget()
            return None
        try:
            result = self.hands.process(rgb_frame)   # frame is already RGB
        except Exception as error:          # a detection failure must not crash the app
            self.error_message = f"Hand tracking error: {error}"
            print(f"[HandTracker] {self.error_message}")
            self._forget()
            return None

        hands = getattr(result, "multi_hand_landmarks", None)
        if not hands:
            self._forget()
            return None

        candidates = []
        for index, hand in enumerate(hands):
            points = [(point.x, point.y) for point in hand.landmark]
            score, label = self._handedness(result, index)
            if score < config.HAND_MIN_SCORE:
                continue                    # MediaPipe is not sure this is a hand
            if not self._landmarks_plausible(points):
                continue                    # incomplete / too small / out of frame
            candidates.append((points, score, label, self._palm_size(points)))
        if not candidates:
            self._forget()
            return None

        points, score, label, palm = self._best_hand(candidates)
        self.last_confidence = score
        self.last_handedness = label
        self.last_palm_size = palm
        return points

    def _forget(self):
        self.last_confidence = 0.0
        self.last_handedness = "-"
        self.last_palm_size = 0.0

    # -------------------------------------------------------- static helpers
    @staticmethod
    def _handedness(result, index):
        """(score, "Left"/"Right") of the index-th detected hand."""
        try:
            classification = result.multi_handedness[index].classification[0]
            return classification.score, classification.label
        except (AttributeError, IndexError, TypeError):
            return 1.0, "-"                 # older MediaPipe without handedness

    @staticmethod
    def _palm_size(points):
        """Wrist -> middle-knuckle distance (hand scale in normalized units)."""
        if len(points) < 10:
            return 0.0
        return distance(points[0], points[9])

    @staticmethod
    def _landmarks_plausible(points):
        """Reject incomplete detections before they reach the classifier."""
        if len(points) != 21:
            return False
        margin = config.HAND_LANDMARK_MARGIN
        for x, y in points:
            if not (-margin <= x <= 1.0 + margin and -margin <= y <= 1.0 + margin):
                return False                # landmark far outside the frame
        return HandTracker._palm_size(points) >= config.HAND_MIN_PALM_SIZE

    @staticmethod
    def _best_hand(candidates):
        """Pick the clearest hand: highest confidence, then largest palm."""
        best = candidates[0]
        for candidate in candidates[1:]:
            if (candidate[1], candidate[3]) > (best[1], best[3]):
                best = candidate
        return best

    def close(self):
        if self.hands is not None:
            self.hands.close()
            self.hands = None


# ===================================================================== face
# MediaPipe Face Mesh point numbers
LEFT_EYE = (33, 160, 158, 133, 153, 144)      # corner, top1, top2, corner, bottom2, bottom1
RIGHT_EYE = (362, 385, 387, 263, 373, 380)
MOUTH_CORNERS = (61, 291)
FACE_EDGES = (234, 454)
NOSE_TIP = 1              # the corners rise toward it when smiling
FOREHEAD_TOP = 10         # with CHIN these define the face height for normalization
CHIN_BOTTOM = 152


class FaceTracker:
    """Measures smile and eye state using MediaPipe Face Mesh.

    It only measures - turning the measurements into the SMILE / BLINK
    events (with hold time and cooldown) happens in gesture_engine.py.

    Smile detection uses TWO independent measurements (mouth width AND
    corner raise), both compared against this person's neutral baseline,
    so a plain wide mouth is not mistaken for a smile.
    """

    def __init__(self):
        self.face_mesh = None
        self.error_message = ""
        self.last_points = None        # normalized (x, y) points of the last face (debug)
        self._open_history = deque(maxlen=config.EYE_BASELINE_FRAMES)   # recent "eyes open" values
        self._recent_eye = deque(maxlen=config.EYE_SMOOTH_FRAMES)       # for smoothing
        self._width_history = deque(maxlen=config.SMILE_BASELINE_FRAMES)   # neutral mouth widths
        self._lift_history = deque(maxlen=config.SMILE_BASELINE_FRAMES)    # neutral corner gaps

        problem = mediapipe_problem()
        if problem:
            self.error_message = problem
            print(f"[FaceTracker] {self.error_message}")
            return

        try:
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(  # type: ignore[union-attr,attr-defined]
                static_image_mode=False,
                max_num_faces=1,
                refine_landmarks=True,      # more accurate eyelids -> better closed-eye detection
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        except Exception as error:          # never crash on a broken machine setup
            self.error_message = f"Could not start face tracking: {error}"
            print(f"[FaceTracker] {self.error_message}")

    @property
    def is_available(self):
        return self.face_mesh is not None

    def detect(self, rgb_frame):
        """Analyse one RGB frame (MediaPipe's format) and return a FaceInfo."""
        if self.face_mesh is None or rgb_frame is None:
            return FaceInfo()
        try:
            result = self.face_mesh.process(rgb_frame)   # already RGB - no conversion
        except Exception as error:
            self.error_message = f"Face tracking error: {error}"
            print(f"[FaceTracker] {self.error_message}")
            return FaceInfo()
        if not result.multi_face_landmarks:
            self._recent_eye.clear()
            self.last_points = None
            return FaceInfo()          # no face -> everything False

        height, width = rgb_frame.shape[:2]
        raw = result.multi_face_landmarks[0].landmark
        points = [(p.x * width, p.y * height) for p in raw]
        self.last_points = [(p.x, p.y) for p in raw]      # normalized, for the debug overlay

        width_ratio, lift_ratio = self._smile_metrics(points)
        self._recent_eye.append(self._get_eye_ratio(points))
        eye_ratio = sum(self._recent_eye) / len(self._recent_eye)      # smoothed
        is_closed = self._is_closed(eye_ratio)

        smiling, effective_threshold = self._classify_smile(width_ratio, lift_ratio)
        return FaceInfo(
            face_found=True,
            is_smiling=smiling,
            is_eyes_closed=is_closed,
            smile_ratio=width_ratio,
            eye_ratio=eye_ratio,
            smile_lift=lift_ratio,
            smile_threshold=effective_threshold,
            eye_open=not is_closed,
        )

    # ------------------------------------------------------------ smile
    def _classify_smile(self, width_ratio, lift_ratio):
        """Decide 'smiling' from BOTH measurements; returns (bool, width_threshold).

        Warmup (personal baseline not learned yet): the absolute mouth-width
        floor is used alone, exactly like the old behaviour.
        Afterwards a smile needs:
          * width  >= personal neutral + margin  (or the absolute floor), AND
          * corner gap shrunk by SMILE_LIFT_DROP_RATIO vs personal neutral
            (the corners must actually RISE - a wide neutral mouth fails here).
        """
        baseline_width, baseline_lift = self._smile_baseline()
        if baseline_width is None:
            # First second: only the absolute floor, while the baseline fills up.
            self._width_history.append(width_ratio)
            self._lift_history.append(lift_ratio)
            return width_ratio >= config.SMILE_WIDTH_THRESHOLD, config.SMILE_WIDTH_THRESHOLD

        threshold = baseline_width + config.SMILE_WIDTH_MARGIN
        width_ok = width_ratio >= threshold or width_ratio >= config.SMILE_WIDTH_THRESHOLD
        lift_ok = lift_ratio <= baseline_lift * (1.0 - config.SMILE_LIFT_DROP_RATIO)
        smiling = width_ok and lift_ok
        if not smiling:                     # only neutral frames teach the baseline
            self._width_history.append(width_ratio)
            self._lift_history.append(lift_ratio)
        return smiling, threshold

    def _smile_baseline(self):
        """(neutral width, neutral corner gap) or (None, None) while warming up."""
        if len(self._width_history) < config.SMILE_BASELINE_WARMUP:
            return None, None
        width = self._percentile(self._width_history, config.SMILE_BASELINE_PERCENTILE)
        lift = self._percentile(self._lift_history, 100 - config.SMILE_BASELINE_PERCENTILE)
        return width, lift

    @staticmethod
    def _percentile(values, pct):
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, int(len(ordered) * pct / 100)))
        return ordered[index]

    def _is_closed(self, eye_ratio):
        """Closed = clearly below this person's own normal open-eye value.

        Every face (and camera distance) gives a different number, so a single
        fixed threshold fails for many people. We learn the open-eye value from
        the last few seconds and compare against it.
        """
        if len(self._open_history) < config.EYE_BASELINE_WARMUP:
            self._open_history.append(eye_ratio)
            return eye_ratio < config.EYE_CLOSED_THRESHOLD
        ordered = sorted(self._open_history)
        baseline = ordered[int(len(ordered) * 0.8)]        # typical OPEN value
        closed = eye_ratio < baseline * config.EYE_CLOSED_RELATIVE
        if not closed:                                     # closed frames must not lower the baseline
            self._open_history.append(eye_ratio)
        return closed

    # ------------------------------------------------------- measurements
    @staticmethod
    def _smile_metrics(points):
        """(mouth width ratio, corner lift ratio) for one face.

        width = mouth corner distance / face width      -> a smile widens the mouth
        lift  = vertical gap nose-tip..corner-mid / face height
                -> a smile RAISES the corners, shrinking this gap.
        Two independent measurements so one wide mouth cannot fake a smile.
        """
        mouth_width = distance(points[MOUTH_CORNERS[0]], points[MOUTH_CORNERS[1]])
        face_width = distance(points[FACE_EDGES[0]], points[FACE_EDGES[1]])
        width_ratio = mouth_width / face_width if face_width > 0 else 0.0

        face_height = distance(points[FOREHEAD_TOP], points[CHIN_BOTTOM])
        corner_mid_y = (points[MOUTH_CORNERS[0]][1] + points[MOUTH_CORNERS[1]][1]) / 2
        vertical_gap = abs(corner_mid_y - points[NOSE_TIP][1])
        lift_ratio = vertical_gap / face_height if face_height > 0 else 1.0
        return width_ratio, lift_ratio

    @staticmethod
    def _eye_openness(points, eye):
        """Standard 6-point Eye Aspect Ratio for one eye."""
        corner_a, top_1, top_2, corner_b, bottom_2, bottom_1 = (points[i] for i in eye)
        eye_width = distance(corner_a, corner_b)
        eye_height = distance(top_1, bottom_1) + distance(top_2, bottom_2)
        return eye_height / (2 * eye_width) if eye_width > 0 else 0.0

    @staticmethod
    def _get_eye_ratio(points):
        """EAR averaged over both eyes (open ~0.25, closed ~0.05 for most faces)."""
        left = FaceTracker._eye_openness(points, LEFT_EYE)
        right = FaceTracker._eye_openness(points, RIGHT_EYE)
        return (left + right) / 2

    def close(self):
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None
        self.last_points = None
