"""Hand and face tracking with MediaPipe.

This file ONLY tracks what the camera sees. It does not decide what a
gesture means - that is the job of gesture_engine.py.

    HandTracker.find_hand(frame) -> 21 (x, y) hand points, or None
    FaceTracker.detect(frame)    -> FaceInfo with simple True/False values
"""
from collections import deque
from dataclasses import dataclass

import cv2

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


@dataclass
class FaceInfo:
    """Simple measurements taken from one camera frame."""
    face_found: bool = False
    is_smiling: bool = False        # True while the person is smiling
    is_eyes_closed: bool = False    # True while the eyes are closed
    smile_ratio: float = 0.0        # mouth width / face width (debug view)
    eye_ratio: float = 0.0          # eye openness (debug view)


class HandTracker:
    """Finds one hand in a camera frame using MediaPipe Hands."""

    def __init__(self):
        self.hands = None
        self.error_message = ""

        problem = mediapipe_problem()
        if problem:
            self.error_message = problem
            print(f"[HandTracker] {self.error_message}")
            return

        try:
            self.hands = mp.solutions.hands.Hands(  # type: ignore[union-attr,attr-defined]
                static_image_mode=False,
                max_num_hands=1,            # one hand is enough for this project
                model_complexity=0,         # 0 = fastest model
                min_detection_confidence=0.6,
                min_tracking_confidence=0.5,
            )
        except Exception as error:          # never crash on a broken machine setup
            self.error_message = f"Could not start hand tracking: {error}"
            print(f"[HandTracker] {self.error_message}")

    @property
    def is_available(self):
        return self.hands is not None

    def find_hand(self, frame):
        """Look for a hand in a BGR frame.

        Returns a list of 21 (x, y) points (values from 0 to 1), or None.
        Point numbers follow MediaPipe: 0 = wrist, 4 = thumb tip,
        8 = index tip, ...
        """
        if self.hands is None or frame is None:
            return None
        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)   # MediaPipe wants RGB
            result = self.hands.process(rgb_frame)
        except Exception as error:          # a detection failure must not crash the app
            self.error_message = f"Hand tracking error: {error}"
            print(f"[HandTracker] {self.error_message}")
            return None
        if not result.multi_hand_landmarks:
            return None
        hand = result.multi_hand_landmarks[0]
        return [(point.x, point.y) for point in hand.landmark]

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


class FaceTracker:
    """Measures smile and eye state using MediaPipe Face Mesh.

    It only measures - turning the measurements into the SMILE / BLINK
    events (with hold time and cooldown) happens in gesture_engine.py.
    """

    def __init__(self):
        self.face_mesh = None
        self.error_message = ""
        self._open_history = deque(maxlen=config.EYE_BASELINE_FRAMES)   # recent "eyes open" values
        self._recent_eye = deque(maxlen=config.EYE_SMOOTH_FRAMES)       # for smoothing

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

    def detect(self, frame):
        """Analyse one BGR frame and return a FaceInfo."""
        if self.face_mesh is None or frame is None:
            return FaceInfo()
        try:
            result = self.face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        except Exception as error:
            self.error_message = f"Face tracking error: {error}"
            print(f"[FaceTracker] {self.error_message}")
            return FaceInfo()
        if not result.multi_face_landmarks:
            self._recent_eye.clear()
            return FaceInfo()          # no face -> everything False

        height, width = frame.shape[:2]
        points = [(p.x * width, p.y * height) for p in result.multi_face_landmarks[0].landmark]
        smile_ratio = self._get_smile_ratio(points)
        self._recent_eye.append(self._get_eye_ratio(points))
        eye_ratio = sum(self._recent_eye) / len(self._recent_eye)      # smoothed
        return FaceInfo(
            face_found=True,
            is_smiling=smile_ratio > config.SMILE_RATIO_THRESHOLD,
            is_eyes_closed=self._is_closed(eye_ratio),
            smile_ratio=smile_ratio,
            eye_ratio=eye_ratio,
        )

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
    def _get_smile_ratio(points):
        mouth_width = distance(points[MOUTH_CORNERS[0]], points[MOUTH_CORNERS[1]])
        face_width = distance(points[FACE_EDGES[0]], points[FACE_EDGES[1]])
        return mouth_width / face_width if face_width > 0 else 0.0

    @staticmethod
    def _eye_openness(points, eye):
        corner_a, top_1, top_2, corner_b, bottom_2, bottom_1 = (points[i] for i in eye)
        eye_width = distance(corner_a, corner_b)
        eye_height = distance(top_1, bottom_1) + distance(top_2, bottom_2)
        return eye_height / (2 * eye_width) if eye_width > 0 else 0.0

    def _get_eye_ratio(self, points):
        return (self._eye_openness(points, LEFT_EYE) + self._eye_openness(points, RIGHT_EYE)) / 2

    def close(self):
        if self.face_mesh is not None:
            self.face_mesh.close()
            self.face_mesh = None
