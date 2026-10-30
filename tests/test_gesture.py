"""Gesture engine tests with synthetic hand/face data (no camera needed).

Recreated after the original file was lost (see .pytest_cache node ids).
Landmarks follow MediaPipe point numbering: 0 = wrist, 4 = thumb tip,
8 = index tip, 9 = middle-finger knuckle (palm centre), 21 points total.
"""
from src.gesture_engine import GestureEngine
from src.hand_tracker import FaceInfo


class FakeClock:
    """A clock the test can advance by hand."""

    def __init__(self, start=1000.0):
        self.now = start

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


# ---------------------------------------------------------------- hands
FINGERS = {"index": (8, 6), "middle": (12, 10), "ring": (16, 14), "pinky": (20, 18)}
FINGER_X = {"index": 0.42, "middle": 0.50, "ring": 0.58, "pinky": 0.66}


def make_hand(up=(), thumb_up=False):
    """Build 21 landmarks. `up` names which fingers are extended."""
    points = [(0.50, 0.75)] * 21
    points[0] = (0.50, 0.90)              # wrist
    points[9] = (0.50, 0.70)              # middle knuckle -> palm size 0.20
    for name, (tip, middle) in FINGERS.items():
        x = FINGER_X[name]
        if name in up:
            points[middle] = (x, 0.70)
            points[tip] = (x, 0.45)       # tip far from wrist -> extended
        else:
            points[middle] = (x, 0.72)
            points[tip] = (x, 0.82)       # tip near wrist -> curled
    points[5] = (FINGER_X["index"], 0.70) # index knuckle (thumb check)
    if thumb_up:                          # thumb points to the sky
        points[2], points[3], points[4] = (0.38, 0.66), (0.36, 0.55), (0.34, 0.45)
    else:                                 # thumb folded
        points[2], points[3], points[4] = (0.36, 0.84), (0.38, 0.82), (0.40, 0.80)
    return points


def feed(engine, landmarks, seconds, step=0.1):
    """Show one hand pose for `seconds`, returning all events that fired."""
    events = []
    elapsed = 0.0
    while elapsed < seconds:
        events.extend(engine.update(landmarks))
        engine._clock.advance(step)
        elapsed += step
    return events


OPEN_PALM = make_hand(up=("index", "middle", "ring", "pinky"))
POINTING = make_hand(up=("index",))
TWO_FINGERS = make_hand(up=("index", "middle"))
FIST = make_hand()
THUMBS_UP = make_hand(thumb_up=True)


# ---------------------------------------------------------------- poses
def test_no_hand_gives_no_events():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    for _ in range(20):
        assert engine.update(None) == []
        clock.advance(0.1)


def test_open_palm_recognized():
    engine = GestureEngine(clock=FakeClock())
    assert "OPEN_PALM" in feed(engine, OPEN_PALM, 1.5)


def test_pointing_recognized():
    engine = GestureEngine(clock=FakeClock())
    assert "POINTING" in feed(engine, POINTING, 1.5)


def test_two_fingers_recognized():
    engine = GestureEngine(clock=FakeClock())
    assert "TWO_FINGERS" in feed(engine, TWO_FINGERS, 1.5)


def test_fist_recognized():
    engine = GestureEngine(clock=FakeClock())
    assert "FIST" in feed(engine, FIST, 1.5)


def test_thumbs_up_recognized():
    engine = GestureEngine(clock=FakeClock())
    assert "THUMBS_UP" in feed(engine, THUMBS_UP, 1.5)


# --------------------------------------------------------------- debounce
def test_held_gesture_fires_only_once():
    """One held gesture must never trigger a second action."""
    engine = GestureEngine(clock=FakeClock())
    events = feed(engine, THUMBS_UP, 3.0)
    assert events.count("THUMBS_UP") == 1


def test_gesture_cooldown_works():
    """A new gesture within the cooldown window is ignored."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    feed(engine, POINTING, 1.2)                 # fires POINTING
    events = feed(engine, THUMBS_UP, 0.3)       # inside the 0.7 s cooldown
    assert "THUMBS_UP" not in events


def test_rearm_allows_retry():
    """When the controller rejects an action, rearm lets the gesture retry."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    feed(engine, THUMBS_UP, 1.0)
    engine.rearm()
    clock.advance(1.0)                          # step past the cooldown
    assert "THUMBS_UP" in feed(engine, THUMBS_UP, 1.0)


# ---------------------------------------------------------------- swipes
def swipe_frames(engine, clock, start_x, direction, frames=6):
    """An open palm moving sideways - returns the events seen."""
    events = []
    for i in range(frames):
        hand = list(OPEN_PALM)
        hand[9] = (start_x + direction * 0.08 * i, 0.70)
        hand[0] = hand[9]
        events.extend(engine.update(hand))
        clock.advance(0.1)
    return events


def test_swipe_right_detected():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = swipe_frames(engine, clock, start_x=0.20, direction=+1)
    assert "SWIPE_RIGHT" in events


def test_swipe_left_detected():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = swipe_frames(engine, clock, start_x=0.80, direction=-1)
    assert "SWIPE_LEFT" in events


def test_swipe_cooldown_blocks_second_swipe():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    swipe_frames(engine, clock, start_x=0.20, direction=+1)
    clock.advance(0.3)                          # < SWIPE_COOLDOWN (1.0 s)
    # 5 frames span 0.4 s: the whole attempt ends at t+0.7 < blocked_until.
    # Frame 5 alone would move 0.32 >= SWIPE_DISTANCE, so only the cooldown
    # can be what stops this second swipe from firing.
    events = swipe_frames(engine, clock, start_x=0.20, direction=+1, frames=5)
    assert "SWIPE_RIGHT" not in events
    # once the cooldown has expired, a new swipe is allowed again
    clock.advance(1.0)
    events = swipe_frames(engine, clock, start_x=0.20, direction=+1)
    assert "SWIPE_RIGHT" in events


def test_slow_drift_is_not_a_swipe():
    """Moving the hand far but slowly (a drift) must not count as a swipe."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for i in range(7):                 # 0.043 per 0.1 s = 0.43 widths/s < 0.45
        hand = list(OPEN_PALM)
        hand[9] = (0.20 + 0.043 * i, 0.70)
        hand[0] = hand[9]
        events.extend(engine.update(hand))
        clock.advance(0.1)
    # 0.258 >= SWIPE_DISTANCE within the window, but too slow to be a swipe
    assert "SWIPE_RIGHT" not in events
    assert "SWIPE_LEFT" not in events


def test_swipe_survives_one_curled_finger_frame():
    """A single non-palm frame mid-swipe must not erase the motion history."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for i in range(6):
        hand = list(OPEN_PALM)
        hand[9] = (0.20 + 0.08 * i, 0.70)
        hand[0] = hand[9]
        if i == 3:                      # one frame reads as TWO_FINGERS
            hand = list(TWO_FINGERS)
            hand[9] = (0.20 + 0.08 * i, 0.70)
            hand[0] = hand[9]
        events.extend(engine.update(hand))
        clock.advance(0.1)
    assert "SWIPE_RIGHT" in events


# ---------------------------------------------------- stability / debug
def test_hand_loss_resets_gesture_hold():
    """A held gesture must restart its hold after the hand disappears."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = feed(engine, THUMBS_UP, 0.5)       # < 0.7 s hold: nothing yet
    assert "THUMBS_UP" not in events
    for _ in range(5):                          # hand lost 0.5 s
        assert engine.update(None) == []
        clock.advance(0.1)
    events = feed(engine, THUMBS_UP, 0.4)       # hold restarts from scratch
    assert "THUMBS_UP" not in events


def test_camera_dropout_does_not_complete_a_hold():
    """The engine must be fed None while the camera is gone (main.py does this)."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = feed(engine, THUMBS_UP, 0.6)       # just under the 0.7 s hold
    assert "THUMBS_UP" not in events
    for _ in range(4):                          # camera dropout, frames = None
        engine.update(None, None)
        clock.advance(0.1)
    events = feed(engine, THUMBS_UP, 0.6)       # hold must start over
    assert "THUMBS_UP" not in events


def test_gesture_confidence_and_cooldown_debug_values():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    assert engine.gesture_confidence == 0.0
    assert engine.last_event == "NONE"
    feed(engine, OPEN_PALM, 1.0)                  # fires OPEN_PALM once
    assert engine.last_event == "OPEN_PALM"
    assert engine.gesture_confidence == 1.0
    assert engine.cooldown_remaining > 0.0
    clock.advance(1.0)
    assert engine.cooldown_remaining == 0.0


# ----------------------------------------------------------------- face
def smile_face(smiling=True, eyes_closed=False):
    return FaceInfo(face_found=True, is_smiling=smiling,
                    is_eyes_closed=eyes_closed)


def open_face():
    return FaceInfo(face_found=True)


def test_no_face_no_face_events():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    for _ in range(20):
        assert engine.update(None, FaceInfo(face_found=False)) == []
        clock.advance(0.1)


def test_smile_fires_once():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for _ in range(12):                         # smiling for 1.2 s
        events.extend(engine.update(None, smile_face(smiling=True)))
        clock.advance(0.1)
    assert events.count("SMILE") == 1


def test_smile_needs_stable_consecutive_frames():
    """A smile flickering on/off frame by frame must never fire."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for _ in range(30):                         # 2 on / 1 off, forever
        events.extend(engine.update(None, smile_face(smiling=True)))
        clock.advance(0.1)
        events.extend(engine.update(None, smile_face(smiling=True)))
        clock.advance(0.1)
        events.extend(engine.update(None, open_face()))   # breaks the run
        clock.advance(0.1)
    assert "SMILE" not in events


def test_blink_fires_once_per_cycle():
    """A complete OPEN -> CLOSED -> OPEN blink fires exactly once."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for _ in range(6):                          # eyes open first
        events.extend(engine.update(None, open_face()))
        clock.advance(0.1)
    for _ in range(4):                          # closed 0.4 s (inside 0.10-0.70)
        events.extend(engine.update(None, smile_face(smiling=False, eyes_closed=True)))
        clock.advance(0.1)
    for _ in range(6):                          # open again -> cycle complete
        events.extend(engine.update(None, open_face()))
        clock.advance(0.1)
    assert events.count("BLINK") == 1
    assert events.count("SMILE") == 0


def test_blink_too_short_is_ignored():
    """A half-open flicker shorter than BLINK_MIN_SECONDS is not a blink."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for _ in range(5):
        events.extend(engine.update(None, open_face()))
        clock.advance(0.1)
    events.extend(engine.update(None, smile_face(smiling=False, eyes_closed=True)))
    clock.advance(0.05)                         # only 0.05 s closed (< 0.10)
    events.extend(engine.update(None, open_face()))
    assert "BLINK" not in events


def test_eyes_kept_closed_are_not_a_blink():
    """Closing the eyes longer than BLINK_MAX_SECONDS means 'eyes closed', not blink."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for _ in range(5):
        events.extend(engine.update(None, open_face()))
        clock.advance(0.1)
    for _ in range(12):                         # 1.2 s closed (> 0.70 max)
        events.extend(engine.update(None, smile_face(smiling=False, eyes_closed=True)))
        clock.advance(0.1)
    events.extend(engine.update(None, open_face()))
    assert "BLINK" not in events


def test_blink_requires_eyes_seen_open_first():
    """Face appears already closed (or unknown) -> no blink can start."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for _ in range(5):                          # face never seen open
        events.extend(engine.update(None, FaceInfo(face_found=False)))
        clock.advance(0.1)
    for _ in range(5):
        events.extend(engine.update(None, smile_face(smiling=False, eyes_closed=True)))
        clock.advance(0.1)
    events.extend(engine.update(None, open_face()))
    assert "BLINK" not in events


def test_face_lost_cancels_pending_blink():
    """Losing the face longer than the grace period cancels the closure."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for _ in range(5):
        events.extend(engine.update(None, open_face()))
        clock.advance(0.1)
    events.extend(engine.update(None, smile_face(smiling=False, eyes_closed=True)))
    clock.advance(0.1)
    for _ in range(8):                          # face gone 0.8 s > 0.6 s grace
        events.extend(engine.update(None, FaceInfo(face_found=False)))
        clock.advance(0.1)
    for _ in range(5):                          # face returns still closed
        events.extend(engine.update(None, smile_face(smiling=False, eyes_closed=True)))
        clock.advance(0.1)
    events.extend(engine.update(None, open_face()))
    assert "BLINK" not in events


def test_face_lost_briefly_keeps_pending_blink():
    """MediaPipe's usual short face flicker must not kill a good blink."""
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for _ in range(5):
        events.extend(engine.update(None, open_face()))
        clock.advance(0.1)
    events.extend(engine.update(None, smile_face(smiling=False, eyes_closed=True)))
    clock.advance(0.15)
    for _ in range(2):                          # face lost 0.2 s (< 0.6 s grace)
        events.extend(engine.update(None, FaceInfo(face_found=False)))
        clock.advance(0.1)
    events.extend(engine.update(None, smile_face(smiling=False, eyes_closed=True)))
    clock.advance(0.15)
    events.extend(engine.update(None, open_face()))    # total closed ~0.5 s
    assert events.count("BLINK") == 1


def test_blink_cooldown_blocks_second_blink():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)

    def blink_once():
        got = []
        for _ in range(4):
            got.extend(engine.update(None, open_face()))
            clock.advance(0.1)
        for _ in range(4):
            got.extend(engine.update(None, smile_face(smiling=False, eyes_closed=True)))
            clock.advance(0.1)
        for _ in range(3):
            got.extend(engine.update(None, open_face()))
            clock.advance(0.1)
        return got

    assert blink_once().count("BLINK") == 1
    clock.advance(0.1)                          # second attempt finishes inside
    assert blink_once().count("BLINK") == 0     # the 1.5 s BLINK_COOLDOWN window
    clock.advance(2.0)                          # cooldown expired
    assert blink_once().count("BLINK") == 1


def test_reset_face_state_clears_half_held_gestures():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    engine.update(None, smile_face(smiling=True))       # smile just started
    assert engine.smile_started_at is not None
    engine.reset_face_state()
    assert engine.smile_started_at is None
    assert engine.smile_frames == 0
    assert engine.smile_has_fired is False


# ------------------------------------------------------- finger display
def test_finger_states_none_without_hand():
    assert GestureEngine.finger_states(None) is None


def test_finger_states_open_palm_with_thumb_out():
    hand = make_hand(up=("index", "middle", "ring", "pinky"), thumb_up=True)
    states = GestureEngine.finger_states(hand)
    assert states is not None
    assert states == {"thumb": True, "index": True, "middle": True,
                      "ring": True, "pinky": True}


def test_finger_states_fist_has_no_finger_up():
    states = GestureEngine.finger_states(make_hand())
    assert states is not None
    assert not any(states.values())


def test_finger_states_two_fingers():
    states = GestureEngine.finger_states(make_hand(up=("index", "middle")))
    assert states is not None
    assert states["index"] and states["middle"]
    assert not (states["thumb"] or states["ring"] or states["pinky"])


# ---------------------------------------------- face hold progress (UI)
def test_smile_progress_grows_then_resets():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    smiling = FaceInfo(face_found=True, is_smiling=True)
    assert engine.smile_progress == 0.0
    engine.update(None, smiling)
    clock.advance(0.25)
    assert 0.0 < engine.smile_progress < 1.0
    engine.update(None, FaceInfo(face_found=True))        # smile stops
    assert engine.smile_progress == 0.0


def test_blink_progress_grows_then_resets():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    assert engine.blink_progress == 0.0
    engine.update(None, FaceInfo(face_found=True))    # eyes must be seen open first
    clock.advance(0.1)
    engine.update(None, FaceInfo(face_found=True, is_eyes_closed=True))
    clock.advance(0.25)
    assert 0.0 < engine.blink_progress < 1.0
    engine.update(None, FaceInfo(face_found=True))    # eyes open again
    assert engine.blink_progress == 0.0