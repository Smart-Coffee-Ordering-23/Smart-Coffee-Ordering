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


# ----------------------------------------------------------------- face
def smile_face(smiling=True, eyes_closed=False):
    return FaceInfo(face_found=True, is_smiling=smiling,
                    is_eyes_closed=eyes_closed)


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


def test_blink_fires_once():
    clock = FakeClock()
    engine = GestureEngine(clock=clock)
    events = []
    for _ in range(12):                         # eyes closed for 1.2 s
        events.extend(engine.update(None, smile_face(smiling=False,
                                                     eyes_closed=True)))
        clock.advance(0.1)
    assert events.count("BLINK") == 1


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
    closed = FaceInfo(face_found=True, is_eyes_closed=True)
    assert engine.blink_progress == 0.0
    engine.update(None, closed)
    clock.advance(0.25)
    assert 0.0 < engine.blink_progress < 1.0
    engine.update(None, FaceInfo(face_found=True))        # eyes open again
    assert engine.blink_progress == 0.0