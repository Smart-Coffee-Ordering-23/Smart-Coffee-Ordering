"""Unit tests for the face geometry used by FaceTracker (no camera needed).

A synthetic face is built from the MediaPipe landmark indices the tracker
uses: eyes, mouth corners, nose tip, forehead, chin and face edges. This
verifies EAR (eye blink) and the two smile measurements without a webcam.
"""
from collections import deque

from src import config
from src.hand_tracker import (CHIN_BOTTOM, FACE_EDGES, FOREHEAD_TOP, LEFT_EYE,
                              MOUTH_CORNERS, NOSE_TIP, RIGHT_EYE, FaceTracker)

FACE_SIZE = 478          # MediaPipe Face Mesh has 478 points with refine_landmarks


def bare_tracker():
    """A FaceTracker without MediaPipe startup - only the smile history is set up."""
    tracker = FaceTracker.__new__(FaceTracker)
    tracker._width_history = deque(maxlen=config.SMILE_BASELINE_FRAMES)
    tracker._lift_history = deque(maxlen=config.SMILE_BASELINE_FRAMES)
    return tracker


def make_face(eye_half_height=0.012, mouth_width=0.35, corner_raise=0.0):
    """Build a geometrically consistent synthetic face.

    eye_half_height - half of the eyelid gap (0.012 open, 0.002 closed)
    mouth_width     - mouth width / face width ratio (0.35 neutral, 0.5 smiling)
    corner_raise    - how far the mouth corners move UP toward the nose
    """
    points = [(0.5, 0.5)] * FACE_SIZE
    points[FOREHEAD_TOP] = (0.50, 0.20)      # face height (10 -> 152) = 0.60
    points[CHIN_BOTTOM] = (0.50, 0.80)
    points[NOSE_TIP] = (0.50, 0.42)
    points[FACE_EDGES[0]] = (0.25, 0.50)     # face width (234 -> 454) = 0.50
    points[FACE_EDGES[1]] = (0.75, 0.50)

    # eyes: corner_a, top1, top2, corner_b, bottom2, bottom1
    for eye, center_x in ((LEFT_EYE, 0.38), (RIGHT_EYE, 0.62)):
        corner_a = (center_x - 0.05, 0.35)
        corner_b = (center_x + 0.05, 0.35)
        points[eye[0]], points[eye[3]] = corner_a, corner_b
        points[eye[1]] = (center_x - 0.015, 0.35 - eye_half_height)
        points[eye[2]] = (center_x + 0.015, 0.35 - eye_half_height)
        points[eye[4]] = (center_x + 0.015, 0.35 + eye_half_height)
        points[eye[5]] = (center_x - 0.015, 0.35 + eye_half_height)

    # mouth corners at the requested width, raised by corner_raise
    half = mouth_width * 0.50 / 2           # width ratio * face width / 2
    corner_y = 0.60 - corner_raise
    points[MOUTH_CORNERS[0]] = (0.50 - half, corner_y)
    points[MOUTH_CORNERS[1]] = (0.50 + half, corner_y)
    return points


# ------------------------------------------------------------------- EAR
def test_ear_is_high_when_eyes_open():
    ear = FaceTracker._get_eye_ratio(make_face(eye_half_height=0.012))
    assert ear > 0.15                        # open eyes sit well above 0.15


def test_ear_is_low_when_eyes_closed():
    ear = FaceTracker._get_eye_ratio(make_face(eye_half_height=0.002))
    assert ear < 0.06                        # closed eyes collapse the ratio


def test_ear_averages_both_eyes():
    points = make_face()
    left = FaceTracker._eye_openness(points, LEFT_EYE)
    right = FaceTracker._eye_openness(points, RIGHT_EYE)
    both = FaceTracker._get_eye_ratio(points)
    assert abs(both - (left + right) / 2) < 1e-9


def test_ear_is_scale_invariant():
    """Same eye shape at a different face size must give the same EAR."""
    small = make_face()
    big = [(x * 2.0, y * 2.0) for x, y in make_face()]
    assert abs(FaceTracker._get_eye_ratio(small)
               - FaceTracker._get_eye_ratio(big)) < 1e-9


# ----------------------------------------------------------------- smile
def test_smile_width_grows_with_mouth():
    narrow, _ = FaceTracker._smile_metrics(make_face(mouth_width=0.30))
    wide, _ = FaceTracker._smile_metrics(make_face(mouth_width=0.50))
    assert wide > narrow
    assert abs(wide - 0.50) < 1e-9           # width ratio == mouth_width input


def test_smile_lift_shrinks_when_corners_rise():
    _, neutral = FaceTracker._smile_metrics(make_face(corner_raise=0.0))
    _, raised = FaceTracker._smile_metrics(make_face(corner_raise=0.08))
    assert raised < neutral                  # smiling pulls the corners up


def test_warmup_uses_absolute_width_only():
    """Before the baseline exists, the classic width floor decides alone."""
    tracker = bare_tracker()

    smiling, threshold = tracker._classify_smile(0.50, 0.30)
    assert smiling is True
    assert threshold == config.SMILE_WIDTH_THRESHOLD

    smiling, _ = tracker._classify_smile(0.30, 0.30)
    assert smiling is False


def test_baseline_rejects_wide_neutral_mouth():
    """A wide neutral mouth (no corner raise) must NOT read as a smile."""
    tracker = bare_tracker()
    for _ in range(config.SMILE_BASELINE_WARMUP):   # learn a wide neutral mouth
        tracker._width_history.append(0.52)
        tracker._lift_history.append(0.30)

    smiling, threshold = tracker._classify_smile(0.53, 0.30)   # wide, but no lift
    assert threshold > config.SMILE_WIDTH_THRESHOLD * 0.9
    assert smiling is False                  # corners did not rise


def test_baseline_accepts_genuine_smile():
    """Beating the personal width AND raising the corners = smile."""
    tracker = bare_tracker()
    for _ in range(config.SMILE_BASELINE_WARMUP):
        tracker._width_history.append(0.40)          # narrow neutral mouth
        tracker._lift_history.append(0.30)

    smiling, threshold = tracker._classify_smile(0.46, 0.20)
    assert threshold == 0.40 + config.SMILE_WIDTH_MARGIN
    assert smiling is True


def test_smiling_frames_do_not_pollute_baseline():
    tracker = bare_tracker()
    for _ in range(config.SMILE_BASELINE_WARMUP):
        tracker._classify_smile(0.40, 0.30)          # neutral frames teach it
    size_before = len(tracker._width_history)
    tracker._classify_smile(0.70, 0.10)              # a smile - must not be learned
    assert len(tracker._width_history) == size_before
