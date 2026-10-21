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

SWIPE_DISTANCE = 0.25        # hand must move this far (0-1 = fraction of frame width)
SWIPE_TIME = 0.6             # ...within this many seconds
SWIPE_COOLDOWN = 1.0         # seconds to wait before another swipe is accepted

# Face gestures (smile = discount, deliberate blink = back)
SMILE_RATIO_THRESHOLD = 0.45  # mouth width / face width; above this = smiling
SMILE_HOLD_SECONDS = 0.5
EYE_CLOSED_THRESHOLD = 0.22   # fallback (first second only): below this = eyes closed
EYE_CLOSED_RELATIVE = 0.75    # eyes count as closed below 75% of YOUR normal open-eye value
EYE_BASELINE_FRAMES = 90      # ~3 seconds of recent frames used to learn your open-eye value
EYE_BASELINE_WARMUP = 15      # frames needed before the personal baseline is trusted
EYE_SMOOTH_FRAMES = 3         # average the last few frames so camera noise does not hide a closed eye
FACE_LOST_GRACE_SECONDS = 0.6 # MediaPipe often loses the face when the eyes shut - keep counting
BLINK_HOLD_SECONDS = 0.5      # a quick normal blink is ignored on purpose
BLINK_COOLDOWN = 1.5

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