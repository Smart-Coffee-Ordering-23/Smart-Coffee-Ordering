"""Shared settings for Smart Coffee Ordering.

Every tunable value of the project lives here: window size, colors,
gesture timing, discount rate, sounds and the debug switch.
Other files import from this module instead of repeating values.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MENU_FILE = DATA_DIR / "menu.json"
DATABASE_FILE = DATA_DIR / "orders.db"

ASSETS_DIR = PROJECT_ROOT / "assets"

PRODUCT_IMAGE_DIRS = (ASSETS_DIR / "products", ASSETS_DIR / "image")
LOGO_PATHS = (ASSETS_DIR / "icons" / "logo.png", ASSETS_DIR / "logo.png")
SOUNDS_DIR = ASSETS_DIR / "sounds"
FONTS_DIR = ASSETS_DIR / "fonts"

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
FPS = 30
START_FULLSCREEN = False          
WINDOW_TITLE = "Wave Coffee | Touchless Ordering"

SHOP_NAME = "WAVE COFFEE"
SHOP_TAGLINE = "Touchless Coffee Ordering"
SHOP_SLOGAN = "Order your coffee with simple hand gestures."

NAVBAR_HEIGHT = 72                 
PROGRESS_HEIGHT = 52               
SIDEBAR_WIDTH = 300                
MAIN_WIDTH = WINDOW_WIDTH - SIDEBAR_WIDTH          
HINT_HEIGHT = 56                   
CONTENT_TOP = NAVBAR_HEIGHT + PROGRESS_HEIGHT       
CONTENT_BOTTOM = WINDOW_HEIGHT - HINT_HEIGHT       
CONTENT_CARD = (28, 176, MAIN_WIDTH - 56, CONTENT_BOTTOM - 184)  
ITEMS_PER_PAGE = 6                

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

GESTURE_ONLY = True          
DEBUG_MODE = False           
SOUND_ENABLED = True          
SOUND_VOLUME = 0.7           
SOUND_MAX_VOICES = 3          
SOUND_RETRIGGER_SECONDS = 0.3 
SOUND_AMBIENCE_ENABLED = False 
SOUND_AMBIENCE_VOLUME = 0.25    
SOUND_MUSIC_ENABLED = True      
SOUND_MUSIC_VOLUME = 0.50      
DISCOUNT_PERCENT = 10         
MAX_QUANTITY = 10             
MESSAGE_SECONDS = 2.5         
COMPLETE_SECONDS = 6          
KITCHEN_PREPARE_SECONDS = 8   

GESTURE_HOLD_SECONDS = {
    "OPEN_PALM": 0.6,
    "POINTING": 0.8,
    "THUMBS_UP": 0.7,
    "TWO_FINGERS": 0.7,
    "FIST": 0.9,
}
GESTURE_REPEAT_SECONDS = {"TWO_FINGERS": 1.2}   
GESTURE_COOLDOWN = 0.7       

GESTURE_VOTE_FRAMES = 10    
GESTURE_MIN_CONFIDENCE = 0.8 
HAND_LOST_RESET_FRAMES = 3  
HAND_MIN_DETECTION_CONFIDENCE = 0.6   
HAND_MIN_TRACKING_CONFIDENCE = 0.5     
HAND_MIN_SCORE = 0.5        
HAND_MAX_NUM_HANDS = 2       
HAND_MIN_PALM_SIZE = 0.08    
HAND_LANDMARK_MARGIN = 0.15  

FINGER_SCORE_ON = 0.45      
FINGER_SCORE_OFF = 0.25      
FINGER_STRAIGHT_WEIGHT = 0.5 
FINGER_REACH_FULL = 0.5     
THUMB_UP_OVER_KNUCKLE = 0.30 

SWIPE_DISTANCE = 0.25        
SWIPE_TIME = 0.6             
SWIPE_COOLDOWN = 1.0         
SWIPE_MIN_SPEED = 0.45       
SWIPE_MAX_VERTICAL_RATIO = 0.7   
SWIPE_MIN_FRAMES = 4         
SWIPE_MIN_PATH_RATIO = 0.7   

SMILE_WIDTH_THRESHOLD = 0.45     
SMILE_WIDTH_MARGIN = 0.03        
SMILE_LIFT_DROP_RATIO = 0.25     
SMILE_HOLD_SECONDS = 0.5         
SMILE_STABLE_FRAMES = 4          
SMILE_BASELINE_FRAMES = 150      
SMILE_BASELINE_WARMUP = 20       
SMILE_BASELINE_PERCENTILE = 25   
                              
BLINK_MIN_SECONDS = 0.10     
BLINK_MAX_SECONDS = 0.70     
BLINK_COOLDOWN = 1.5         
EYE_CLOSED_THRESHOLD = 0.22   
EYE_CLOSED_RELATIVE = 0.75   
EYE_BASELINE_FRAMES = 90     
EYE_BASELINE_WARMUP = 15     
EYE_SMOOTH_FRAMES = 3        
FACE_LOST_GRACE_SECONDS = 0.6 

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_BUFFER_FRAMES = 1      
CAMERA_FRAME_STALE_SECONDS = 1.0   
CAMERA_RECONNECT_SECONDS = 3.0    
WELCOME = "WELCOME"
MENU = "MENU"
SELECT = "SELECT"
QUANTITY = "QUANTITY"
DISCOUNT = "DISCOUNT"
CONFIRM = "CONFIRM"
SUMMARY = "SUMMARY"
COMPLETE = "COMPLETE"

SCREEN_ORDER = [WELCOME, MENU, SELECT, QUANTITY, DISCOUNT, CONFIRM, SUMMARY, COMPLETE]

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