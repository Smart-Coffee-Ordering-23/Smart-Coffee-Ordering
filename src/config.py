"""Shared settings for Smart Coffee Ordering.

Every tunable value of the project lives here: window size, colors,
gesture timing, discount rate, sounds and the debug switch.
Other files import from this module instead of repeating values.
"""
from pathlib import Path

# ================================================================= paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MENU_FILE = DATA_DIR / "menu.json"
DATABASE_FILE = DATA_DIR / "orders.db"

ASSETS_DIR = PROJECT_ROOT / "assets"
# The teacher's structure keeps product images in assets/products.
# The legacy assets/image folder is still checked so nothing breaks if it returns.
PRODUCT_IMAGE_DIRS = (ASSETS_DIR / "products", ASSETS_DIR / "image")
LOGO_PATHS = (ASSETS_DIR / "icons" / "logo.png", ASSETS_DIR / "logo.png")
SOUNDS_DIR = ASSETS_DIR / "sounds"
FONTS_DIR = ASSETS_DIR / "fonts"

# ================================================================= window
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 30
START_FULLSCREEN = False          # True = kiosk mode, F11 toggles at any time
WINDOW_TITLE = "Wave Coffee | Touchless Ordering"

# Brand
SHOP_NAME = "WAVE COFFEE"
SHOP_TAGLINE = "Touchless Coffee Ordering"
SHOP_SLOGAN = "Order your coffee with simple hand gestures."

# ================================================================= layout
NAVBAR_HEIGHT = 72                 # top bar with logo / section / cart
PROGRESS_HEIGHT = 52               # step rail under the navbar
SIDEBAR_WIDTH = 300                # right panel: camera + AI status
MAIN_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH          # 980 px for the coffee screens
HINT_HEIGHT = 56                   # bottom instruction bar
CONTENT_TOP = NAVBAR_HEIGHT + PROGRESS_HEIGHT       # 124
CONTENT_BOTTOM = WINDOW_HEIGHT - HINT_HEIGHT        # 664
CONTENT_CARD = (28, 176, MAIN_WIDTH - 56, CONTENT_BOTTOM - 184)   # big white card
ITEMS_PER_PAGE = 6                 # 3 columns x 2 rows

# ================================================================= colors
# Warm coffee-shop palette: cream background, dark brown text, caramel accent.
COLORS = {
    "background": (250, 245, 238),   # warm cream
    "card": (255, 255, 255),         # white cards
    "border": (230, 220, 210),       # light beige border
    "shadow": (226, 214, 201),       # soft shadow
    "beige": (242, 234, 224),        # secondary areas / image backgrounds
    "text": (46, 34, 27),            # dark coffee brown
    "muted": (126, 107, 92),         # muted brown text
    "accent": (180, 112, 57),        # caramel
    "accent_dark": (126, 77, 40),    # deep caramel
    "accent_soft": (248, 235, 222),  # soft caramel background
    "white": (255, 255, 255),
    "good": (80, 155, 103),          # success green
    "good_soft": (230, 244, 232),
    "bad": (194, 92, 78),            # error red-brown
    "bad_soft": (248, 232, 228),
    "panel": (52, 37, 28),           # dark coffee camera panel
    "panel_text": (248, 240, 235),
    "panel_muted": (194, 177, 162),
    "panel_alt": (89, 66, 55),
}

# ================================================================= behaviour
GESTURE_ONLY = True           # True = hands/face only: mouse and keyboard are ignored (Q still quits)
DEBUG_MODE = False            # True = show landmarks, ratios and raw AI values
SOUND_ENABLED = True          # master switch for sound feedback (M key toggles it)
SOUND_VOLUME = 0.7            # master volume 0.0 (silent) - 1.0 (loud); never harsh
SOUND_MAX_VOICES = 3          # never more than this many sounds at the same time
SOUND_RETRIGGER_SECONDS = 0.3 # default minimum gap between two plays of one sound
SOUND_AMBIENCE_ENABLED = False  # optional cafe background noise - OFF by default
SOUND_AMBIENCE_VOLUME = 0.25    # ambience stays quietly in the background
SOUND_MUSIC_ENABLED = True      # soft lo-fi cafe music loop (needs assets/sounds/fx_music.wav)
SOUND_MUSIC_VOLUME = 0.50       # background music level (it ducks while effects play)
DISCOUNT_PERCENT = 10         # smile gesture gives 10% off, once per order
MAX_QUANTITY = 10             # maximum cups of one coffee
MESSAGE_SECONDS = 2.5         # how long a toast message stays on screen
COMPLETE_SECONDS = 6          # the Thank-you screen closes by itself after this
KITCHEN_PREPARE_SECONDS = 8   # seconds an order stays "Preparing" in the kitchen

# ================================================================= gestures
# How long a gesture must be held before it triggers (seconds).
GESTURE_HOLD_SECONDS = {
    "OPEN_PALM": 0.6,
    "POINTING": 0.8,
    "THUMBS_UP": 0.7,
    "TWO_FINGERS": 0.7,
    "FIST": 0.9,
}
GESTURE_REPEAT_SECONDS = {"TWO_FINGERS": 1.2}   # keep firing while held
GESTURE_COOLDOWN = 0.7       # minimum seconds between any two gesture events

# Stability of the hand-pose vote (consecutive-frame validation).
# Example: with 10 frames and 0.8, a pose must be seen in 8 of the last
# 10 frames before it is accepted.
GESTURE_VOTE_FRAMES = 10     # last N frames voted on (majority decides)
GESTURE_MIN_CONFIDENCE = 0.8 # the winning pose needs at least this vote share
HAND_LOST_RESET_FRAMES = 3   # empty frames before all hand state is reset
HAND_MIN_DETECTION_CONFIDENCE = 0.6    # MediaPipe hand detector threshold
HAND_MIN_TRACKING_CONFIDENCE = 0.5     # MediaPipe hand tracker threshold
HAND_MIN_SCORE = 0.5         # ignore hands MediaPipe labels with low confidence
HAND_MAX_NUM_HANDS = 2       # detect up to 2, then keep the clearest one

# Hand quality gates (normalized coordinates): reject incomplete detections
# before they can confuse the classifier.
HAND_MIN_PALM_SIZE = 0.08    # wrist->middle-knuckle distance; smaller = too far/cut off
HAND_LANDMARK_MARGIN = 0.15  # landmarks may leave the frame by at most this much

# Finger state: per-finger score = FINGER_STRAIGHT_WEIGHT * PIP straightness
# (angle at the PIP joint, rotation/scale invariant) + weight * reach
# (tip beyond pip relative to palm size). Positive = extended, < 0 = curled.
# Hysteresis: >= FINGER_SCORE_ON flips the finger UP, <= FINGER_SCORE_OFF flips
# it DOWN, anything in between KEEPS the previous state (no flicker).
FINGER_SCORE_ON = 0.45       # score to accept a finger as extended
FINGER_SCORE_OFF = 0.25      # score to accept a finger as folded
FINGER_STRAIGHT_WEIGHT = 0.5 # balance between straightness and reach cues
FINGER_REACH_FULL = 0.5      # reach that counts as "fully extended" for scaling
THUMB_UP_OVER_KNUCKLE = 0.30 # thumb tip must rise this many palm sizes along
                             # the hand's own axis beyond the index knuckle

SWIPE_DISTANCE = 0.25        # hand must move this far (0-1 = fraction of frame width)
SWIPE_TIME = 0.6             # ...within this many seconds
SWIPE_COOLDOWN = 1.0         # seconds to wait before another swipe is accepted
SWIPE_MIN_SPEED = 0.45       # frame widths per second - rejects slow drifts
SWIPE_MAX_VERTICAL_RATIO = 0.7   # vertical move must stay below 70% of horizontal
SWIPE_MIN_FRAMES = 4         # samples needed before a swipe can be judged
SWIPE_MIN_PATH_RATIO = 0.7   # net path / traveled path - rejects jittery motion

# ------------------------------------------------------------- face gestures
# SMILE = 10% discount. A genuine smile needs TWO independent measurements:
#   1) mouth width / face width        (corners pulled outward)
#   2) nose-tip -> corner-mid vertical (corners raised toward the nose)
# Both are compared against this person's own neutral baseline once it is
# learned, so wide-mouthed or narrow-face users work too.
SMILE_WIDTH_THRESHOLD = 0.45     # absolute floor: mouth width / face width
SMILE_WIDTH_MARGIN = 0.03        # must beat personal neutral width by this much
SMILE_LIFT_DROP_RATIO = 0.25     # corner gap must shrink by 25% vs neutral
SMILE_HOLD_SECONDS = 0.5         # seconds the smile must be held
SMILE_STABLE_FRAMES = 4          # consecutive smiling frames required
SMILE_BASELINE_FRAMES = 150      # ~5 s of frames used to learn the neutral mouth
SMILE_BASELINE_WARMUP = 20       # frames before the personal baseline is trusted
SMILE_BASELINE_PERCENTILE = 25   # low percentile of widths = neutral mouth
                                # (the matching high percentile of lift = neutral lift)

# BLINK = Back. A blink is a complete cycle: OPEN -> CLOSED -> OPEN.
# Closures shorter than MIN are noise; longer than MAX count as "eyes kept
# closed" and are ignored on purpose. A face must be seen open first.
BLINK_MIN_SECONDS = 0.10     # shortest closure that counts as a deliberate blink
BLINK_MAX_SECONDS = 0.70     # longer than this = keeping eyes closed, not blinking
BLINK_COOLDOWN = 1.5         # seconds between two accepted blinks
EYE_CLOSED_THRESHOLD = 0.22   # fallback (first second only): below this = eyes closed
EYE_CLOSED_RELATIVE = 0.75    # eyes count as closed below 75% of YOUR normal open-eye value
EYE_BASELINE_FRAMES = 90      # ~3 seconds of recent frames used to learn your open-eye value
EYE_BASELINE_WARMUP = 15      # frames needed before the personal baseline is trusted
EYE_SMOOTH_FRAMES = 3         # average the last few frames so camera noise does not hide a closed eye
FACE_LOST_GRACE_SECONDS = 0.6 # MediaPipe often loses the face when the eyes shut - keep counting

# ------------------------------------------------------------- camera
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_BUFFER_FRAMES = 1      # keep the freshest frame only (low latency)
CAMERA_FRAME_STALE_SECONDS = 1.0   # older frame = treated as "camera lost"
CAMERA_RECONNECT_SECONDS = 3.0     # retry interval after a camera dropout

# ================================================================= screens
WELCOME = "WELCOME"
MENU = "MENU"
SELECT = "SELECT"
QUANTITY = "QUANTITY"
DISCOUNT = "DISCOUNT"
CONFIRM = "CONFIRM"
SUMMARY = "SUMMARY"
COMPLETE = "COMPLETE"

SCREEN_ORDER = [WELCOME, MENU, SELECT, QUANTITY, DISCOUNT, CONFIRM, SUMMARY, COMPLETE]

# (screen, label) shown on the progress rail and used as the navbar section name
STEP_LABELS = [
    (WELCOME, "Welcome"),
    (MENU, "Menu"),
    (SELECT, "Select"),
    (QUANTITY, "Quantity"),
    (DISCOUNT, "Discount"),
    (CONFIRM, "Confirm"),
    (SUMMARY, "Summary"),
    (COMPLETE, "Done"),
]